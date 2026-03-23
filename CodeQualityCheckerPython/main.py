import asyncio
import json
import os
import threading
from datetime import datetime
from tkinter import filedialog, messagebox

import customtkinter as ctk

from models import AnalysisType, CodeSubmission
from services.github_service import GitHubService
from services.gitlab_service import GitLabService
from services.history_service import AnalysisRecord, HistoryService
from services.llm_service import LlmService


LANGUAGE_MAP = {
    ".cs": "C#",
    ".py": "Python",
    ".js": "JavaScript",
    ".ts": "TypeScript",
    ".java": "Java",
    ".cpp": "C++",
    ".c": "C",
    ".go": "Go",
    ".rs": "Rust",
    ".php": "PHP",
    ".rb": "Ruby",
    ".swift": "Swift",
    ".kt": "Kotlin",
    ".sql": "SQL",
}

ANALYSIS_TYPE_LABELS = {
    AnalysisType.FULL: "Полный анализ",
    AnalysisType.SECURITY_ONLY: "Только безопасность",
    AnalysisType.STYLE_ONLY: "Только стиль",
    AnalysisType.PERFORMANCE: "Производительность",
    AnalysisType.BEST_PRACTICES: "Лучшие практики",
    AnalysisType.CODE_EXAMPLES: "Примеры улучшенного кода",
}

LABEL_TO_ANALYSIS_TYPE = {v: k for k, v in ANALYSIS_TYPE_LABELS.items()}


class CodeQualityCheckerApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Code Quality Checker")
        self.geometry("1500x900")

        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        self.llm_service = LlmService()
        self.github_service = GitHubService()
        self.gitlab_service = GitLabService()
        self.history_service = HistoryService()

        self.last_history_records: list[AnalysisRecord] = []
        self.history_buttons = []

        self._build_ui()
        self._refresh_history()

    def _build_ui(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        header = ctk.CTkFrame(self)
        header.grid(row=0, column=0, sticky="ew", padx=10, pady=(10, 0))
        header.grid_columnconfigure(0, weight=1)
        self.title_label = ctk.CTkLabel(
            header,
            text="Code Quality Checker - Дипломная версия",
            font=ctk.CTkFont(size=20, weight="bold"),
        )
        self.title_label.grid(row=0, column=0, sticky="w", padx=12, pady=10)
        self.status_label = ctk.CTkLabel(header, text="Статус: готово")
        self.status_label.grid(row=0, column=1, sticky="e", padx=12, pady=10)

        tabs = ctk.CTkTabview(self)
        tabs.grid(row=1, column=0, sticky="nsew", padx=10, pady=10)
        self.tab_local = tabs.add("Локальный анализ")
        self.tab_git = tabs.add("Git-репозиторий")
        self.tab_history = tabs.add("История анализов")

        self._build_local_tab()
        self._build_git_tab()
        self._build_history_tab()

    def _build_local_tab(self):
        self.tab_local.grid_columnconfigure(0, weight=1)
        self.tab_local.grid_columnconfigure(1, weight=1)
        self.tab_local.grid_rowconfigure(3, weight=1)

        self.local_language = ctk.StringVar(value="Python")
        self.local_analysis_type_label = ctk.StringVar(value=ANALYSIS_TYPE_LABELS[AnalysisType.FULL])

        ctk.CTkLabel(self.tab_local, text="Язык:").grid(row=0, column=0, sticky="w", padx=8, pady=(8, 2))
        ctk.CTkOptionMenu(self.tab_local, variable=self.local_language, values=sorted(set(LANGUAGE_MAP.values()))).grid(
            row=1, column=0, sticky="ew", padx=8, pady=4
        )
        ctk.CTkLabel(self.tab_local, text="Тип анализа:").grid(row=0, column=1, sticky="w", padx=8, pady=(8, 2))
        ctk.CTkOptionMenu(
            self.tab_local,
            variable=self.local_analysis_type_label,
            values=list(ANALYSIS_TYPE_LABELS.values()),
        ).grid(row=1, column=1, sticky="ew", padx=8, pady=4)

        self.local_code = ctk.CTkTextbox(self.tab_local, wrap="none")
        self.local_code.grid(row=3, column=0, sticky="nsew", padx=8, pady=8)
        self.local_result = ctk.CTkTextbox(self.tab_local, wrap="word")
        self.local_result.grid(row=3, column=1, sticky="nsew", padx=8, pady=8)

        btns = ctk.CTkFrame(self.tab_local, fg_color="transparent")
        btns.grid(row=4, column=0, columnspan=2, sticky="ew", padx=8, pady=8)
        btns.grid_columnconfigure((0, 1, 2, 3), weight=1)
        ctk.CTkButton(btns, text="Открыть файл", command=self._open_local_file).grid(row=0, column=0, padx=4, sticky="ew")
        ctk.CTkButton(btns, text="Анализировать", command=self._analyze_local).grid(row=0, column=1, padx=4, sticky="ew")
        ctk.CTkButton(btns, text="Очистить", command=self._clear_local).grid(row=0, column=2, padx=4, sticky="ew")
        ctk.CTkButton(btns, text="Сохранить результат в .txt", command=self._save_local_result).grid(row=0, column=3, padx=4, sticky="ew")

    def _build_git_tab(self):
        self.tab_git.grid_columnconfigure(0, weight=1)
        self.tab_git.grid_columnconfigure(1, weight=1)
        self.tab_git.grid_rowconfigure(6, weight=1)

        self.git_url = ctk.StringVar()
        self.git_branch = ctk.StringVar()
        self.git_path = ctk.StringVar()
        self.git_token = ctk.StringVar()
        self.git_analysis_type_label = ctk.StringVar(value=ANALYSIS_TYPE_LABELS[AnalysisType.FULL])

        ctk.CTkLabel(self.tab_git, text="URL репозитория:").grid(row=0, column=0, columnspan=2, sticky="w", padx=8, pady=(8, 2))
        ctk.CTkEntry(self.tab_git, textvariable=self.git_url, placeholder_text="https://github.com/owner/repo").grid(
            row=1, column=0, columnspan=2, sticky="ew", padx=8, pady=4
        )

        ctk.CTkEntry(self.tab_git, textvariable=self.git_branch, placeholder_text="Ветка (например main)").grid(
            row=2, column=0, sticky="ew", padx=8, pady=4
        )
        ctk.CTkEntry(self.tab_git, textvariable=self.git_path, placeholder_text="Путь к файлу (опционально)").grid(
            row=2, column=1, sticky="ew", padx=8, pady=4
        )
        ctk.CTkEntry(self.tab_git, textvariable=self.git_token, placeholder_text="Token (опционально)", show="*").grid(
            row=3, column=0, sticky="ew", padx=8, pady=4
        )
        ctk.CTkOptionMenu(
            self.tab_git,
            variable=self.git_analysis_type_label,
            values=list(ANALYSIS_TYPE_LABELS.values()),
        ).grid(row=3, column=1, sticky="ew", padx=8, pady=4)

        self.git_files = ctk.CTkTextbox(self.tab_git, wrap="none")
        self.git_files.grid(row=6, column=0, sticky="nsew", padx=8, pady=8)
        self.git_result = ctk.CTkTextbox(self.tab_git, wrap="word")
        self.git_result.grid(row=6, column=1, sticky="nsew", padx=8, pady=8)

        btns = ctk.CTkFrame(self.tab_git, fg_color="transparent")
        btns.grid(row=7, column=0, columnspan=2, sticky="ew", padx=8, pady=8)
        btns.grid_columnconfigure((0, 1, 2), weight=1)
        ctk.CTkButton(btns, text="Загрузить дерево файлов", command=self._load_repo_tree).grid(row=0, column=0, padx=4, sticky="ew")
        ctk.CTkButton(btns, text="Анализ 1 файла", command=self._analyze_repo_file).grid(row=0, column=1, padx=4, sticky="ew")
        ctk.CTkButton(btns, text="Проверить токен", command=self._validate_git_token).grid(row=0, column=2, padx=4, sticky="ew")

    def _build_history_tab(self):
        self.tab_history.grid_columnconfigure(0, weight=0)
        self.tab_history.grid_columnconfigure(1, weight=1)
        self.tab_history.grid_rowconfigure(1, weight=1)

        tools = ctk.CTkFrame(self.tab_history, fg_color="transparent")
        tools.grid(row=0, column=0, columnspan=2, sticky="ew", padx=8, pady=8)
        tools.grid_columnconfigure((0, 1, 2), weight=1)
        ctk.CTkButton(tools, text="Обновить историю", command=self._refresh_history).grid(row=0, column=0, padx=4, sticky="ew")
        ctk.CTkButton(tools, text="Очистить историю", command=self._clear_history).grid(row=0, column=1, padx=4, sticky="ew")
        ctk.CTkButton(tools, text="Экспорт всей истории в JSON", command=self._export_history_json).grid(row=0, column=2, padx=4, sticky="ew")

        self.history_list_frame = ctk.CTkScrollableFrame(self.tab_history, width=360)
        self.history_list_frame.grid(row=1, column=0, sticky="nsw", padx=(8, 4), pady=8)

        self.history_detail = ctk.CTkTextbox(self.tab_history, wrap="word")
        self.history_detail.grid(row=1, column=1, sticky="nsew", padx=(4, 8), pady=8)

    def _set_status(self, text: str):
        self.status_label.configure(text=f"Статус: {text}")

    def _format_items(self, value):
        if value is None:
            return []
        if isinstance(value, str):
            return [value]
        if isinstance(value, dict):
            desc = value.get("description") or value.get("message") or json.dumps(value, ensure_ascii=False)
            sev = value.get("severity")
            return [f"{desc} ({sev})" if sev else desc]
        if isinstance(value, list):
            out = []
            for item in value:
                if isinstance(item, dict):
                    desc = item.get("description") or item.get("message") or json.dumps(item, ensure_ascii=False)
                    sev = item.get("severity")
                    out.append(f"- {desc} ({sev})" if sev else f"- {desc}")
                else:
                    out.append(f"- {item}")
            return out
        return [str(value)]

    def _format_result(self, raw: str, language: str):
        try:
            data = json.loads(raw)
        except Exception:
            return raw
        if isinstance(data, list):
            return "Результат пришел списком:\n" + "\n".join(self._format_items(data))
        if not isinstance(data, dict):
            return str(data)
        if data.get("error"):
            return f"Ошибка модели:\n{data.get('error')}\n\n{data.get('details', '')}"

        parts = [f"Язык: {language}", ""]
        score_line = (
            f"Сложность: {data.get('complexity_score', 0)}/10 | "
            f"Сопровождаемость: {data.get('maintainability_score', 0)}/10 | "
            f"Безопасность: {data.get('security_score', 0)}/10 | "
            f"Производительность: {data.get('performance_score', 0)}/10"
        )
        parts.append(score_line)
        parts.append("")
        sections = [
            ("Ошибки", "errors"),
            ("Проблемы стиля", "style_issues"),
            ("Риски безопасности", "security_risks"),
            ("Проблемы производительности", "performance_issues"),
            ("Лучшие практики", "best_practices"),
            ("Примеры улучшенного кода", "code_suggestions"),
        ]
        for title, key in sections:
            items = self._format_items(data.get(key))
            if items:
                parts.append(f"=== {title} ===")
                parts.extend(items)
                parts.append("")
        if data.get("summary"):
            parts.append("=== Резюме ===")
            parts.append(str(data["summary"]))
        return "\n".join(parts).strip()

    def _open_local_file(self):
        path = filedialog.askopenfilename(title="Открыть файл кода")
        if not path:
            return
        with open(path, "r", encoding="utf-8") as f:
            code = f.read()
        self.local_code.delete("1.0", "end")
        self.local_code.insert("1.0", code)
        self.local_language.set(LANGUAGE_MAP.get(os.path.splitext(path)[1].lower(), "Python"))

    def _clear_local(self):
        self.local_code.delete("1.0", "end")
        self.local_result.delete("1.0", "end")

    def _save_local_result(self):
        text = self.local_result.get("1.0", "end").strip()
        if not text:
            messagebox.showinfo("Пусто", "Нет результата для сохранения.")
            return
        path = filedialog.asksaveasfilename(defaultextension=".txt", filetypes=[("Text", "*.txt")])
        if not path:
            return
        with open(path, "w", encoding="utf-8") as f:
            f.write(text)
        messagebox.showinfo("Готово", f"Сохранено: {path}")

    def _analyze_local(self):
        code = self.local_code.get("1.0", "end").strip()
        if not code:
            messagebox.showwarning("Внимание", "Вставьте код для анализа.")
            return
        analysis_type = LABEL_TO_ANALYSIS_TYPE[self.local_analysis_type_label.get()]
        sub = CodeSubmission(code=code, language=self.local_language.get(), analysis_type=analysis_type)
        self.local_result.delete("1.0", "end")
        self.local_result.insert("1.0", "Выполняется анализ...\n")
        self._set_status("идет локальный анализ")
        self._run_bg(self._analyze_submission(sub, "local", self.local_result))

    async def _analyze_submission(self, sub: CodeSubmission, source: str, output):
        raw = await self.llm_service.analyze_code_async(sub)
        pretty = self._format_result(raw, sub.language)
        output.delete("1.0", "end")
        output.insert("1.0", pretty)
        await self.history_service.save_analysis(
            sub.code,
            sub.language,
            raw,
            analysis_type=sub.analysis_type,
            source=source,
        )
        self.after(0, self._refresh_history)
        self.after(0, lambda: self._set_status("готово"))

    async def _resolve_repo(self, url: str, token: str):
        if "github.com" in url.lower():
            owner, repo, branch, path = self.github_service.parse_github_url(url)
            if not branch:
                branch = await self.github_service.get_default_branch(owner, repo, token or None)
            return "github", owner, repo, branch, path
        if "gitlab.com" in url.lower():
            owner, repo, branch, path = self.gitlab_service.parse_gitlab_url(url)
            if not branch:
                branch = await self.gitlab_service.get_default_branch(owner, repo, token or None)
            return "gitlab", owner, repo, branch, path
        raise ValueError("Поддерживаются только GitHub/GitLab")

    def _load_repo_tree(self):
        url = self.git_url.get().strip()
        if not url:
            messagebox.showwarning("Внимание", "Введите URL репозитория.")
            return
        self._set_status("загрузка дерева репозитория")
        self._run_bg(self._load_repo_tree_task(url, self.git_token.get().strip()))

    async def _load_repo_tree_task(self, url, token):
        try:
            platform, owner, repo, branch, path = await self._resolve_repo(url, token)
            branch = self.git_branch.get().strip() or branch
            path = self.git_path.get().strip() or path
            files = await (
                self.github_service.get_directory_contents(owner, repo, path, branch, token or None)
                if platform == "github"
                else self.gitlab_service.get_directory_contents(owner, repo, path, branch, token or None)
            )
            text = "\n".join([f"[{f.type}] {f.path or f.name}" for f in files]) or "Файлы не найдены."
        except Exception as exc:
            text = f"Ошибка: {exc}"
        self.after(0, lambda: (self.git_files.delete("1.0", "end"), self.git_files.insert("1.0", text), self._set_status("готово")))

    def _analyze_repo_file(self):
        url = self.git_url.get().strip()
        if not url:
            messagebox.showwarning("Внимание", "Введите URL репозитория.")
            return
        self._set_status("анализ файла из репозитория")
        self._run_bg(self._analyze_repo_file_task(url, self.git_token.get().strip()))

    async def _analyze_repo_file_task(self, url, token):
        try:
            platform, owner, repo, branch, path = await self._resolve_repo(url, token)
            branch = self.git_branch.get().strip() or branch
            path = self.git_path.get().strip() or path
            if not path:
                files = await (
                    self.github_service.get_directory_contents(owner, repo, "", branch, token or None)
                    if platform == "github"
                    else self.gitlab_service.get_directory_contents(owner, repo, "", branch, token or None)
                )
                code_files = [f for f in files if f.type == "file" and os.path.splitext(f.name)[1].lower() in LANGUAGE_MAP]
                if not code_files:
                    raise ValueError("Не найден файл для анализа")
                path = code_files[0].path
            content = await (
                self.github_service.get_file_content(owner, repo, path, branch, token or None)
                if platform == "github"
                else self.gitlab_service.get_file_content(owner, repo, path, branch, token or None)
            )
            lang = LANGUAGE_MAP.get(os.path.splitext(path)[1].lower(), "Python")
            analysis_type = LABEL_TO_ANALYSIS_TYPE[self.git_analysis_type_label.get()]
            raw = await self.llm_service.analyze_code_async(CodeSubmission(code=content, language=lang, analysis_type=analysis_type))
            pretty = self._format_result(raw, lang)
            await self.history_service.save_analysis(content, lang, raw, analysis_type=analysis_type, source=f"{platform}:{owner}/{repo}:{path}")
            self.after(0, self._refresh_history)
            text = f"Файл: {path}\n\n{pretty}"
        except Exception as exc:
            text = f"Ошибка: {exc}"
        self.after(0, lambda: (self.git_result.delete("1.0", "end"), self.git_result.insert("1.0", text), self._set_status("готово")))

    def _validate_git_token(self):
        token = self.git_token.get().strip()
        url = self.git_url.get().strip()
        if not token or not url:
            messagebox.showwarning("Внимание", "Введите URL и токен.")
            return
        self._run_bg(self._validate_git_token_task(url, token))

    async def _validate_git_token_task(self, url, token):
        try:
            if "github.com" in url.lower():
                res = await self.github_service.validate_token(token)
            elif "gitlab.com" in url.lower():
                res = await self.gitlab_service.validate_token(token)
            else:
                raise ValueError("Не удалось определить платформу.")
            txt = f"Токен валиден. Пользователь: {res.user_name}" if res.is_valid else f"Токен невалиден: {res.error_message}"
            self.after(0, lambda: messagebox.showinfo("Проверка токена", txt))
        except Exception as exc:
            self.after(0, lambda: messagebox.showerror("Ошибка", str(exc)))

    def _render_history_buttons(self):
        for b in self.history_buttons:
            b.destroy()
        self.history_buttons.clear()
        for idx, item in enumerate(self.last_history_records):
            title = f"#{item.id} | {item.language} | {item.analysis_type}"
            subtitle = f"{item.timestamp} | {item.source}"
            btn = ctk.CTkButton(
                self.history_list_frame,
                text=f"{title}\n{subtitle}",
                anchor="w",
                height=56,
                command=lambda rec=item: self._show_history_record(rec),
            )
            btn.grid(row=idx, column=0, sticky="ew", padx=4, pady=4)
            self.history_buttons.append(btn)

    def _show_history_record(self, rec: AnalysisRecord):
        pretty = self._format_result(rec.result, rec.language)
        self.history_detail.delete("1.0", "end")
        self.history_detail.insert(
            "1.0",
            f"ID: {rec.id}\nДата: {rec.timestamp}\nЯзык: {rec.language}\nТип: {rec.analysis_type}\nИсточник: {rec.source}\n\n{pretty}",
        )

    def _refresh_history(self):
        async def task():
            records = await self.history_service.get_history(limit=150)
            self.last_history_records = records
            self.after(0, self._render_history_buttons)
            self.after(0, lambda: self._set_status("готово"))
        self._run_bg(task())

    def _clear_history(self):
        if not messagebox.askyesno("Подтверждение", "Очистить всю историю?"):
            return
        async def task():
            await self.history_service.clear_history()
            self.after(0, self._refresh_history)
        self._run_bg(task())

    def _export_history_json(self):
        path = filedialog.asksaveasfilename(defaultextension=".json", filetypes=[("JSON", "*.json")])
        if not path:
            return
        async def task():
            records = await self.history_service.get_history(limit=500)
            payload = [
                {
                    "id": r.id,
                    "timestamp": str(r.timestamp),
                    "language": r.language,
                    "analysis_type": r.analysis_type,
                    "source": r.source,
                    "result": r.result,
                    "code": r.code,
                }
                for r in records
            ]
            with open(path, "w", encoding="utf-8") as f:
                json.dump(payload, f, ensure_ascii=False, indent=2)
            self.after(0, lambda: messagebox.showinfo("Готово", f"Экспортировано: {path}"))
        self._run_bg(task())

    def _run_bg(self, coro):
        def run():
            asyncio.run(coro)
        threading.Thread(target=run, daemon=True).start()


if __name__ == "__main__":
    app = CodeQualityCheckerApp()
    app.mainloop()
