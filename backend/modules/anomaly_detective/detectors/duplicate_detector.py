"""Duplicate entry detector -- finds exact and near-duplicate journal entries."""

from __future__ import annotations

import logging
from collections import defaultdict
from datetime import datetime, timedelta
from decimal import Decimal

from .base import BaseDetector, DetectionResult

logger = logging.getLogger(__name__)


def _parse_date(d: str) -> datetime | None:
    """Parse common SAP date formats."""
    if not d:
        return None
    for fmt in ("%Y-%m-%d", "%Y-%m-%dT%H:%M:%S", "%Y%m%d"):
        try:
            return datetime.strptime(d[:19], fmt)
        except ValueError:
            continue
    return None


class DuplicateDetector(BaseDetector):
    """Flag duplicate or near-duplicate journal entries.

    - Exact match: same (amount + vendor/reference + posting_date)
    - Near match: same amount + same GL account within time_window hours
    """

    name = "duplicate"
    description = "Detects duplicate or near-duplicate journal entries"

    def __init__(self, config: dict | None = None) -> None:
        cfg = {**self.get_default_config(), **(config or {})}
        self.time_window_hours: int = cfg["time_window_hours"]
        self.amount_tolerance: float = cfg["amount_tolerance"]

    def get_default_config(self) -> dict:
        return {
            "time_window_hours": 24,
            "amount_tolerance": 0.01,
        }

    async def detect(self, entries: list[dict]) -> list[DetectionResult]:
        results: list[DetectionResult] = []
        if not entries:
            return results

        # --- Exact duplicates: (amount, vendor/reference, posting_date) ---
        exact_groups: dict[tuple, list[dict]] = defaultdict(list)
        for entry in entries:
            amount = float(
                entry.get("amount_in_company_code_currency")
                or entry.get("AmountInCompanyCodeCurrency", 0)
            )
            vendor = (
                entry.get("reference_document")
                or entry.get("ReferenceDocument", "")
            )
            pdate = entry.get("posting_date") or entry.get("PostingDate", "")
            key = (round(amount, 2), vendor, pdate)
            exact_groups[key].append(entry)

        flagged_docs: set[str] = set()
        for key, group in exact_groups.items():
            if len(group) < 2:
                continue
            # Flag all entries in a duplicate group
            for entry in group:
                doc = entry.get("accounting_document") or entry.get("AccountingDocument", "")
                if doc in flagged_docs:
                    continue
                flagged_docs.add(doc)
                results.append(
                    self._make_result(
                        entry,
                        anomaly_type="Exact Duplicate",
                        confidence=0.85,
                        description=(
                            f"Document {doc} shares amount {key[0]:,.2f}, "
                            f"reference '{key[1]}', posting date {key[2]} "
                            f"with {len(group)-1} other entries"
                        ),
                        details={"group_size": len(group), "match_type": "exact"},
                    )
                )

        # --- Near duplicates: same amount + GL within time window ---
        gl_amount_groups: dict[tuple, list[dict]] = defaultdict(list)
        for entry in entries:
            amount = float(
                entry.get("amount_in_company_code_currency")
                or entry.get("AmountInCompanyCodeCurrency", 0)
            )
            gl = entry.get("gl_account") or entry.get("GLAccount", "")
            key = (round(amount, 2), gl)
            gl_amount_groups[key].append(entry)

        window = timedelta(hours=self.time_window_hours)
        for key, group in gl_amount_groups.items():
            if len(group) < 2:
                continue
            # Sort by posting date and find close pairs
            dated = []
            for e in group:
                pd = _parse_date(e.get("posting_date") or e.get("PostingDate", ""))
                if pd:
                    dated.append((pd, e))
            dated.sort(key=lambda x: x[0])

            for i in range(len(dated)):
                for j in range(i + 1, len(dated)):
                    if dated[j][0] - dated[i][0] > window:
                        break
                    for idx in (i, j):
                        doc = (
                            dated[idx][1].get("accounting_document")
                            or dated[idx][1].get("AccountingDocument", "")
                        )
                        if doc in flagged_docs:
                            continue
                        flagged_docs.add(doc)
                        results.append(
                            self._make_result(
                                dated[idx][1],
                                anomaly_type="Near Duplicate",
                                confidence=0.65,
                                description=(
                                    f"Document {doc} has same amount {key[0]:,.2f} and "
                                    f"GL {key[1]} as another entry within "
                                    f"{self.time_window_hours}h"
                                ),
                                details={"match_type": "near", "time_window_hours": self.time_window_hours},
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
