"""Tests for all anomaly detectors."""

import pytest

from modules.anomaly_detective.detectors.amount_detector import AmountDetector
from modules.anomaly_detective.detectors.combination_detector import CombinationDetector
from modules.anomaly_detective.detectors.duplicate_detector import DuplicateDetector
from modules.anomaly_detective.detectors.ml_detector import MLDetector
from modules.anomaly_detective.detectors.round_number_detector import RoundNumberDetector
from modules.anomaly_detective.detectors.timing_detector import TimingDetector


# ============================================================
# AmountDetector
# ============================================================


class TestAmountDetector:
    @pytest.mark.asyncio
    async def test_statistical_outlier_detected(self, normal_entries, make_entry):
        """An amount far from the mean should be flagged."""
        entries = normal_entries + [
            make_entry(doc="9999999999", amount=99999.0, gl_account="400000")
        ]
        detector = AmountDetector()
        results = await detector.detect(entries)
        outlier_results = [r for r in results if r.anomaly_type == "Statistical Outlier"]
        assert len(outlier_results) >= 1
        assert any(r.document_number == "9999999999" for r in outlier_results)

    @pytest.mark.asyncio
    async def test_normal_entries_not_flagged(self, normal_entries):
        """Normal entries within expected range should not be flagged as outliers."""
        detector = AmountDetector()
        results = await detector.detect(normal_entries)
        outlier_results = [r for r in results if r.anomaly_type == "Statistical Outlier"]
        assert len(outlier_results) == 0

    @pytest.mark.asyncio
    async def test_negative_on_positive_account(self, normal_entries, make_entry):
        """Negative amount on a normally-positive account should be flagged."""
        entries = normal_entries + [
            make_entry(doc="8888888888", amount=-500.0, gl_account="400000")
        ]
        detector = AmountDetector()
        results = await detector.detect(entries)
        neg_results = [r for r in results if r.anomaly_type == "Negative on Positive Account"]
        assert len(neg_results) >= 1

    @pytest.mark.asyncio
    async def test_too_few_entries_skipped(self, make_entry):
        """Fewer than min_entries_for_stats should be skipped."""
        entries = [make_entry(doc=f"A{i}", amount=100.0 * i) for i in range(1, 5)]
        detector = AmountDetector({"min_entries_for_stats": 10})
        results = await detector.detect(entries)
        assert len(results) == 0

    @pytest.mark.asyncio
    async def test_empty_entries(self):
        detector = AmountDetector()
        assert await detector.detect([]) == []


# ============================================================
# DuplicateDetector
# ============================================================


class TestDuplicateDetector:
    @pytest.mark.asyncio
    async def test_exact_duplicate_detected(self, make_entry):
        """Two entries with same amount, reference, and date should be flagged."""
        e1 = make_entry(doc="1111111111", amount=5000.0, reference="INV-X", posting_date="2025-03-01")
        e2 = make_entry(doc="2222222222", amount=5000.0, reference="INV-X", posting_date="2025-03-01")
        detector = DuplicateDetector()
        results = await detector.detect([e1, e2])
        exact = [r for r in results if r.anomaly_type == "Exact Duplicate"]
        assert len(exact) >= 1

    @pytest.mark.asyncio
    async def test_near_duplicate_same_gl_within_window(self, make_entry):
        """Same amount + GL within time window should be flagged."""
        e1 = make_entry(doc="3333333333", amount=7500.0, gl_account="500000", posting_date="2025-03-01")
        e2 = make_entry(doc="4444444444", amount=7500.0, gl_account="500000", posting_date="2025-03-01")
        detector = DuplicateDetector()
        results = await detector.detect([e1, e2])
        assert len(results) >= 1

    @pytest.mark.asyncio
    async def test_different_amounts_not_flagged(self, make_entry):
        """Different amounts should not be flagged as duplicates."""
        e1 = make_entry(doc="5555555555", amount=1000.0)
        e2 = make_entry(doc="6666666666", amount=2000.0)
        detector = DuplicateDetector()
        results = await detector.detect([e1, e2])
        exact = [r for r in results if r.anomaly_type == "Exact Duplicate"]
        assert len(exact) == 0

    @pytest.mark.asyncio
    async def test_empty_entries(self):
        detector = DuplicateDetector()
        assert await detector.detect([]) == []


# ============================================================
# TimingDetector
# ============================================================


