"""Timing anomaly detector -- flags off-hours, weekend, and holiday postings."""

from __future__ import annotations

import logging
from datetime import datetime
from decimal import Decimal

from .base import BaseDetector, DetectionResult

logger = logging.getLogger(__name__)


def _parse_date(d: str) -> datetime | None:
    if not d:
        return None
    for fmt in ("%Y-%m-%d", "%Y-%m-%dT%H:%M:%S", "%Y%m%d"):
        try:
            return datetime.strptime(d[:19], fmt)
        except ValueError:
            continue
    return None


class TimingDetector(BaseDetector):
    """Flag entries posted during unusual times.

    - Off-hours postings (e.g. 22:00-05:00)
    - Weekend postings (Saturday/Sunday)
    - Holiday postings (configurable list)
    """

    name = "timing"
    description = "Detects postings made during off-hours, weekends, or holidays"

    def __init__(self, config: dict | None = None) -> None:
        cfg = {**self.get_default_config(), **(config or {})}
        self.off_hours_start: int = cfg["off_hours_start"]
        self.off_hours_end: int = cfg["off_hours_end"]
        self.flag_weekends: bool = cfg["flag_weekends"]
        self.holidays: list[str] = cfg["holidays"]  # list of "YYYY-MM-DD"

    def get_default_config(self) -> dict:
        return {
            "off_hours_start": 22,
            "off_hours_end": 5,
            "flag_weekends": True,
            "holidays": [],
        }

    async def detect(self, entries: list[dict]) -> list[DetectionResult]:
        results: list[DetectionResult] = []
        holiday_set = set(self.holidays)

        for entry in entries:
            pdate_str = entry.get("posting_date") or entry.get("PostingDate", "")
            pdate = _parse_date(pdate_str)
            if not pdate:
                continue

            # Off-hours check (only meaningful if time info is present)
            hour = pdate.hour
            is_off_hours = False
            if self.off_hours_start > self.off_hours_end:
                # Wraps midnight, e.g. 22:00 - 05:00
                is_off_hours = hour >= self.off_hours_start or hour < self.off_hours_end
            else:
                is_off_hours = self.off_hours_start <= hour < self.off_hours_end

            if is_off_hours and hour != 0:
                # hour == 0 often means date-only with no time info
                results.append(
                    self._make_result(
                        entry,
                        anomaly_type="Off-Hours Posting",
                        confidence=0.6,
                        description=(
                            f"Posted at {hour:02d}:00, outside normal hours "
                            f"({self.off_hours_end:02d}:00-{self.off_hours_start:02d}:00)"
                        ),
                        details={"hour": hour},
                    )
                )

            # Weekend check
            if self.flag_weekends and pdate.weekday() >= 5:
                day_name = "Saturday" if pdate.weekday() == 5 else "Sunday"
                results.append(
                    self._make_result(
                        entry,
                        anomaly_type="Weekend Posting",
                        confidence=0.5,
                        description=f"Posted on {day_name} ({pdate_str})",
                        details={"day_of_week": pdate.weekday(), "day_name": day_name},
                    )
                )

            # Holiday check
            date_key = pdate.strftime("%Y-%m-%d")
            if date_key in holiday_set:
                results.append(
                    self._make_result(
                        entry,
                        anomaly_type="Holiday Posting",
                        confidence=0.55,
                        description=f"Posted on holiday {date_key}",
                        details={"holiday_date": date_key},
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
