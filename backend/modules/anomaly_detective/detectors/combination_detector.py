"""Account combination detector -- flags rare debit/credit account pairings."""

from __future__ import annotations

import logging
from collections import defaultdict
from decimal import Decimal

from .base import BaseDetector, DetectionResult

logger = logging.getLogger(__name__)


class CombinationDetector(BaseDetector):
    """Flag unusual debit/credit GL account combinations.

    Builds a frequency table of (debit_account, credit_account) pairs from
    historical data and flags pairs that occur very rarely.
    """

    name = "combination"
    description = "Detects rare GL account debit/credit pairings"

    def __init__(self, config: dict | None = None) -> None:
        cfg = {**self.get_default_config(), **(config or {})}
        self.frequency_threshold: float = cfg["frequency_threshold"]
        self.min_history_days: int = cfg["min_history_days"]

    def get_default_config(self) -> dict:
        return {
            "frequency_threshold": 0.001,
            "min_history_days": 365,
        }

    async def detect(self, entries: list[dict]) -> list[DetectionResult]:
        results: list[DetectionResult] = []
        if not entries:
            return results

        # Build pairs from entries: group by document, separate debits/credits
        doc_sides: dict[str, dict[str, list[dict]]] = defaultdict(lambda: {"D": [], "C": []})
        for entry in entries:
            doc = entry.get("accounting_document") or entry.get("AccountingDocument", "")
            bukrs = entry.get("company_code") or entry.get("CompanyCode", "")
            dc = entry.get("debit_credit_code") or entry.get("DebitCreditCode", "")
            key = f"{bukrs}_{doc}"
            if dc in ("S", "D", "H", "C"):
                side = "D" if dc in ("S", "D") else "C"
                doc_sides[key][side].append(entry)

        # Build frequency table of (debit_gl, credit_gl) pairs
        pair_counts: dict[tuple[str, str], int] = defaultdict(int)
        pair_entries: dict[tuple[str, str], list[dict]] = defaultdict(list)
        total_pairs = 0

        for doc_key, sides in doc_sides.items():
            for d_entry in sides["D"]:
                d_gl = d_entry.get("gl_account") or d_entry.get("GLAccount", "")
                for c_entry in sides["C"]:
                    c_gl = c_entry.get("gl_account") or c_entry.get("GLAccount", "")
                    pair = (d_gl, c_gl)
                    pair_counts[pair] += 1
                    pair_entries[pair].append(d_entry)
                    total_pairs += 1

        if total_pairs == 0:
            return results

        # Flag rare pairs
        for pair, count in pair_counts.items():
            frequency = count / total_pairs
            if frequency < self.frequency_threshold:
                for entry in pair_entries[pair]:
                    confidence = min(1.0, max(0.3, 1.0 - (frequency / self.frequency_threshold)))
                    results.append(
                        self._make_result(
                            entry,
                            anomaly_type="Rare Account Combination",
                            confidence=confidence,
                            description=(
                                f"Debit {pair[0]} / Credit {pair[1]} occurs {count} time(s) "
                                f"({frequency*100:.4f}% of all pairs, threshold {self.frequency_threshold*100:.3f}%)"
                            ),
                            details={
                                "debit_account": pair[0],
                                "credit_account": pair[1],
                                "pair_count": count,
                                "total_pairs": total_pairs,
                                "frequency": round(frequency, 6),
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