class TestTimingDetector:
    @pytest.mark.asyncio
    async def test_weekend_posting_flagged(self, make_entry):
        """A Saturday posting should be flagged."""
        # 2025-06-14 is a Saturday
        entry = make_entry(posting_date="2025-06-14")
        detector = TimingDetector()
        results = await detector.detect([entry])
        weekend = [r for r in results if r.anomaly_type == "Weekend Posting"]
        assert len(weekend) == 1
        assert weekend[0].details["day_name"] == "Saturday"

    @pytest.mark.asyncio
    async def test_weekday_not_flagged(self, make_entry):
        """A normal weekday posting should not be flagged for weekends."""
        # 2025-06-16 is a Monday
        entry = make_entry(posting_date="2025-06-16")
        detector = TimingDetector()
        results = await detector.detect([entry])
        weekend = [r for r in results if r.anomaly_type == "Weekend Posting"]
        assert len(weekend) == 0

    @pytest.mark.asyncio
    async def test_holiday_posting_flagged(self, make_entry):
        """Posting on a configured holiday should be flagged."""
        entry = make_entry(posting_date="2025-12-25")
        detector = TimingDetector({"holidays": ["2025-12-25"]})
        results = await detector.detect([entry])
        holidays = [r for r in results if r.anomaly_type == "Holiday Posting"]
        assert len(holidays) == 1

    @pytest.mark.asyncio
    async def test_off_hours_flagged(self, make_entry):
        """Posting at 23:00 should be flagged as off-hours."""
        entry = make_entry(posting_date="2025-06-16T23:30:00")
        detector = TimingDetector()
        results = await detector.detect([entry])
        off_hours = [r for r in results if r.anomaly_type == "Off-Hours Posting"]
        assert len(off_hours) == 1


# ============================================================
# CombinationDetector
# ============================================================


class TestCombinationDetector:
    @pytest.mark.asyncio
    async def test_rare_pair_flagged(self, document_pair_entries):
        """A rare debit/credit account pair should be flagged."""
        detector = CombinationDetector({"frequency_threshold": 0.05})
        results = await detector.detect(document_pair_entries)
        rare = [r for r in results if r.anomaly_type == "Rare Account Combination"]
        assert len(rare) >= 1
        # The rare pair involves GL 999999
        assert any("999999" in r.details.get("credit_account", "") for r in rare)

    @pytest.mark.asyncio
    async def test_common_pair_not_flagged(self, document_pair_entries):
        """The common pair should NOT be flagged."""
        detector = CombinationDetector({"frequency_threshold": 0.01})
        results = await detector.detect(document_pair_entries)
        flagged_pairs = {r.details.get("credit_account") for r in results}
        # 200000 is the common credit account
        assert "200000" not in flagged_pairs

    @pytest.mark.asyncio
    async def test_empty_entries(self):
        detector = CombinationDetector()
        assert await detector.detect([]) == []


# ============================================================
# RoundNumberDetector
# ============================================================


class TestRoundNumberDetector:
    @pytest.mark.asyncio
    async def test_round_amount_flagged(self, make_entry):
        """A round amount above min_amount should be flagged."""
        entry = make_entry(amount=50000.0)
        detector = RoundNumberDetector({"min_amount": 10000, "round_unit": 1000})
        results = await detector.detect([entry])
        rounds = [r for r in results if r.anomaly_type == "Round Number Amount"]
        assert len(rounds) == 1

    @pytest.mark.asyncio
    async def test_non_round_not_flagged(self, make_entry):
        """A non-round amount should not be flagged."""
        entry = make_entry(amount=50123.45)
        detector = RoundNumberDetector()
        results = await detector.detect([entry])
        rounds = [r for r in results if r.anomaly_type == "Round Number Amount"]
        assert len(rounds) == 0

    @pytest.mark.asyncio
    async def test_below_min_not_flagged(self, make_entry):
        """Round amount below min_amount should not be flagged."""
        entry = make_entry(amount=5000.0)
        detector = RoundNumberDetector({"min_amount": 10000})
        results = await detector.detect([entry])
        rounds = [r for r in results if r.anomaly_type == "Round Number Amount"]
        assert len(rounds) == 0

    @pytest.mark.asyncio
    async def test_default_config(self):
        detector = RoundNumberDetector()
        cfg = detector.get_default_config()
        assert cfg["round_unit"] == 1000
        assert cfg["min_amount"] == 10000
        assert cfg["benford_chi_sq_threshold"] == 15.507


# ============================================================
# MLDetector
# ============================================================


class TestMLDetector:
    @pytest.mark.asyncio
    async def test_detects_anomalies_in_mixed_data(self, normal_entries, make_entry):
        """ML detector should flag obvious outliers."""
        # Add a very unusual entry
        outlier = make_entry(
            doc="ML_OUTLIER_1",
            amount=999999.0,
            posting_date="2025-06-14T23:59:00",  # Saturday, late night
            gl_account="999888",
            reference="RARE_VENDOR",
        )
        entries = normal_entries + [outlier]
        detector = MLDetector({"contamination": 0.05})
        results = await detector.detect(entries)
        # At least one anomaly should be detected
        assert len(results) >= 1

    @pytest.mark.asyncio
    async def test_fit_model_stores_model(self, normal_entries):
        """fit_model should create a trained model."""
        detector = MLDetector()
        detector.fit_model(normal_entries)
        assert detector._model is not None

    @pytest.mark.asyncio
    async def test_empty_entries(self):
        detector = MLDetector()
        assert await detector.detect([]) == []

    @pytest.mark.asyncio
    async def test_too_few_entries_no_model(self, make_entry):
        """With very few entries, model should not be fitted."""
        entries = [make_entry(doc=f"FEW{i}") for i in range(3)]
        detector = MLDetector()
        detector.fit_model(entries)
        assert detector._model is None
