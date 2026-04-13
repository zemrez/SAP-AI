"""Round number detector -- flags suspiciously round amounts and Benford's law deviations."""

from __future__ import annotations

import logging
import math
from collections import Counter
from decimal import Decimal

from .base import BaseDetector, DetectionResult

logger = logging.getLogger(__name__)

# Expected first-digit distribution per Benford's law
BENFORD_EXPECTED = {
    1: 0.301,
    2: 0.176,
    3: 0.125,
    4: 0.097,
    5: 0.079,
    6: 0.067,
    7: 0.058,
    8: 0.051,
    9: 0.046,
}


class RoundNumberDetector(BaseDetector):
    """Flag round-number amounts and Benford's law violations.

    - Round amounts: divisible by round_unit and above min_amount
    - Benford check: chi-squared test on first-digit distribution
    """

    name = "round_number"
    description = "Detects suspiciously round amounts and Benford's law deviations"

    def __init__(self, config: dict | None = None) -> None:
        cfg = {**self.get_default_config(), **(config or {})}
        self.round_unit: int = cfg["round_unit"]
        self.min_amount: float = cfg["min_amount"]
        self.benford_chi_sq_threshold: float = cfg["benford_chi_sq_threshold"]

    def get_default_config(self) -> dict:
        return {
            "round_unit": 1000,
            "min_amount": 10000,
            "benford_chi_sq_threshold": 15.507,  # chi-sq critical value, df=8, p=0.05
        }

    async def detect(self, entries: list[dict]) -> list[DetectionResult]:
        results: list[DetectionResult] = []
        if not entries:
            return results

        # --- Round number check ---
        for entry in entries:
            raw_amt = entry.get("amount_in_company_code_currency") or entry.get(
                "AmountInCompanyCodeCurrency", 0
            )
            amount = abs(float(raw_amt))

            if amount >= self.min_amount and amount % self.round_unit == 0:
                # Higher confidence for larger amounts
                confidence = min(0.7, 0.3 + (amount / (self.min_amount * 100)))
                results.append(
                    self._make_result(
                        entry,
                        anomaly_type="Round Number Amount",
                        confidence=confidence,
                        description=(
                            f"Amount {amount:,.2f} is a round number "
                            f"(divisible by {self.round_unit:,})"
                        ),
                        details={"round_unit": self.round_unit},
                    )
                )

        # --- Benford's law check ---
        benford_results = self._benford_check(entries)
        results.extend(benford_results)

        return results

    def _benford_check(self, entries: list[dict]) -> list[DetectionResult]:
        """Check first-digit distribution against Benford's law."""
        results: list[DetectionResult] = []

        # Collect first digits
        first_digits: list[int] = []
        for entry in entries:
            raw_amt = entry.get("amount_in_company_code_currency") or entry.get(
                "AmountInCompanyCodeCurrency", 0
            )
            amount = abs(float(raw_amt))
            if amount >= 1:
                first_digit = int(str(amount).lstrip("0").lstrip(".")[0])
                if 1 <= first_digit <= 9:
                    first_digits.append(first_digit)

        n = len(first_digits)
        if n < 50:
            # Not enough data for meaningful Benford analysis
            return results

        digit_counts = Counter(first_digits)
        chi_sq = 0.0
        for digit in range(1, 10):
            observed = digit_counts.get(digit, 0)
            expected = BENFORD_EXPECTED[digit] * n
            if expected > 0:
                chi_sq += (observed - expected) ** 2 / expected

        if chi_sq > self.benford_chi_sq_threshold:
            # Benford violation detected -- flag the most deviant entries
            # Find which digits are over-represented
            over_represented: set[int] = set()
            for digit in range(1, 10):
                observed_pct = digit_counts.get(digit, 0) / n
                if observed_pct > BENFORD_EXPECTED[digit] * 1.5:
                    over_represented.add(digit)

            if over_represented:
                for entry in entries:
                    raw_amt = entry.get("amount_in_company_code_currency") or entry.get(
                        "AmountInCompanyCodeCurrency", 0
                    )
                    amount = abs(float(raw_amt))
                    if amount < 1:
                        continue
                    first_digit = int(str(amount).lstrip("0").lstrip(".")[0])
                    if first_digit in over_represented:
                        confidence = min(0.6, chi_sq / (self.benford_chi_sq_threshold * 5))
                        results.append(
                            self._make_result(
                                entry,
                                anomaly_type="Benford's Law Deviation",
                                confidence=confidence,
                                description=(
                                    f"First digit {first_digit} is over-represented "
                                    f"(chi-sq={chi_sq:.1f}, threshold={self.benford_chi_sq_threshold})"
                                ),
                                details={
                                    "chi_squared": round(chi_sq, 2),
                                    "first_digit": first_digit,
                                    "observed_pct": round(digit_counts.get(first_digit, 0) / n, 4),
                                    "expected_pct": BENFORD_EXPECTED[first_digit],
                                },
                            )
                        )

        return results

    def _make_result(
        self,
        entry: dict,
        *,
        anomaly_type: str,
        confidence: float,
        description: str,
        details: dict,
    ) -> DetectionResult:
        raw_amt = entry.get("amount_in_company_code_currency") or entry.get(
            "AmountInCompanyCodeCurrency", 0
        )
        fy_raw = entry.get("fiscal_year") or entry.get("FiscalYear", "")
        return DetectionResult(
            detector_name=self.name,
            anomaly_type=anomaly_type,
            confidence=confidence,
            document_number=entry.get("accounting_document") or entry.get("AccountingDocument"),
            company_code=entry.get("company_code") or entry.get("CompanyCode"),
            fiscal_year=int(fy_raw) if fy_raw else None,
            posting_date=entry.get("posting_date") or entry.get("PostingDate"),
            amount=Decimal(str(raw_amt)),
            currency=entry.get("company_code_currency") or entry.get("CompanyCodeCurrency", ""),
            details=details,
            description=description,
        )
