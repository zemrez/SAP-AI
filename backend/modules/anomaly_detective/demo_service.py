"""In-memory demo service — no SAP connection needed.

Used when DEMO_MODE=true in .env. Returns realistic mock data.
"""

from __future__ import annotations

import random
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any


# --- Seed demo data ---

_DETECTORS = [
    ("amount", "Amount Outlier", "STATISTICAL", "Detects statistical outliers in transaction amounts"),
    ("duplicate", "Duplicate Detection", "PATTERN", "Detects duplicate or near-duplicate journal entries"),
    ("timing", "Timing Anomaly", "RULE_BASED", "Detects postings during off-hours or weekends"),
    ("combination", "Rare GL Combination", "PATTERN", "Detects unusual GL account pairings"),
    ("round_number", "Round Number", "RULE_BASED", "Detects suspiciously round amounts and Benford violations"),
    ("ml", "ML Isolation Forest", "ML", "Machine learning anomaly detection"),
]

_SEVERITIES = ["LOW", "MEDIUM", "HIGH", "CRITICAL"]
_STATUSES = ["OPEN", "INVESTIGATING", "RESOLVED", "FALSE_POSITIVE"]
_COMPANIES = ["1000", "2000", "3000"]


def _gen_anomalies(n: int = 60) -> list[dict[str, Any]]:
    now = datetime.now(timezone.utc)
    anomalies = []
    for i in range(n):
        det = random.choice(_DETECTORS)
        sev = random.choices(_SEVERITIES, weights=[30, 35, 25, 10])[0]
        status = random.choices(_STATUSES, weights=[50, 20, 20, 10])[0]
        risk = {"LOW": random.randint(5, 30), "MEDIUM": random.randint(30, 60),
                "HIGH": random.randint(60, 85), "CRITICAL": random.randint(85, 100)}[sev]
        detected = now - timedelta(days=random.randint(0, 45), hours=random.randint(0, 23))
        anomalies.append({
            "id": uuid.uuid4().hex[:12],
            "scan_run_id": f"SCAN{(i // 10) + 1:03d}",
            "rule_id": det[0],
            "rule_name": det[1],
            "severity": sev,
            "status": status,
            "risk_score": risk,
            "company_code": random.choice(_COMPANIES),
            "fiscal_year": "2025",
            "fiscal_period": f"{random.randint(1, 12):02d}",
            "document_number": f"{random.randint(100000000, 999999999)}",
            "vendor_id": f"V{random.randint(1000, 9999)}" if random.random() > 0.3 else None,
            "amount": round(random.uniform(500, 500000), 2),
            "currency": "EUR",
            "description": f"{det[1]}: {det[3]}",
            "details": {},
            "llm_explanation": f"This anomaly was flagged by the {det[1]} detector. "
                              f"The transaction shows unusual patterns that warrant review." if sev in ("HIGH", "CRITICAL") else None,
            "detected_at": detected.isoformat(),
            "updated_at": detected.isoformat(),
        })
    anomalies.sort(key=lambda a: a["detected_at"], reverse=True)
    return anomalies


def _gen_scans() -> list[dict[str, Any]]:
    now = datetime.now(timezone.utc)
    scans = []
    for i in range(7):
        started = now - timedelta(days=i * 5, hours=random.randint(0, 12))
        scans.append({
            "id": f"SCAN{i + 1:03d}",
            "status": "COMPLETED",
            "company_code": random.choice(_COMPANIES),
            "fiscal_year": "2025",
            "fiscal_period": None,
            "started_at": started.isoformat(),
            "completed_at": (started + timedelta(minutes=random.randint(2, 15))).isoformat(),
            "anomaly_count": random.randint(3, 15),
            "error_message": None,
            "triggered_by": "DEMO",
        })
    return scans


# Singleton data
_anomalies: list[dict] = _gen_anomalies()
_scans: list[dict] = _gen_scans()


