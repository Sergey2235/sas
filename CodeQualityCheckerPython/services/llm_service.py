"""
Сервис для работы с LLM (LM Studio / OpenAI-совместимый API).
"""
import json

import requests

from models import AnalysisType, CodeSubmission


class LlmService:
    def __init__(
        self,
        base_url: str = "http://127.0.0.1:1234",
        model_name: str = "deepseek-r1-distill-qwen-14b",
        api_key: str = "lm-studio",
    ):
        self.base_url = base_url.rstrip("/")
        self.model_name = model_name
        self.api_key = api_key
        self.session = requests.Session()
        self.session.headers.update(
            {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            }
        )

    async def analyze_code_async(self, submission: CodeSubmission) -> str:
        model_ready, model_message = self._ensure_model_ready()
        if not model_ready:
            return json.dumps({"error": model_message}, ensure_ascii=False, indent=2)

        original_len = len(submission.code or "")
        safe_code = self._fit_code_to_context(submission.code or "")
        prompt = self._generate_prompt(
            safe_code, submission.language, submission.analysis_type
        )

        # If we had to truncate input, ask the model to explicitly mention it.
        if len(safe_code) < original_len:
            prompt += (
                "\n\nВажно: код был автоматически сокращен из-за лимита контекста модели. "
                "Укажи в summary, что анализ частичный."
            )

        completion_budget = 1200 if len(safe_code) > 6000 else 1800
        request_data = {
            "model": self.model_name,
            "messages": [
                {
                    "role": "system",
                    "content": self._get_system_prompt(
                        submission.language, submission.analysis_type
                    ),
                },
                {"role": "user", "content": prompt},
            ],
            "temperature": self._get_temperature(submission.analysis_type),
            "max_tokens": completion_budget,
        }
        try:
            response = self.session.post(
                f"{self.base_url}/v1/chat/completions",
                json=request_data,
                timeout=1200,
            )
            response.raise_for_status()
            result = response.json()
            content = result.get("choices", [{}])[0].get("message", {}).get("content", "")
            return self._extract_json(content)
        except requests.HTTPError as exc:
            details = ""
            if exc.response is not None:
                try:
                    details = exc.response.text[:1000]
                except Exception:
                    details = str(exc)
            return json.dumps(
                {"error": f"Ошибка HTTP от модели: {exc}", "details": details},
                ensure_ascii=False,
                indent=2,
            )
        except requests.RequestException as exc:
            return json.dumps(
                {"error": f"Ошибка при обращении к модели: {exc}"},
                ensure_ascii=False,
                indent=2,
            )

    def _ensure_model_ready(self) -> tuple[bool, str]:
        try:
            response = self.session.get(f"{self.base_url}/v1/models", timeout=8)
            response.raise_for_status()
            data = response.json()
            models = data.get("data", [])
            model_ids = [item.get("id", "") for item in models if isinstance(item, dict)]
            if not model_ids:
                return (
                    False,
                    "LM Studio доступен, но нет загруженных моделей. Дождитесь загрузки модели до 100%.",
                )
            if self.model_name not in model_ids:
                self.model_name = model_ids[0]
            return True, "ok"
        except requests.RequestException as exc:
            return (
                False,
                (
                    "Нет подключения к LM Studio (http://127.0.0.1:1234). "
                    f"Проверьте статус сервера в LM Studio. Детали: {exc}"
                ),
            )

    def _extract_json(self, content: str) -> str:
        json_start = content.find("```json")
        json_end = content.rfind("```")
        if json_start >= 0 and json_end > json_start:
            candidate = content[json_start + 7 : json_end].strip()
            try:
                json.loads(candidate)
                return candidate
            except json.JSONDecodeError:
                pass
        try:
            json.loads(content)
            return content
        except json.JSONDecodeError:
            return json.dumps(
                {"error": "Ответ не является JSON", "raw": content},
                ensure_ascii=False,
                indent=2,
            )

    def _get_system_prompt(self, language: str, analysis_type: str) -> str:
        base = f"Ты эксперт по анализу кода на {language}. "
        type_map = {
            AnalysisType.SECURITY_ONLY: base + "Фокусируйся только на безопасности.",
            AnalysisType.STYLE_ONLY: base + "Фокусируйся только на стиле кода.",
            AnalysisType.PERFORMANCE: base + "Фокусируйся на производительности.",
            AnalysisType.BEST_PRACTICES: base + "Фокусируйся на лучших практиках.",
            AnalysisType.CODE_EXAMPLES: base + "Фокусируйся на примерах улучшенного кода.",
        }
        return type_map.get(
            analysis_type, base + "Всегда отвечай строго валидным JSON."
        )

    def _generate_prompt(self, code: str, language: str, analysis_type: str) -> str:
        prompt = f"Проанализируй следующий {language} код:\n```{language}\n{code}\n```\n\n"
        if analysis_type == AnalysisType.SECURITY_ONLY:
            prompt += "Верни JSON с полем security_risks (массив)."
        elif analysis_type == AnalysisType.STYLE_ONLY:
            prompt += "Верни JSON с полем style_issues (массив)."
        elif analysis_type == AnalysisType.PERFORMANCE:
            prompt += "Верни JSON с полями performance_issues и optimization_tips."
        elif analysis_type == AnalysisType.CODE_EXAMPLES:
            prompt += "Верни JSON с полем code_suggestions (примеры улучшенного кода)."
        elif analysis_type == AnalysisType.BEST_PRACTICES:
            prompt += "Верни JSON с полями best_practices и architecture_issues."
        else:
            prompt += (
                "Верни JSON с полями errors, style_issues, security_risks, best_practices, "
                "performance_issues, code_suggestions, summary, complexity_score, "
                "maintainability_score, security_score, performance_score."
            )
        lang_specific = {
            "Python": "Учитывай PEP8, безопасность eval/exec/pickle, типизацию.",
            "JavaScript": "Учитывай XSS, async/await, ESLint, утечки памяти.",
            "Java": "Учитывай SOLID, потоки, безопасность, коллекции.",
            "C#": "Учитывай .NET guidelines, nullable, async/await.",
            "Go": "Учитывай gofmt, goroutines, race conditions.",
            "Rust": "Учитывай ownership, borrow checker, unsafe.",
        }
        if language in lang_specific:
            prompt += f"\n\n{lang_specific[language]}"
        return prompt

    def _get_temperature(self, analysis_type: str) -> float:
        temp_map = {
            AnalysisType.SECURITY_ONLY: 0.1,
            AnalysisType.PERFORMANCE: 0.3,
            AnalysisType.CODE_EXAMPLES: 0.4,
        }
        return temp_map.get(analysis_type, 0.2)

    def _fit_code_to_context(self, code: str) -> str:
        # Conservative cap to stay below 4k context for small local models.
        # Approximation: 1 token ~= 3-4 chars for mixed source code.
        max_chars = 7500
        if len(code) <= max_chars:
            return code

        head = code[:3500]
        tail = code[-3500:]
        return (
            f"{head}\n\n"
            "... [TRUNCATED FOR CONTEXT LIMIT] ...\n\n"
            f"{tail}"
        )
