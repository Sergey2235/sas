"""
Сервис для работы с GitHub API.
"""
import base64
from datetime import datetime
from typing import List, Optional, Tuple
from urllib.parse import urlparse

import requests

from models import GitCommitResult, GitFileInfo, TokenValidationResult


class GitHubService:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update(
            {
                "User-Agent": "CodeQualityChecker/1.0",
                "Accept": "application/vnd.github.v3+json",
            }
        )

    def parse_github_url(self, url: str) -> Tuple[str, str, str, str]:
        url = url.strip().rstrip("/")
        parsed = urlparse(url)
        segments = [s for s in parsed.path.split("/") if s]
        if len(segments) < 2:
            raise ValueError("Неверный формат URL GitHub репозитория")
        owner = segments[0]
        repo = segments[1].replace(".git", "")
        branch = ""
        path = ""
        for i, seg in enumerate(segments[2:], start=2):
            if seg in {"tree", "blob"}:
                branch = segments[i + 1] if i + 1 < len(segments) else ""
                path = "/".join(segments[i + 2 :]) if i + 2 < len(segments) else ""
                break
        return owner, repo, branch, path

    async def get_default_branch(
        self, owner: str, repo: str, token: Optional[str] = None
    ) -> str:
        headers = dict(self.session.headers)
        if token:
            headers["Authorization"] = f"Bearer {token}"
        response = self.session.get(f"https://api.github.com/repos/{owner}/{repo}", headers=headers)
        response.raise_for_status()
        return response.json().get("default_branch", "main")

    async def get_file_content(
        self, owner: str, repo: str, path: str, branch: str, token: Optional[str] = None
    ) -> str:
        headers = dict(self.session.headers)
        if token:
            headers["Authorization"] = f"Bearer {token}"
        url = f"https://api.github.com/repos/{owner}/{repo}/contents/{path}?ref={branch}"
        response = self.session.get(url, headers=headers)
        response.raise_for_status()
        content = response.json().get("content", "")
        if not content:
            raise ValueError("Не удалось получить содержимое файла")
        return base64.b64decode(content.replace("\n", "")).decode("utf-8", errors="replace")

    async def get_directory_contents(
        self, owner: str, repo: str, path: str, branch: str, token: Optional[str] = None
    ) -> List[GitFileInfo]:
        headers = dict(self.session.headers)
        if token:
            headers["Authorization"] = f"Bearer {token}"
        url = (
            f"https://api.github.com/repos/{owner}/{repo}/contents/{path}?ref={branch}"
            if path
            else f"https://api.github.com/repos/{owner}/{repo}/contents?ref={branch}"
        )
        response = self.session.get(url, headers=headers)
        response.raise_for_status()
        data = response.json()
        if isinstance(data, dict):
            data = [data]
        return [
            GitFileInfo(
                name=item.get("name", ""),
                path=item.get("path", ""),
                type="dir" if item.get("type") == "dir" else "file",
                size=item.get("size", 0),
                download_url=item.get("download_url"),
            )
            for item in data
        ]

    async def create_commit_with_fixes(
        self,
        owner: str,
        repo: str,
        branch: str,
        file_path: str,
        fixed_content: str,
        commit_message: str,
        pr_description: str,
        token: str,
    ) -> GitCommitResult:
        if not token:
            return GitCommitResult(success=False, error_message="Требуется токен")
        headers = {**self.session.headers, "Authorization": f"Bearer {token}"}
        try:
            branch_url = f"https://api.github.com/repos/{owner}/{repo}/branches/{branch}"
            response = self.session.get(branch_url, headers=headers)
            response.raise_for_status()
            sha = response.json()["commit"]["sha"]

            feature_branch = f"code-quality-fix-{datetime.now().strftime('%Y%m%d%H%M%S')}"
            ref_data = {"ref": f"refs/heads/{feature_branch}", "sha": sha}
            response = self.session.post(
                f"https://api.github.com/repos/{owner}/{repo}/git/refs",
                headers=headers,
                json=ref_data,
            )
            response.raise_for_status()

            get_file_url = f"https://api.github.com/repos/{owner}/{repo}/contents/{file_path}?ref={branch}"
            response = self.session.get(get_file_url, headers=headers)
            response.raise_for_status()
            current_sha = response.json().get("sha")

            content_data = {
                "message": commit_message,
                "content": base64.b64encode(fixed_content.encode("utf-8")).decode("utf-8"),
                "branch": feature_branch,
            }
            if current_sha:
                content_data["sha"] = current_sha

            response = self.session.put(
                f"https://api.github.com/repos/{owner}/{repo}/contents/{file_path}",
                headers=headers,
                json=content_data,
            )
            response.raise_for_status()

            pr_data = {
                "head": feature_branch,
                "base": branch,
                "title": commit_message.split("\n")[0],
                "body": pr_description,
            }
            response = self.session.post(
                f"https://api.github.com/repos/{owner}/{repo}/pulls",
                headers=headers,
                json=pr_data,
            )
            response.raise_for_status()
            created_pr = response.json()
            return GitCommitResult(
                success=True,
                branch_name=feature_branch,
                pull_request_url=created_pr.get("html_url", ""),
                pull_request_number=created_pr.get("number", 0),
            )
        except Exception as exc:
            return GitCommitResult(success=False, error_message=str(exc))

    async def add_pull_request_comment(
        self, owner: str, repo: str, pr_number: int, comment: str, token: str
    ) -> bool:
        if not token:
            return False
        headers = {**self.session.headers, "Authorization": f"Bearer {token}"}
        url = f"https://api.github.com/repos/{owner}/{repo}/issues/{pr_number}/comments"
        response = self.session.post(url, headers=headers, json={"body": comment})
        return response.status_code == 201

    async def validate_token(self, token: str) -> TokenValidationResult:
        headers = {**self.session.headers, "Authorization": f"Bearer {token}"}
        try:
            response = self.session.get("https://api.github.com/user", headers=headers)
            if response.status_code == 200:
                return TokenValidationResult(
                    is_valid=True, user_name=response.json().get("login", "")
                )
            return TokenValidationResult(is_valid=False, error_message="Неверный токен")
        except Exception as exc:
            return TokenValidationResult(is_valid=False, error_message=str(exc))
