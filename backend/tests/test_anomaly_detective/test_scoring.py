"""Tests for the scoring engine."""

from decimal import Decimal

import pytest

import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parent.parent.parent
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from modules.anomaly_detective.detectors.base import DetectionResult
from modules.anomaly_detective.scoring import ScoredAnomaly, ScoringEngine


def _result(
    *,
    detector: str = "amount",
    doc: str = "5000000001",
    bukrs: str = "1000",
    gjahr: int = 2025,
    confidence: float = 0.8,
    anomaly_type: str = "Test Anomaly",
) -> DetectionResult:
    return DetectionResult(
        detector_name=detector,
        anomaly_type=anomaly_type,
        confidence=confidence,
        document_number=doc,
        company_code=bukrs,
        fiscal_year=gjahr,
        posting_date="2025-06-15",
        amount=Decimal("1500.00"),
        currency="EUR",
        details={},
        description=f"Test finding from {detector}",
    )


class TestScoringEngine:
    def test_single_detector_single_doc(self):
        """One finding from one detector should produce a scored anomaly."""
        engine = ScoringEngine()
        results = [_result(confidence=0.9)]
        scored = engine.aggregate_scores(results)
        assert len(scored) == 1
        assert scored[0].risk_score == 90.0
        assert scored[0].severity.value == "CRITICAL"
        assert scored[0].detectors_triggered == ["amount"]

    def test_multiple_detectors_same_doc(self):
        """Multiple detectors flagging the same document should combine scores."""
        engine = ScoringEngine()
        results = [
            _result(detector="amount", confidence=0.8),
            _result(detector="duplicate", confidence=0.6),
            _result(detector="timing", confidence=0.4),
        ]
        scored = engine.aggregate_scores(results)
        assert len(scored) == 1
        assert len(scored[0].detectors_triggered) == 3
        assert scored[0].total_findings == 3
        # Weighted average should be between min and max confidence * 100
        assert 40 <= scored[0].risk_score <= 100

    def test_multiple_documents(self):
        """Findings for different documents should produce separate scored anomalies."""
        engine = ScoringEngine()
        results = [
            _result(doc="DOC_A", confidence=0.9),
            _result(doc="DOC_B", confidence=0.3),
        ]
        scored = engine.aggregate_scores(results)
        assert len(scored) == 2
        # Should be sorted by risk_score descending
        assert scored[0].risk_score >= scored[1].risk_score

    def test_severity_low(self):
        """Score 0-25 should be LOW."""
        engine = ScoringEngine()
        results = [_result(confidence=0.15)]
        scored = engine.aggregate_scores(results)
        assert scored[0].severity.value == "LOW"

    def test_severity_medium(self):
        """Score 26-50 should be MEDIUM."""
        engine = ScoringEngine()
        results = [_result(confidence=0.35)]
        scored = engine.aggregate_scores(results)
        assert scored[0].severity.value == "MEDIUM"

    def test_severity_high(self):
        """Score 51-75 should be HIGH."""
        engine = ScoringEngine()
        results = [_result(confidence=0.65)]
        scored = engine.aggregate_scores(results)
        assert scored[0].severity.value == "HIGH"

    def test_severity_critical(self):
        """Score 76-100 should be CRITICAL."""
        engine = ScoringEngine()
        results = [_result(confidence=0.95)]
        scored = engine.aggregate_scores(results)
        assert scored[0].severity.value == "CRITICAL"

    def test_empty_results(self):
        """No findings should produce no scored anomalies."""
        engine = ScoringEngine()
        assert engine.aggregate_scores([]) == []

    def test_custom_weights(self):
        """Custom weights should override defaults."""
        engine = ScoringEngine(weights={"amount": 1.0, "duplicate": 0.0})
        results = [
            _result(detector="amount", confidence=0.8),
            _result(detector="duplicate", confidence=0.2),
        ]
        scored = engine.aggregate_scores(results)
        assert len(scored) == 1
        # amount weight=1.0, duplicate weight=0.0
        # So score should be dominated by amount confidence
        # weighted_sum = 0.8*1.0 + 0.2*0.0 = 0.8, total_weight = 1.0
        # raw_score = (0.8/1.0)*100 = 80
        assert scored[0].risk_score == 80.0

    def test_max_confidence_tracked(self):
        """max_confidence should reflect the highest individual confidence."""
        engine = ScoringEngine()
        results = [
            _result(detector="amount", confidence=0.3),
            _result(detector="duplicate", confidence=0.9),
        ]
        scored = engine.aggregate_scores(results)
        assert scored[0].max_confidence == 0.9

    def test_description_includes_detector_types(self):
        """Description should mention the anomaly types found."""
        engine = ScoringEngine()
        results = [
            _result(detector="amount", anomaly_type="Statistical Outlier"),
            _result(detector="timing", anomaly_type="Weekend Posting"),
        ]
        scored = engine.aggregate_scores(results)
        assert "2 detector(s)" in scored[0].description
