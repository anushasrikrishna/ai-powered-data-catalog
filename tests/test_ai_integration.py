from __future__ import annotations

import os
import unittest

from ai.model_comparison import build_synthetic_documentation, compare_models
from ai.ollama_client import OllamaClient
from ai.quality_rule_suggester import QualityRuleSuggester


@unittest.skipUnless(
    os.getenv("RUN_OLLAMA_INTEGRATION_TESTS") == "1",
    "Set RUN_OLLAMA_INTEGRATION_TESTS=1 to run local Ollama integration.",
)
class TestOllamaIntegration(unittest.TestCase):
    def test_structured_suggestion_smoke(self) -> None:
        documentation = build_synthetic_documentation()
        result = QualityRuleSuggester(OllamaClient()).suggest_for_table(documentation)
        self.assertEqual(result.status, "SUCCESS")
        self.assertIsNotNone(result.response_time_ms)
        self.assertLessEqual(len(result.suggestions), 8)
        columns = {column.column_name for column in documentation.columns}
        self.assertTrue(all(item.rule.column in columns for item in result.suggestions))


class TestModelComparisonGate(unittest.TestCase):
    def test_comparison_is_disabled_by_default(self) -> None:
        original = os.environ.pop("RUN_AI_MODEL_COMPARISON", None)
        try:
            self.assertEqual(compare_models(), [])
        finally:
            if original is not None:
                os.environ["RUN_AI_MODEL_COMPARISON"] = original
