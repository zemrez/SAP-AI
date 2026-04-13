"""Amount anomaly detector -- statistical outlier detection per GL account."""

from __future__ import annotations

import logging
import math
from collections import defaultdict
from decimal import Decimal

from .base import BaseDetector, DetectionResult

logger = logging.getLogger(__name__)


class AmountDetector(BaseDetector):
    """Flag journal entries with statistically unusual amounts.

    - Entries where |amount| > mean + threshold * stddev for that GL account
    - Negative amounts on normally-positive accounts
    """

    name = "amount"
    description = "Statistical outlier detection on transaction amounts per GL account"

    def __init__(self, config: dict | None = None) -> None:
        cfg = {**self.get_default_config(), **(config or {})}
        self.std_dev_threshold: float = cfg["std_dev_threshold"]
        self.min_entries_for_stats: int = cfg["min_entries_for_stats"]

    def get_default_config(self) -> dict:
        return {
            "std_dev_threshold": 3,
            "min_entries_for_stats": 10,
        }

    async def detect(self, entries: list[dict]) -> list[DetectionResult]:
        results: list[DetectionResult] = []
        if not entries:
            return results

        # Group amounts by GL account
        account_amounts: dict[str, list[float]] = defaultdict(list)
        for entry in entries:
            gl = entry.get("gl_account") or entry.get("GLAccount", "")
            raw_amt = entry.get("amount_in_company_code_currency") or entry.get(
                "AmountInCompanyCodeCurrency", 0
            )
            account_amounts[gl].append(float(raw_amt))

        # Pre-compute stats per account
        account_stats: dict[str, tuple[float, float, float]] = {}  # mean, std, pct_positive
        for gl, amounts in account_amounts.items():
            if len(amounts) < self.min_entries_for_stats:
                continue
            mean = sum(amounts) / len(amounts)
            variance = sum((a - mean) ** 2 for a in amounts) / len(amounts)
            std = math.sqrt(variance)
            positive_count = sum(1 for a in amounts if a > 0)
            pct_positive = positive_count / len(amounts)
            account_stats[gl] = (mean, std, pct_positive)

        # Scan each entry
        for entry in entries:
            gl = entry.get("gl_account") or entry.get("GLAccount", "")
            raw_amt = entry.get("amount_in_company_code_currency") or entry.get(
                "AmountInCompanyCodeCurrency", 0
            )
            amount = float(raw_amt)

            if gl not in account_stats:
                continue

            mean, std, pct_positive = account_stats[gl]

            # Standard deviation outlier
            if std > 0 and abs(amount - mean) > self.std_dev_threshold * std:
                z_score = abs(amount - mean) / std
                confidence = min(1.0, (z_score - self.std_dev_threshold) / self.std_dev_threshold + 0.5)
                results.append(
                    self._make_result(
                        entry,
                        anomaly_type="Statistical Outlier",
                        confidence=confidence,
                        description=(
                            f"Amount {amount:,.2f} is {z_score:.1f} std devs from mean "
                            f"{mean:,.2f} for GL account {gl}"
                        ),
                        details={"z_score": round(z_score, 2), "mean": round(mean, 2), "std": round(std, 2)},
                    )
                )

            # Negative amount on normally-positive account
            if amount < 0 and pct_positive > 0.9:
                confidence = min(1.0, pct_positive)
                results.append(
                    self._make_result(
                        entry,
                        anomaly_type="Negative on Positive Account",
                        confidence=confidence,
                        description=(
                            f"Negative amount {amount:,.2f} on GL {gl} where "
                            f"{pct_positive*100:.0f}% of entries are positive"
                        ),
                        details={"pct_positive": round(pct_positive, 4)},
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