class DemoService:
    """Drop-in replacement for AnomalyDetectiveService with in-memory data."""

    async def run_scan(self, company_code: str, fiscal_year: str, **kwargs: Any) -> dict:
        scan_id = f"SCAN{len(_scans) + 1:03d}"
        now = datetime.now(timezone.utc)
        new_anomalies = _gen_anomalies(random.randint(3, 10))
        for a in new_anomalies:
            a["scan_run_id"] = scan_id
            a["company_code"] = company_code
        _anomalies.extend(new_anomalies)
        scan = {
            "scan_id": scan_id, "status": "COMPLETED", "company_code": company_code,
            "fiscal_year": fiscal_year, "total_documents": random.randint(100, 5000),
            "anomalies_found": len(new_anomalies),
            "detectors_used": [d[0] for d in _DETECTORS],
            "severity_breakdown": {s: sum(1 for a in new_anomalies if a["severity"] == s) for s in _SEVERITIES},
            "started_at": now.isoformat(),
            "completed_at": (now + timedelta(seconds=random.randint(5, 30))).isoformat(),
        }
        _scans.insert(0, {
            "id": scan_id, "status": "COMPLETED", "company_code": company_code,
            "fiscal_year": fiscal_year, "started_at": scan["started_at"],
            "completed_at": scan["completed_at"], "anomaly_count": len(new_anomalies),
            "triggered_by": "USER",
        })
        return scan

    async def get_scans(self, *, page: int = 1, size: int = 20) -> dict:
        start = (page - 1) * size
        return {"items": _scans[start:start + size], "total": len(_scans), "page": page, "size": size}

    async def get_scan(self, scan_id: str) -> dict | None:
        return next((s for s in _scans if s["id"] == scan_id), None)

    async def get_anomalies(self, *, severity: str | None = None, detector: str | None = None,
                            status: str | None = None, date_from: str | None = None,
                            date_to: str | None = None, min_score: float | None = None,
                            page: int = 1, size: int = 20) -> dict:
        filtered = list(_anomalies)
        if severity:
            filtered = [a for a in filtered if a["severity"] == severity]
        if detector:
            filtered = [a for a in filtered if a["rule_id"] == detector]
        if status:
            filtered = [a for a in filtered if a["status"] == status]
        if min_score is not None:
            filtered = [a for a in filtered if a["risk_score"] >= min_score]
        start = (page - 1) * size
        return {"items": filtered[start:start + size], "total": len(filtered), "page": page, "size": size}

    async def get_anomaly(self, anomaly_id: str) -> dict | None:
        return next((a for a in _anomalies if a["id"] == anomaly_id), None)

    async def update_anomaly_status(self, anomaly_id: str, *, status: str,
                                     assigned_to: str | None = None,
                                     resolution_note: str | None = None) -> dict | None:
        for a in _anomalies:
            if a["id"] == anomaly_id:
                a["status"] = status
                if assigned_to:
                    a["assigned_to"] = assigned_to
                return {"anomaly_id": anomaly_id, "status": status}
        return None

    async def get_rules(self) -> list[dict]:
        return [
            {
                "RuleId": d[0], "Name": d[1], "RuleType": d[2],
                "Description": d[3], "IsActive": True,
                "ConfigJson": "{}"
            }
            for d in _DETECTORS
        ]

    async def update_rule(self, rule_id: str, *, is_active: bool | None = None,
                          config_json: str | None = None) -> dict | None:
        for d in _DETECTORS:
            if d[0] == rule_id:
                return {"rule_id": rule_id, "IsActive": is_active}
        return None

    async def get_stats(self) -> dict:
        by_sev = {s: sum(1 for a in _anomalies if a["severity"] == s) for s in _SEVERITIES}
        by_det = {}
        for a in _anomalies:
            by_det[a["rule_id"]] = by_det.get(a["rule_id"], 0) + 1
        return {
            "total_anomalies": len(_anomalies),
            "by_severity": by_sev,
            "by_detector": by_det,
            "recent_scans": _scans[:5],
        }

    async def get_trends(self, *, period: str = "day", days: int = 30) -> list[dict]:
        now = datetime.now(timezone.utc)
        cutoff = now - timedelta(days=days)
        recent = [a for a in _anomalies if a["detected_at"] >= cutoff.isoformat()]
        buckets: dict[str, dict[str, int]] = {}
        for a in recent:
            key = a["detected_at"][:10]
            if key not in buckets:
                buckets[key] = {"total": 0, "LOW": 0, "MEDIUM": 0, "HIGH": 0, "CRITICAL": 0}
            buckets[key]["total"] += 1
            buckets[key][a["severity"]] += 1
        return [{"period": k, **v} for k, v in sorted(buckets.items())]
