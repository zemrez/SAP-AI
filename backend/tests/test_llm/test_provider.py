"""Tests for the LLM provider and prompt templates."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Ensure backend root on path
BACKEND_ROOT = Path(__file__).resolve().parent.parent.parent
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from llm.prompts import (
    ANOMALY_BATCH_SUMMARY,
    ANOMALY_EXPLANATION_SYSTEM,
    ANOMALY_EXPLANATION_USER,
)
from llm.provider import LLMProvider, LLMProviderError


# ---------------------------------------------------------------------------
# Prompt template tests
# ---------------------------------------------------------------------------


class TestPromptTemplates:
    """Verify prompt templates render correctly with expected variables."""

    def test_anomaly_explanation_system_is_string(self) -> None:
        assert isinstance(ANOMALY_EXPLANATION_SYSTEM, str)
        assert "SAP financial auditor" in ANOMALY_EXPLANATION_SYSTEM

    def test_anomaly_explanation_user_format(self) -> None:
        rendered = ANOMALY_EXPLANATION_USER.format(
            anomaly_type="Statistical Outlier",
            detector_name="amount",
            risk_score=85.5,
            severity="CRITICAL",
            document_number="5000001234",
            amount="150000.00",
            currency="EUR",
            gl_account="400000",
            description="Amount is 5.2 standard deviations above mean",
            detector_details="Statistical Outlier (confidence: 92%)",
        )
        assert "Statistical Outlier" in rendered
        assert "5000001234" in rendered
        assert "150000.00" in rendered
        assert "root_cause_analysis" in rendered

    def test_anomaly_explanation_user_has_all_placeholders(self) -> None:
        """Ensure the template has all expected placeholders."""
        expected = [
            "anomaly_type", "detector_name", "risk_score", "severity",
            "document_number", "amount", "currency", "gl_account",
            "description", "detector_details",
        ]
        for placeholder in expected:
            assert f"{{{placeholder}}}" in ANOMALY_EXPLANATION_USER, (
                f"Missing placeholder: {placeholder}"
            )

    def test_batch_summary_format(self) -> None:
        rendered = ANOMALY_BATCH_SUMMARY.format(
            company_code="1000",
            date_from="2025-01-01",
            date_to="2025-12-31",
            total_documents=5000,
            anomalies_found=42,
            critical=3,
            high=12,
            medium=20,
            low=7,
            anomaly_list="- Doc 5000001234: Outlier amount (Score: 85.5, Severity: CRITICAL)",
        )
        assert "1000" in rendered
        assert "5000" in rendered
        assert "42" in rendered
        assert "executive_summary" in rendered

    def test_batch_summary_has_all_placeholders(self) -> None:
        expected = [
            "company_code", "date_from", "date_to", "total_documents",
            "anomalies_found", "critical", "high", "medium", "low",
            "anomaly_list",
        ]
        for placeholder in expected:
            assert f"{{{placeholder}}}" in ANOMALY_BATCH_SUMMARY, (
                f"Missing placeholder: {placeholder}"
            )


# ---------------------------------------------------------------------------
# LLM Provider tests (mocked)
# ---------------------------------------------------------------------------


def _mock_completion_response(content: str) -> MagicMock:
    """Create a mock litellm completion response."""
    choice = MagicMock()
    choice.message.content = content
    response = MagicMock()
    response.choices = [choice]
    return response


class TestLLMProvider:
    """Test the LLMProvider with mocked litellm calls."""

    @pytest.mark.asyncio
    @patch("llm.provider.litellm.acompletion", new_callable=AsyncMock)
    async def test_generate_text(self, mock_completion: AsyncMock) -> None:
        mock_completion.return_value = _mock_completion_response("This is a test response.")
        provider = LLMProvider(provider="gemini")

        result = await provider.generate("What is 2+2?")

        assert result == "This is a test response."
        mock_completion.assert_called_once()
        call_kwargs = mock_completion.call_args
        assert call_kwargs.kwargs["model"] == "gemini/gemini-2.0-flash"
        assert call_kwargs.kwargs["temperature"] == 0.3

    @pytest.mark.asyncio
    @patch("llm.provider.litellm.acompletion", new_callable=AsyncMock)
    async def test_generate_with_system_prompt(self, mock_completion: AsyncMock) -> None:
        mock_completion.return_value = _mock_completion_response("Response")
        provider = LLMProvider(provider="openai")

        await provider.generate("Hello", system_prompt="You are helpful.")

        messages = mock_completion.call_args.kwargs["messages"]
        assert len(messages) == 2
        assert messages[0]["role"] == "system"
        assert messages[0]["content"] == "You are helpful."
        assert messages[1]["role"] == "user"

    @pytest.mark.asyncio
    @patch("llm.provider.litellm.acompletion", new_callable=AsyncMock)
    async def test_generate_json_valid(self, mock_completion: AsyncMock) -> None:
        json_response = json.dumps({
            "root_cause_analysis": "Test analysis",
            "risk_assessment": "Medium risk",
        })
        mock_completion.return_value = _mock_completion_response(json_response)
        provider = LLMProvider(provider="gemini")

        result = await provider.generate_json("Analyze this")

        assert result["root_cause_analysis"] == "Test analysis"
        assert result["risk_assessment"] == "Medium risk"

    @pytest.mark.asyncio
    @patch("llm.provider.litellm.acompletion", new_callable=AsyncMock)
    async def test_generate_json_strips_markdown_fences(self, mock_completion: AsyncMock) -> None:
        json_body = json.dumps({"key": "value"})
        fenced = f"```json\n{json_body}\n```"
        mock_completion.return_value = _mock_completion_response(fenced)
        provider = LLMProvider(provider="gemini")

        result = await provider.generate_json("Return JSON")

        assert result == {"key": "value"}

    @pytest.mark.asyncio
    @patch("llm.provider.litellm.acompletion", new_callable=AsyncMock)
    async def test_generate_json_invalid_raises(self, mock_completion: AsyncMock) -> None:
        mock_completion.return_value = _mock_completion_response("This is not JSON")
        provider = LLMProvider(provider="gemini")

        with pytest.raises(LLMProviderError, match="Invalid JSON"):
            await provider.generate_json("Return JSON")

    @pytest.mark.asyncio
    @patch("llm.provider.litellm.acompletion", new_callable=AsyncMock)
    async def test_generate_llm_error_raises(self, mock_completion: AsyncMock) -> None:
        mock_completion.side_effect = Exception("API rate limit exceeded")
        provider = LLMProvider(provider="gemini")

        with pytest.raises(LLMProviderError, match="LLM call failed"):
            await provider.generate("Hello")

    def test_provider_model_mapping_gemini(self) -> None:
        provider = LLMProvider(provider="gemini")
        assert provider.model == "gemini/gemini-2.0-flash"

    def test_provider_model_mapping_openai(self) -> None:
        provider = LLMProvider(provider="openai")
        assert provider.model == "gpt-4o"

    def test_provider_custom_model(self) -> None:
        provider = LLMProvider(provider="openai", model="gpt-4-turbo")
        assert provider.model == "gpt-4-turbo"

    @pytest.mark.asyncio
    @patch("llm.provider.litellm.acompletion", new_callable=AsyncMock)
    async def test_generate_custom_temperature(self, mock_completion: AsyncMock) -> None:
        mock_completion.return_value = _mock_completion_response("Response")
        provider = LLMProvider(provider="gemini")

        await provider.generate("Hello", temperature=0.8)

        assert mock_completion.call_args.kwargs["temperature"] == 0.8
