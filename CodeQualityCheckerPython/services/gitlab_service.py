"""
Сервис для работы с GitLab API.
"""
import base64
from datetime import datetime
from typing import List, Optional, Tuple
from urllib.parse import quote, urlparse

import requests

from models import GitCommitResult, GitFileInfo, TokenValidationResult


class GitLabService:
    def __init__(self):
        self.session = requests.Session()

    def parse_gitlab_url(self, url: str) -> Tuple[str, str, str, str]:
        url = url.strip().rstrip("/")
        if url.endswith(".git"):
            url = url[:-4]
        parsed = urlparse(url)
        segments = [s for s in parsed.path.split("/") if s]
        if len(segments) < 2:
            raise ValueError("Неверный формат URL GitLab репозитория")
        owner, repo = segments[0], segments[1]
        branch, path = "", ""
        full_path = "/".join(segments)
        if "-/tree/" in full_path:
            after = full_path.split("-/tree/", maxsplit=1)[1]
            parts = after.split("/")
            branch = parts[0]
            path = "/".join(parts[1:]) if len(parts) > 1 else ""
        elif "-/blob/" in full_path:
            after = full_path.split("-/blob/", maxsplit=1)[1]
            parts = after.split("/")
            branch = parts[0]
            path = "/".join(parts[1:]) if len(parts) > 1 else ""
        return owner, repo, branch, path

    def _encode_project_path(self, owner: str, repo: str) -> str:
        return quote(f"{owner}/{repo}", safe="")

    async def get_default_branch(
        self, owner: str, repo: str, token: Optional[str] = None
    ) -> str:
        project_path = self._encode_project_path(owner, repo)
        headers = {"Authorization": f"Bearer {token}"} if token else {}
        response = self.session.get(
            f"https://gitlab.com/api/v4/projects/{project_path}", headers=headers
        )
        response.raise_for_status()
        return response.json().get("default_branch", "main")

    async def get_file_content(
        self, owner: str, repo: str, path: str, branch: str, token: Optional[str] = None
    ) -> str:
        project_path = self._encode_project_path(owner, repo)
        encoded_path = quote(path, safe="")
        headers = {"Authorization": f"Bearer {token}"} if token else {}
        url = (
            f"https://gitlab.com/api/v4/projects/{project_path}/repository/files/"
            f"{encoded_path}?ref={branch}"
        )
        response = self.session.get(url, headers=headers)
        response.raise_for_status()
        content = response.json().get("content", "")
        if not content:
            raise ValueError("Не удалось получить содержимое файла")
        return base64.b64decode(content).decode("utf-8", errors="replace")

    async def get_directory_contents(
        self, owner: str, repo: str, path: str, branch: str, token: Optional[str] = None
    ) -> List[GitFileInfo]:
        project_path = self._encode_project_path(owner, repo)
        headers = {"Authorization": f"Bearer {token}"} if token else {}
        if path:
            url = (
                f"https://gitlab.com/api/v4/projects/{project_path}/repository/tree"
                f"?path={quote(path, safe='')}&ref={branch}"
            )
        else:
            url = (
                f"https://gitlab.com/api/v4/projects/{project_path}/repository/tree"
                f"?ref={branch}"
            )
        response = self.session.get(url, headers=headers)
        response.raise_for_status()
        return [
            GitFileInfo(
                name=item.get("name", ""),
                path=item.get("path", ""),
                type="dir" if item.get("type") == "tree" else "file",
                size=0,
            )
            for item in response.json()
        ]

    async def create_commit_with_fixes(
        self,
        owner: str,
        repo: str,
        branch: str,
        file_path: str,
        fixed_content: str,
        commit_message: str,
        mr_description: str,
        token: str,
    ) -> GitCommitResult:
        if not token:
            return GitCommitResult(success=False, error_message="Требуется токен")
        project_path = self._encode_project_path(owner, repo)
        feature_branch = f"code-quality-fix-{datetime.now().strftime('%Y%m%d%H%M%S')}"
        headers = {"Authorization": f"Bearer {token}"}
        try:
            response = self.session.post(
                f"https://gitlab.com/api/v4/projects/{project_path}/repository/branches",
                headers=headers,
                json={"branch": feature_branch, "ref": branch},
            )
            response.raise_for_status()
            response = self.session.post(
                f"https://gitlab.com/api/v4/projects/{project_path}/repository/commits",
                headers=headers,
                json={
                    "branch": feature_branch,
                    "commit_message": commit_message,
                    "actions": [
                        {
                            "action": "update",
                            "file_path": file_path,
                            "content": fixed_content,
                        }
                    ],
                },
            )
            response.raise_for_status()
            response = self.session.post(
                f"https://gitlab.com/api/v4/projects/{project_path}/merge_requests",
                headers=headers,
                json={
                    "source_branch": feature_branch,
                    "target_branch": branch,
                    "title": commit_message.split("\n")[0],
                    "description": mr_description,
                },
            )
            response.raise_for_status()
            mr_data = response.json()
            return GitCommitResult(
                success=True,
                branch_name=feature_branch,
                pull_request_url=mr_data.get("web_url", ""),
                pull_request_number=mr_data.get("iid", 0),
            )
        except Exception as exc:
            return GitCommitResult(success=False, error_message=str(exc))

    async def add_merge_request_comment(
        self, owner: str, repo: str, mr_iid: int, comment: str, token: str
    ) -> bool:
        if not token:
            return False
        project_path = self._encode_project_path(owner, repo)
        response = self.session.post(
            f"https://gitlab.com/api/v4/projects/{project_path}/merge_requests/{mr_iid}/notes",
            headers={"Authorization": f"Bearer {token}"},
            json={"body": comment},
        )
        return response.status_code == 201

    async def validate_token(self, token: str) -> TokenValidationResult:
        try:
            response = self.session.get(
                "https://gitlab.com/api/v4/user",
                headers={"Authorization": f"Bearer {token}"},
            )
            if response.status_code == 200:
                return TokenValidationResult(
                    is_valid=True, user_name=response.json().get("username", "")
                )
            return TokenValidationResult(is_valid=False, error_message="Неверный токен")
        except Exception as exc:
            return TokenValidationResult(is_valid=False, error_message=str(exc))
