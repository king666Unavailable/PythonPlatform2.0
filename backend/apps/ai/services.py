"""Provider-neutral AI service with MySQL conversation persistence."""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from typing import Any

from django.conf import settings


class AIProviderNotConfigured(RuntimeError):
    pass


class AIProviderUnavailable(RuntimeError):
    pass


class AIClient:
    def complete(self, messages: list[dict[str, str]], temperature: float = 0.2) -> str:
        if not settings.AI_API_URL or not settings.AI_API_KEY or not settings.AI_MODEL:
            raise AIProviderNotConfigured
        endpoint = settings.AI_API_URL.rstrip("/")
        if not endpoint.endswith("/chat/completions"):
            endpoint += "/chat/completions"
        request = urllib.request.Request(
            endpoint,
            data=json.dumps({"model": settings.AI_MODEL, "messages": messages, "temperature": temperature}, ensure_ascii=False).encode("utf-8"),
            headers={"Authorization": f"Bearer {settings.AI_API_KEY}", "Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=settings.AI_API_TIMEOUT) as response:
                payload = json.loads(response.read().decode("utf-8"))
            return str(payload["choices"][0]["message"]["content"])
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, ValueError, KeyError, IndexError) as exc:
            raise AIProviderUnavailable from exc


class AIService:
    def answer(self, history: list[dict[str, str]], question: str) -> str:
        clean_history = [{"role": item["role"], "content": item["content"]} for item in history if item.get("role") in {"user", "assistant", "system"}]
        return AIClient().complete([*clean_history, {"role": "user", "content": question}])

    def generate_questions(self, prompt: str) -> Any:
        content = AIClient().complete([
            {"role": "system", "content": "你是教学题目生成器。只返回 JSON 数组，每项包含 title,type_code,content,answer,analysis,difficulty,importance,point_titles。"},
            {"role": "user", "content": prompt},
        ])
        content = content.strip()
        if content.startswith("```"):
            content = content.split("\n", 1)[1].rsplit("```", 1)[0]
        try:
            result = json.loads(content)
        except ValueError as exc:
            raise AIProviderUnavailable("AI 返回不是合法 JSON") from exc
        return result if isinstance(result, list) else [result]
