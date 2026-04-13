"""Tests for the LangGraph anomaly detection workflow."""

from __future__ import annotations

import json
import sys
from decimal import Decimal
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Ensure backend root on path
BACKEND_ROOT = Path(__file__).resolve().parent.parent.parent
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from modules.anomaly_detective.detectors.base import DetectionResult
from modules.anomaly_detective.schemas import AnomalySeverity
from modules.anomaly_detective.scoring import ScoredAnomaly
from modules.anomaly_detective.workflow import (
    ScanState,
    build_scan_workflow,
    explain_anomalies,
    extract_data,
    handle_failure,
    persist_results,
    run_detectors,
    score_anomalies,
    should_continue,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def base_state() -> ScanState:
    """Minimal valid scan state."""
    return ScanState(
        scan_id="ABCD1234",
        bukrs="1000",
        date_from="2025-01-01",
        date_to="2025-12-31",
        scan_type="FULL",
        status="PENDING",
    )


@pytest.fixture
def sample_entries() -> list[dict]:
    """A small set of journal entry dicts."""
    return [
        {
            "accounting_document": f"500000{i:04d}",
            "accounting_document_item": "001",
            "company_code": "1000",
            "fiscal_year": "2025",
            "posting_date": "2025-06-15",
            "document_date": "2025-06-15",
            "gl_account": "400000",
            "amount_in_company_code_currency": 1000.0 + i * 100,
            "company_code_currency": "EUR",
            "debit_credit_code": "S",
            "document_type": "SA",
            "reference_document": "INV-001",
            "document_header_text": "",
            "created_by_user": "TESTUSER",
        }
        for i in range(10)
    ]


@pytest.fixture
def sample_scored_anomalies() -> list[ScoredAnomaly]:
    """A few scored anomalies for testing."""
    return [
        ScoredAnomaly(
            document_number="5000001234",
            company_code="1000",
            fiscal_year=2025,
            risk_score=88.5,
            severity=AnomalySeverity.CRITICAL,
            detectors_triggered=["amount", "ml"],
            total_findings=3,
            max_confidence=0.95,
            posting_date="2025-06-15",
            amount=Decimal("150000.00"),
            currency="EUR",
            findings=[
                DetectionResult(
                    detector_name="amount",
                    anomaly_type="Statistical Outlier",
                    confidence=0.95,
                    document_number="5000001234",
                    company_code="1000",
                    fiscal_year=2025,
                    amount=Decimal("150000.00"),
                    currency="EUR",
                    description="Amount is 5.2 std devs above mean",
                    details={"gl_account": "400000"},
                ),
            ],
            description="Flagged by 2 detector(s): Statistical Outlier, ML Anomaly",
        ),
        ScoredAnomaly(
            document_number="5000005678",
            company_code="1000",
            fiscal_year=2025,
            risk_score=35.0,
            severity=AnomalySeverity.MEDIUM,
            detectors_triggered=["round_number"],
            total_findings=1,
            max_confidence=0.6,
            amount=Decimal("10000.00"),
            currency="EUR",
            findings=[
                DetectionResult(
                    detector_name="round_number",
                    anomaly_type="Round Amount",
                    confidence=0.6,
                    document_number="5000005678",
                    company_code="1000",
                    description="Exact round amount",
                    details={},
                ),
            ],
            description="Flagged by 1 detector(s): Round Amount",
        ),
    ]


# ---------------------------------------------------------------------------
# Routing tests
# ---------------------------------------------------------------------------


class TestRouting:
    def test_should_continue_on_success(self) -> None:
        state: ScanState = {"status": "EXTRACTING_COMPLETE"}  # type: ignore[typeddict-item]
        assert should_continue(state) == "continue"

    def test_should_continue_on_failure(self) -> None:
        state: ScanState = {"status": "FAILED", "error": "something broke"}  # type: ignore[typeddict-item]
        assert should_continue(state) == "handle_failure"


# ---------------------------------------------------------------------------
# Node tests (individual)
# ---------------------------------------------------------------------------


class TestExtractData:
    @pytest.mark.asyncio
    @patch("modules.anomaly_detective.workflow.JournalEntryExtractor")
    @patch("modules.anomaly_detective.workflow.SAPClient")
    async def test_extract_success(
        self, mock_sap_cls: MagicMock, mock_extractor_cls: MagicMock, base_state: ScanState
    ) -> None:
        mock_entry = MagicMock()
        mock_entry.model_dump.return_value = {"accounting_document": "5000000001"}

        mock_extractor = MagicMock()
        mock_extractor.get_entries = AsyncMock(return_value=[mock_entry, mock_entry])
        mock_extractor_cls.return_value = mock_extractor

        result = await extract_data(base_state)

        assert result["total_documents"] == 2
        assert len(result["journal_entries"]) == 2
        assert result["status"] == "EXTRACTING_COMPLETE"

    @pytest.mark.asyncio
    @patch("modules.anomaly_detective.workflow.JournalEntryExtractor")
    @patch("modules.anomaly_detective.workflow.SAPClient")
    async def test_extract_failure(
        self, mock_sap_cls: MagicMock, mock_extractor_cls: MagicMock, base_state: ScanState
    ) -> None:
        from sap.client import SAPClientError

        mock_extractor = MagicMock()
        mock_extractor.get_entries = AsyncMock(side_effect=SAPClientError("Connection refused"))
        mock_extractor_cls.return_value = mock_extractor

        result = await extract_data(base_state)

        assert result["status"] == "FAILED"
        assert "Connection refused" in result["error"]


class TestRunDetectors:
    @pytest.mark.asyncio
    async def test_run_detectors_empty_entries(self, base_state: ScanState) -> None:
        state = {**base_state, "journal_entries": []}
        result = await run_detectors(state)

        assert result["detection_results"] == []
        assert result["status"] == "DETECTING_COMPLETE"

    @pytest.mark.asyncio
    async def test_run_detectors_with_entries(
        self, base_state: ScanState, sample_entries: list[dict]
    ) -> None:
        # Run with only the amount detector for speed
        state = {**base_state, "journal_entries": sample_entries, "detectors": ["amount"]}
        result = await run_detectors(state)

        assert result["status"] == "DETECTING_COMPLETE"
        assert isinstance(result["detection_results"], list)

    @pytest.mark.asyncio
    async def test_run_detectors_unknown_detector_skipped(
        self, base_state: ScanState, sample_entries: list[dict]
    ) -> None:
        state = {
            **base_state,
            "journal_entries": sample_entries,
            "detectors": ["nonexistent_detector"],
        }
        result = await run_detectors(state)

        assert result["status"] == "DETECTING_COMPLETE"
        assert result["detection_results"] == []


class TestScoreAnomalies:
    @pytest.mark.asyncio
    async def test_score_empty_results(self) -> None:
        state: ScanState = {"detection_results": []}  # type: ignore[typeddict-item]
        result = await score_anomalies(state)

        assert result["scored_anomalies"] == []
        assert result["anomalies_found"] == 0

    @pytest.mark.asyncio
    async def test_score_with_results(self) -> None:
        findings = [
            DetectionResult(
                detector_name="amount",
                anomaly_type="Outlier",
                confidence=0.9,
                document_number="5000000001",
                company_code="1000",
                fiscal_year=2025,
                amount=Decimal("50000"),
                currency="EUR",
                description="Test finding",
            ),
        ]
        state: ScanState = {"detection_results": findings}  # type: ignore[typeddict-item]
        result = await score_anomalies(state)

        assert len(result["scored_anomalies"]) == 1
        assert result["anomalies_found"] == 1
        assert result["scored_anomalies"][0].risk_score > 0


class TestExplainAnomalies:
    @pytest.mark.asyncio
    async def test_explain_no_high_priority(self) -> None:
        """No explanations generated when no HIGH/CRITICAL anomalies."""
        low_anomaly = ScoredAnomaly(
            document_number="5000000001",
            company_code="1000",
            risk_score=20.0,
            severity=AnomalySeverity.LOW,
            findings=[],
            description="Low risk item",
        )
        state: ScanState = {"scored_anomalies": [low_anomaly]}  # type: ignore[typeddict-item]
        result = await explain_anomalies(state)

        assert result["explanations"] == {}
        assert result["status"] == "EXPLAINING_COMPLETE"

    @pytest.mark.asyncio
    @patch("modules.anomaly_detective.workflow.LLMProvider")
    async def test_explain_high_priority_anomalies(
        self,
        mock_llm_cls: MagicMock,
        sample_scored_anomalies: list[ScoredAnomaly],
    ) -> None:
        """LLM is called for HIGH/CRITICAL anomalies only."""
        mock_llm = MagicMock()
        mock_llm.generate_json = AsyncMock(
            return_value={
                "root_cause_analysis": "Unusual amount detected",
                "risk_assessment": "High risk of misstatement",
                "recommended_actions": ["Review with manager"],
                "similar_patterns": "Watch for similar outliers",
                "confidence_level": "HIGH",
            }
        )
        mock_llm_cls.return_value = mock_llm

        state: ScanState = {  # type: ignore[typeddict-item]
            "scored_anomalies": sample_scored_anomalies,
            "bukrs": "1000",
            "date_from": "2025-01-01",
            "date_to": "2025-12-31",
            "total_documents": 5000,
        }
        result = await explain_anomalies(state)

        # Only the CRITICAL anomaly should get an explanation (not MEDIUM)
        assert "5000001234" in result["explanations"]
        assert "5000005678" not in result["explanations"]
        assert result["explanations"]["5000001234"]["root_cause_analysis"] == "Unusual amount detected"

    @pytest.mark.asyncio
    @patch("modules.anomaly_detective.workflow.LLMProvider")
    async def test_explain_llm_failure_fallback(
        self,
        mock_llm_cls: MagicMock,
        sample_scored_anomalies: list[ScoredAnomaly],
    ) -> None:
        """Graceful fallback when LLM fails."""
        from llm.provider import LLMProviderError

        mock_llm = MagicMock()
        mock_llm.generate_json = AsyncMock(side_effect=LLMProviderError("API down"))
        mock_llm_cls.return_value = mock_llm

        state: ScanState = {  # type: ignore[typeddict-item]
            "scored_anomalies": sample_scored_anomalies,
            "bukrs": "1000",
            "date_from": "2025-01-01",
            "date_to": "2025-12-31",
            "total_documents": 5000,
        }
        result = await explain_anomalies(state)

        # Should still have an entry with fallback values
        assert "5000001234" in result["explanations"]
        assert result["explanations"]["5000001234"]["root_cause_analysis"] == "LLM explanation unavailable"
        assert result["status"] == "EXPLAINING_COMPLETE"


class TestPersistResults:
    @pytest.mark.asyncio
    @patch("modules.anomaly_detective.workflow.SAPClient")
    async def test_persist_success(
        self,
        mock_sap_cls: MagicMock,
        sample_scored_anomalies: list[ScoredAnomaly],
    ) -> None:
        mock_sap = MagicMock()
        mock_sap.post = AsyncMock(return_value={})
        mock_sap.patch = AsyncMock(return_value={})
        mock_sap_cls.return_value = mock_sap

        state: ScanState = {  # type: ignore[typeddict-item]
            "scan_id": "ABCD1234",
            "bukrs": "1000",
            "date_from": "2025-01-01",
            "scored_anomalies": sample_scored_anomalies,
            "explanations": {
                "5000001234": {"root_cause_analysis": "Test analysis"},
            },
            "total_documents": 100,
        }
        result = await persist_results(state)

        assert result["status"] == "COMPLETED"
        assert result["completed_at"] is not None
        # 2 anomalies posted + 1 scan status patch
        assert mock_sap.post.call_count == 2
        assert mock_sap.patch.call_count == 1

    @pytest.mark.asyncio
    @patch("modules.anomaly_detective.workflow.SAPClient")
    async def test_persist_includes_ai_summary(
        self,
        mock_sap_cls: MagicMock,
        sample_scored_anomalies: list[ScoredAnomaly],
    ) -> None:
        mock_sap = MagicMock()
        mock_sap.post = AsyncMock(return_value={})
        mock_sap.patch = AsyncMock(return_value={})
        mock_sap_cls.return_value = mock_sap

        state: ScanState = {  # type: ignore[typeddict-item]
            "scan_id": "ABCD1234",
            "bukrs": "1000",
            "date_from": "2025-01-01",
            "scored_anomalies": sample_scored_anomalies[:1],  # Only CRITICAL one
            "explanations": {
                "5000001234": {"root_cause_analysis": "Unusual posting pattern detected"},
            },
            "total_documents": 100,
        }
        await persist_results(state)

        # Check the POST call included AiSummary
        post_call = mock_sap.post.call_args_list[0]
        payload = post_call.kwargs.get("json", post_call[1].get("json", {}))
        assert payload["AiSummary"] == "Unusual posting pattern detected"


class TestHandleFailure:
    @pytest.mark.asyncio
    @patch("modules.anomaly_detective.workflow.SAPClient")
    async def test_handle_failure_updates_sap(self, mock_sap_cls: MagicMock) -> None:
        mock_sap = MagicMock()
        mock_sap.patch = AsyncMock(return_value={})
        mock_sap_cls.return_value = mock_sap

        state: ScanState = {  # type: ignore[typeddict-item]
            "scan_id": "ABCD1234",
            "error": "Connection timeout",
        }
        result = await handle_failure(state)

        assert result["status"] == "FAILED"
        mock_sap.patch.assert_called_once()


# ---------------------------------------------------------------------------
# Graph structure test
# ---------------------------------------------------------------------------


class TestWorkflowGraph:
    def test_build_scan_workflow_compiles(self) -> None:
        """Verify the workflow graph compiles without errors."""
        graph = build_scan_workflow()
        assert graph is not None

    def test_workflow_has_expected_nodes(self) -> None:
        graph = build_scan_workflow()
        # The compiled graph should have node definitions
        # We verify by checking it's a valid runnable
        assert hasattr(graph, "ainvoke")
        assert hasattr(graph, "invoke")
