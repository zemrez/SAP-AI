"""ML-based anomaly detector using Isolation Forest."""

from __future__ import annotations

import logging
import math
from collections import Counter
from decimal import Decimal

import numpy as np
from sklearn.ensemble import IsolationForest

from .base import BaseDetector, DetectionResult

logger = logging.getLogger(__name__)


def _parse_hour(d: str) -> int:
    """Extract hour from a date/datetime string. Returns 0 if no time info."""
    if not d or len(d) < 13:
        return 0
    try:
        return int(d[11:13])
    except (ValueError, IndexError):
        return 0


def _day_of_week(d: str) -> int:
    """Return day of week (0=Mon, 6=Sun) from date string."""
    from datetime import datetime

    if not d:
        return 0
    for fmt in ("%Y-%m-%d", "%Y-%m-%dT%H:%M:%S", "%Y%m%d"):
        try:
            return datetime.strptime(d[:19], fmt).weekday()
        except ValueError:
            continue
    return 0


class MLDetector(BaseDetector):
    """Isolation Forest anomaly detector.

    Features extracted from each journal entry:
    - amount (log-transformed)
    - hour_of_day
    - day_of_week (0-6)
    - is_weekend (0/1)
    - account_frequency (how common this GL account is)
    - vendor_frequency (how common this vendor/reference is)
    - is_round_number (0/1)
    """

    name = "ml"
    description = "Machine learning anomaly detection using Isolation Forest"

    def __init__(self, config: dict | None = None) -> None:
        cfg = {**self.get_default_config(), **(config or {})}
        self.contamination: float = cfg["contamination"]
        self.n_estimators: int = cfg["n_estimators"]
        self.random_state: int = cfg["random_state"]
        self._model: IsolationForest | None = None

    def get_default_config(self) -> dict:
        return {
            "contamination": 0.01,
            "n_estimators": 100,
            "random_state": 42,
        }

    def _extract_features(self, entries: list[dict]) -> tuple[np.ndarray, dict[str, float], dict[str, float]]:
        """Build feature matrix from journal entries."""
        n = len(entries)
        if n == 0:
            return np.empty((0, 7)), {}, {}

        # Pre-compute frequency tables
        gl_counter: Counter[str] = Counter()
        vendor_counter: Counter[str] = Counter()
        for e in entries:
            gl = e.get("gl_account") or e.get("GLAccount", "")
            vendor = e.get("reference_document") or e.get("ReferenceDocument", "")
            gl_counter[gl] += 1
            vendor_counter[vendor] += 1

        gl_freq = {k: v / n for k, v in gl_counter.items()}
        vendor_freq = {k: v / n for k, v in vendor_counter.items()}

        features = np.zeros((n, 7))
        for i, e in enumerate(entries):
            raw_amt = float(
                e.get("amount_in_company_code_currency")
                or e.get("AmountInCompanyCodeCurrency", 0)
            )
            pdate = e.get("posting_date") or e.get("PostingDate", "")
            gl = e.get("gl_account") or e.get("GLAccount", "")
            vendor = e.get("reference_document") or e.get("ReferenceDocument", "")
            abs_amt = abs(raw_amt)

            features[i, 0] = math.log1p(abs_amt)  # log-transformed amount
            features[i, 1] = _parse_hour(pdate)  # hour_of_day
            features[i, 2] = _day_of_week(pdate)  # day_of_week
            features[i, 3] = 1.0 if _day_of_week(pdate) >= 5 else 0.0  # is_weekend
            features[i, 4] = gl_freq.get(gl, 0.0)  # account_frequency
            features[i, 5] = vendor_freq.get(vendor, 0.0)  # vendor_frequency
            features[i, 6] = 1.0 if (abs_amt >= 1000 and abs_amt % 1000 == 0) else 0.0  # is_round

        return features, gl_freq, vendor_freq

    def fit_model(self, entries: list[dict]) -> None:
        """Train the Isolation Forest on historical entries."""
        features, _, _ = self._extract_features(entries)
        if features.shape[0] < 10:
            logger.warning("Too few entries (%d) to train ML model.", features.shape[0])
            return

        self._model = IsolationForest(
            contamination=self.contamination,
            n_estimators=self.n_estimators,
            random_state=self.random_state,
        )
        self._model.fit(features)
        logger.info("ML model trained on %d entries.", features.shape[0])

    async def detect(self, entries: list[dict]) -> list[DetectionResult]:
        results: list[DetectionResult] = []
        if not entries:
            return results

        features, _, _ = self._extract_features(entries)

        # If no pre-trained model, fit on the provided entries
        if self._model is None:
            self.fit_model(entries)

        if self._model is None:
            logger.warning("ML model could not be fitted. Skipping ML detection.")
            return results

        predictions = self._model.predict(features)
        scores = self._model.decision_function(features)

        for i, entry in enumerate(entries):
            if predictions[i] == -1:
                # Anomaly detected
                anomaly_score = float(-scores[i])  # Higher = more anomalous
                confidence = min(1.0, max(0.1, anomaly_score))
                raw_amt = entry.get("amount_in_company_code_currency") or entry.get(
                    "AmountInCompanyCodeCurrency", 0
                )
                fy_raw = entry.get("fiscal_year") or entry.get("FiscalYear", "")

                results.append(
                    DetectionResult(
                        detector_name=self.name,
                        anomaly_type="ML Anomaly (Isolation Forest)",
                        confidence=confidence,
                        document_number=entry.get("accounting_document") or entry.get("AccountingDocument"),
                        company_code=entry.get("company_code") or entry.get("CompanyCode"),
                        fiscal_year=int(fy_raw) if fy_raw else None,
                        posting_date=entry.get("posting_date") or entry.get("PostingDate"),
                        amount=Decimal(str(raw_amt)),
                        currency=entry.get("company_code_currency") or entry.get("CompanyCodeCurrency", ""),
                        details={
                            "anomaly_score": round(anomaly_score, 4),
                            "features": {
                                "log_amount": round(float(features[i, 0]), 4),
                                "hour_of_day": int(features[i, 1]),
                                "day_of_week": int(features[i, 2]),
                                "is_weekend": bool(features[i, 3]),
                                "account_frequency": round(float(features[i, 4]), 4),
                                "vendor_frequency": round(float(features[i, 5]), 4),
                                "is_round_number": bool(features[i, 6]),
                            },
                        },
                        description=(
                            f"ML model flagged this entry with anomaly score "
                            f"{anomaly_score:.3f}"
                        ),
                    )
                )

        return results
