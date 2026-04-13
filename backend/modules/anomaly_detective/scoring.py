"""Scoring engine -- aggregates detector results into risk-scored anomalies."""

from __future__ import annotations

from decimal import Decimal

from pydantic import BaseModel, Field

from .detectors.base import DetectionResult
from .schemas import AnomalySeverity


class ScoredAnomaly(BaseModel):
    """A document-level anomaly with an aggregated risk score."""

    document_number: str
    company_code: str
    fiscal_year: int | None = None
    risk_score: float = Field(..., ge=0.0, le=100.0)
    severity: AnomalySeverity
    detectors_triggered: list[str] = Field(default_factory=list)
    total_findings: int = 0
    max_confidence: float = 0.0
    posting_date: str | None = None
    amount: Decimal | None = None
    currency: str | None = None
    findings: list[DetectionResult] = Field(default_factory=list)
    description: str = ""


class ScoringEngine:
    """Combine results from multiple detectors into risk-scored anomalies.

    Groups DetectionResults by document (belnr + bukrs + gjahr), then
    computes a weighted composite score.
    """

    WEIGHTS: dict[str, float] = {
        "amount": 0.20,
        "duplicate": 0.25,
        "timing": 0.10,
        "combination": 0.15,
        "round_number": 0.10,
        "ml": 0.20,
    }

    def __init__(self, weights: dict[str, float] | None = None) -> None:
        if weights:
            self.WEIGHTS = {**self.WEIGHTS, **weights}

    @staticmethod
    def _doc_key(r: DetectionResult) -> str:
        """Composite key for grouping: belnr_bukrs_gjahr."""
        return f"{r.document_number or ''}_{r.company_code or ''}_{r.fiscal_year or ''}"

    @staticmethod
    def _severity_from_score(score: float) -> AnomalySeverity:
        if score >= 76:
            return AnomalySeverity.CRITICAL
        if score >= 51:
            return AnomalySeverity.HIGH
        if score >= 26:
            return AnomalySeverity.MEDIUM
        return AnomalySeverity.LOW

    def aggregate_scores(self, results: list[DetectionResult]) -> list[ScoredAnomaly]:
        """Group results by document and compute weighted risk scores."""
        if not results:
            return []

        # Group by document
        groups: dict[str, list[DetectionResult]] = {}
        for r in results:
            key = self._doc_key(r)
            groups.setdefault(key, []).append(r)

        scored: list[ScoredAnomaly] = []
        for _key, findings in groups.items():
            # Collect per-detector max confidence
            detector_max_conf: dict[str, float] = {}
            for f in findings:
                name = f.detector_name
                if name not in detector_max_conf or f.confidence > detector_max_conf[name]:
                    detector_max_conf[name] = f.confidence

            # Weighted sum
            weighted_sum = 0.0
            total_weight = 0.0
            for det_name, conf in detector_max_conf.items():
                w = self.WEIGHTS.get(det_name, 0.10)
                weighted_sum += conf * w
                total_weight += w

            # Normalize and scale to 0-100
            if total_weight > 0:
                raw_score = (weighted_sum / total_weight) * 100
            else:
                raw_score = 0.0
            risk_score = min(100.0, raw_score)

            # Use first finding for document-level fields
            first = findings[0]
            max_confidence = max(f.confidence for f in findings)

            # Build description from top findings
            top_types = list({f.anomaly_type for f in findings})
            desc = f"Flagged by {len(detector_max_conf)} detector(s): {', '.join(top_types)}"

            scored.append(
                ScoredAnomaly(
                    document_number=first.document_number or "",
                    company_code=first.company_code or "",
                    fiscal_year=first.fiscal_year,
                    risk_score=round(risk_score, 1),
                    severity=self._severity_from_score(risk_score),
                    detectors_triggered=list(detector_max_conf.keys()),
                    total_findings=len(findings),
                    max_confidence=round(max_confidence, 3),
                    posting_date=first.posting_date,
                    amount=first.amount,
                    currency=first.currency,
                    findings=findings,
                    description=desc,
                )
            )

        # Sort by risk score descending
        scored.sort(key=lambda s: s.risk_score, reverse=True)
        return scored
