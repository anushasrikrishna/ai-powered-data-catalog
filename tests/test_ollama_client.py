from __future__ import annotations

import json
import unittest
from unittest.mock import MagicMock

import requests
from pydantic import ValidationError

from ai.models import RuleSuggestionResponse
from ai.ollama_client import OllamaClient


class FakeResponse:
    def __init__(self, payload, status_code=200):
        self._payload = payload
        self.status_code = status_code

    def json(self):
        return self._payload

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError("request failed")


class TestOllamaClient(unittest.TestCase):
    def test_structured_response_schema_requires_suggestions(self) -> None:
        schema = RuleSuggestionResponse.model_json_schema()

        self.assertEqual(schema["required"], ["suggestions"])
        self.assertEqual(
            RuleSuggestionResponse.model_validate({"suggestions": []}).suggestions,
            [],
        )
        with self.assertRaises(ValidationError):
            RuleSuggestionResponse.model_validate({})

    def test_ai_enabled_environment_forms(self) -> None:
        import os
        from unittest.mock import patch

        for value in ("true", "TRUE", "True", "1", "yes", "YES"):
            with self.subTest(value=value), patch.dict(os.environ, {"AI_ENABLED": value}):
                self.assertTrue(OllamaClient(session=MagicMock()).enabled)
        for value in ("false", "FALSE", "0", "no"):
            with self.subTest(value=value), patch.dict(os.environ, {"AI_ENABLED": value}):
                self.assertFalse(OllamaClient(session=MagicMock()).enabled)

    def test_disabled_bypasses_ollama(self) -> None:
        session = MagicMock()
        result = OllamaClient(enabled=False, session=session).suggest({"table_name": "orders"})

        self.assertEqual(result.status, "DISABLED")
        session.get.assert_not_called()
        session.post.assert_not_called()

    def test_structured_request_uses_configured_options(self) -> None:
        session = MagicMock()
        session.get.return_value = FakeResponse({"models": [{"name": "llama3.2:3b"}]})
        content = json.dumps({"suggestions": []})
        session.post.return_value = FakeResponse({"message": {"content": content}})
        client = OllamaClient(
            enabled=True,
            base_url="http://localhost:11434",
            model="llama3.2:3b",
            timeout_seconds=12,
            session=session,
        )

        result = client.suggest({"table_name": "orders"})

        self.assertEqual(result.status, "SUCCESS")
        self.assertIsNotNone(result.response_time_ms)
        request = session.post.call_args.kwargs
        self.assertEqual(request["timeout"], 12)
        self.assertFalse(request["json"]["stream"])
        self.assertEqual(request["json"]["options"]["temperature"], 0)
        self.assertIsInstance(request["json"]["format"], dict)

    def test_unavailable_model_and_service_are_safe(self) -> None:
        missing_model = MagicMock()
        missing_model.get.return_value = FakeResponse({"models": []})
        missing_result = OllamaClient(enabled=True, session=missing_model).suggest({})
        self.assertEqual(missing_result.status, "UNAVAILABLE")
        self.assertIn("model", missing_result.message.lower())

        unavailable = MagicMock()
        unavailable.get.side_effect = requests.ConnectionError()
        self.assertEqual(
            OllamaClient(enabled=True, session=unavailable).suggest({}).status,
            "UNAVAILABLE",
        )

    def test_timeout_is_translated(self) -> None:
        session = MagicMock()
        session.get.return_value = FakeResponse({"models": [{"name": "llama3.2:3b"}]})
        session.post.side_effect = requests.Timeout()

        result = OllamaClient(enabled=True, session=session).suggest({})

        self.assertEqual(result.status, "ERROR")
        self.assertIn("timed out", result.message)
