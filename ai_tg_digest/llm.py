from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import httpx

from ai_tg_digest.utils import robust_json_loads


class OpenAICompatClient:
    def __init__(self, base_url: str, api_key: str, model: str):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.model = model

    def complete_json(self, system_prompt: str, user_prompt: str, temperature: float = 0.1, retries: int = 2) -> dict[str, Any]:
        payload = {
            "model": self.model,
            "temperature": temperature,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        }
        headers = {"Authorization": f"Bearer {self.api_key}"}
        with httpx.Client(timeout=60.0) as client:
            last_error: Exception | None = None
            for _ in range(retries + 1):
                try:
                    response = client.post(f"{self.base_url}/chat/completions", headers=headers, json=payload)
                    response.raise_for_status()
                    text = response.json()["choices"][0]["message"]["content"]
                    return robust_json_loads(text)
                except Exception as e:  # noqa: BLE001
                    last_error = e
            raise RuntimeError(f"LLM JSON completion failed: {last_error}")


def load_prompt(name: str) -> tuple[str, str]:
    content = Path("prompts") .joinpath(name).read_text(encoding="utf-8")
    parts = content.split("\nUSER:\n", 1)
    system = parts[0].replace("SYSTEM:\n", "", 1).strip()
    user = parts[1].strip()
    return system, user


def render(template: str, **kwargs: Any) -> str:
    return template.format(**{k: json.dumps(v, ensure_ascii=False) if isinstance(v, (list, dict)) else v for k, v in kwargs.items()})
