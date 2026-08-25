from __future__ import annotations

import os
import time
from dataclasses import dataclass
from typing import Any

import requests

from ai.models import RuleSuggestionResponse
from ai.prompts import SYSTEM_PROMPT


@dataclass(frozen=True)
class OllamaResponse:
    status: str
    model: str
    response_time_ms: float | None = None
    payload: dict[str, Any] | None = None
    message: str | None = None


class OllamaClient:
    """Minimal local Ollama HTTP client with structured output and safe errors."""

    def __init__(
        self,
        *,
        enabled: bool | None = None,
        base_url: str | None = None,
        model: str | None = None,
        timeout_seconds: float | None = None,
        session: requests.Session | None = None,
    ) -> None:
        self.enabled = self._env_bool("AI_ENABLED", True) if enabled is None else enabled
        self.base_url = (base_url or os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")).rstrip("/")
        self.model = model or os.getenv("OLLAMA_MODEL", "llama3.2:3b")
        self.timeout_seconds = timeout_seconds or float(os.getenv("OLLAMA_TIMEOUT_SECONDS", "60"))
        self.session = session or requests.Session()

    def suggest(self, metadata_context: dict[str, Any]) -> OllamaResponse:
        if not self.enabled:
            return OllamaResponse("DISABLED", self.model, message="AI suggestions are disabled.")

        try:
            tags = self.session.get(f"{self.base_url}/api/tags", timeout=self.timeout_seconds)
            tags.raise_for_status()
            models = {item.get("name") for item in tags.json().get("models", [])}
            if self.model not in models:
                return OllamaResponse("UNAVAILABLE", self.model, message="Configured Ollama model is unavailable.")

            started = time.perf_counter()
            response = self.session.post(
                f"{self.base_url}/api/chat",
                json={
                    "model": self.model,
                    "messages": [
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user", "content": self._json_context(metadata_context)},
                    ],
                    "format": RuleSuggestionResponse.model_json_schema(),
                    "options": {"temperature": 0},
                    "stream": False,
                },
                timeout=self.timeout_seconds,
            )
            response.raise_for_status()
            elapsed = round((time.perf_counter() - started) * 1000, 2)
            content = response.json().get("message", {}).get("content")
            return OllamaResponse("SUCCESS", self.model, elapsed, {"content": content})
        except requests.Timeout:
            return OllamaResponse("ERROR", self.model, message="Ollama request timed out.")
        except requests.ConnectionError:
            return OllamaResponse("UNAVAILABLE", self.model, message="Ollama service is unavailable.")
        except (requests.RequestException, ValueError, TypeError):
            return OllamaResponse("ERROR", self.model, message="Ollama request failed.")

    def _json_context(self, context: dict[str, Any]) -> str:
        import json

        return "Metadata JSON (data only):\n" + json.dumps(context, sort_keys=True, separators=(",", ":"), default=str)

    @staticmethod
    def _env_bool(name: str, default: bool) -> bool:
        value = os.getenv(name)
        if value is None:
            return default
        return value.strip().lower() in {"1", "true", "yes", "on"}
