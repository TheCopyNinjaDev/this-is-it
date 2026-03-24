from __future__ import annotations

import json
import logging
from collections.abc import Sequence

import httpx

logger = logging.getLogger(__name__)


class OpenRouterDateGenerator:
    def __init__(self, *, api_key: str | None, model: str, base_url: str, proxy_urls: list[str | None] | None = None) -> None:
        self.api_key = api_key
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.proxy_urls = proxy_urls if proxy_urls is not None else [None]

    @property
    def enabled(self) -> bool:
        return bool(self.api_key)

    @staticmethod
    def _detect_target_language(prompts: Sequence[dict[str, str]]) -> str:
        joined = " ".join(prompt["text"] for prompt in prompts).strip()
        cyrillic_count = sum(1 for char in joined if "а" <= char.lower() <= "я" or char.lower() == "ё")
        latin_count = sum(1 for char in joined if "a" <= char.lower() <= "z")

        if cyrillic_count > latin_count:
            return "Russian"
        if latin_count > 0:
            return "English"
        return "the same language as the input"

    async def _call_api(self, prompts: Sequence[dict[str, str]], proxy_url: str | None) -> list[dict[str, str]]:
        target_language = self._detect_target_language(prompts)
        prompt_blocks = "\n".join(
            f"- {prompt['name']}: {prompt['text']}"
            for prompt in prompts
        )
        system_prompt = (
            "You create date ideas for two people. "
            "Return strictly valid JSON with this shape: "
            '{"options":[{"title":"...","description":"...","category":"...","vibe":"...","reason":"..."}]}. '
            "Exactly 10 options. No markdown. No extra text. "
            "Each option must be specific, realistic, romantic or fun, and blend both participants' wishes. "
            f"Write every field strictly in {target_language}. "
            "Do not leave category or vibe in English if the input language is different."
        )
        user_prompt = (
            "Create 10 date ideas based on these participant preferences:\n"
            f"{prompt_blocks}\n\n"
            "Requirements:\n"
            "- Each option should feel different from the others.\n"
            "- Keep descriptions concise but vivid.\n"
            "- category should be a short natural label in the target language.\n"
            "- vibe should be a short natural mood label in the target language.\n"
            "- reason should explain in one sentence why this option fits both people.\n"
            f"- Use {target_language} for title, description, category, vibe, and reason.\n"
        )

        async with httpx.AsyncClient(timeout=45.0, proxy=proxy_url) as client:
            response = await client.post(
                f"{self.base_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": self.model,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                    "temperature": 0.9,
                },
            )
            response.raise_for_status()
            logger.info("OpenRouter generation request completed via proxy=%s", bool(proxy_url))

        payload = response.json()
        content = payload["choices"][0]["message"]["content"]
        options_payload = json.loads(content)
        options = options_payload.get("options")
        if not isinstance(options, list) or len(options) != 10:
            raise RuntimeError("OpenRouter returned invalid custom date options payload")

        normalized: list[dict[str, str]] = []
        default_category = "Свидание" if target_language == "Russian" else "Date"
        default_vibe = "Особенный" if target_language == "Russian" else "Personal"
        for option in options:
            if not isinstance(option, dict):
                raise RuntimeError("OpenRouter returned malformed option entry")
            normalized.append(
                {
                    "title": str(option.get("title", "")).strip(),
                    "description": str(option.get("description", "")).strip(),
                    "category": str(option.get("category", "")).strip() or default_category,
                    "vibe": str(option.get("vibe", "")).strip() or default_vibe,
                    "reason": str(option.get("reason", "")).strip(),
                }
            )

        if any(not item["title"] or not item["description"] for item in normalized):
            raise RuntimeError("OpenRouter returned empty custom date fields")

        return normalized

    async def generate_options(self, prompts: Sequence[dict[str, str]]) -> list[dict[str, str]]:
        if not self.api_key:
            raise RuntimeError("OPENROUTER_API_KEY is not configured")

        last_error: Exception | None = None
        for proxy_url in self.proxy_urls:
            try:
                return await self._call_api(prompts, proxy_url)
            except Exception as exc:
                logger.warning("OpenRouter attempt failed via proxy=%s: %s", bool(proxy_url), exc)
                last_error = exc

        raise last_error or RuntimeError("All proxy attempts failed for OpenRouter generation")
