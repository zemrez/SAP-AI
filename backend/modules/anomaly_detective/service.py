"""Anomaly Detective service layer -- orchestrates detection workflows.

Phase 3: Uses LangGraph workflow for scan execution with LLM integration.
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime
from typing import Any

from sap.client import SAPClient, SAPClientError
from sap.odata import ODataQueryBuilder

from .detectors import (
    AmountDetector,
    BaseDetector,
    CombinationDetector,
    DuplicateDetector,
    MLDetector,
    RoundNumberDetector,
    TimingDetector,
)
from .schemas import AnomalySeverity, AnomalyStatus, ScanStatus
from .scoring import ScoredAnomaly, ScoringEngine
from .workflow import scan_workflow

logger = logging.getLogger(__name__)

# OData service path for the Anomaly Detective custom Z service
ZANM_SERVICE = "ZANM_ODATA_SRV"


class AnomalyDetectiveService:
    """Orchestrates: SAP read -> detect -> score -> explain -> SAP write.

    Uses the LangGraph scan_workflow for the full pipeline.
    """

    # Available detector classes keyed by name
    DETECTOR_CLASSES: dict[str, type[BaseDetector]] = {
        "amount": AmountDetector,
        "duplicate": DuplicateDetector,
        "timing": TimingDetector,
        "combination": CombinationDetector,
        "round_number": RoundNumberDetector,
        "ml": MLDetector,
    }

    def __init__(self, sap_client: SAPClient | None = None) -> None:
        self.sap = sap_client or SAPClient()
        self.scoring = ScoringEngine()

    # ------------------------------------------------------------------
    # Scan lifecycle (via LangGraph workflow)
    # ------------------------------------------------------------------

    async def run_scan(
        self,
        company_code: str,
        fiscal_year: str,
        *,
        scan_type: str = "FULL",
        detectors: list[str] | None = None,
        detector_configs: dict[str, dict] | None = None,
    ) -> dict[str, Any]:
        """Execute a full anomaly detection scan via the LangGraph workflow.

        The workflow handles:
        1. Extract journal entries from SAP
        2. Run all enabled detectors in parallel
        3. Aggregate risk scores
        4. Generate LLM explanations for HIGH/CRITICAL anomalies
        5. Persist results back to SAP
        """
        scan_id = uuid.uuid4().hex[:32].upper()
        started_at = datetime.utcnow().isoformat()

        # Create initial scan run record in SAP
        try:
            await self.sap.post(
                f"{ZANM_SERVICE}/ScanRunSet",
                json={
                    "ScanId": scan_id,
                    "CompanyCode": company_code,
                    "FiscalYear": fiscal_year,
                    "Status": ScanStatus.RUNNING.value,
                    "StartedAt": started_at,
                    "TotalDocuments": 0,
                    "AnomaliesFound": 0,
                },
            )
        except SAPClientError:
            logger.warning("Could not create scan run in SAP (service may not be deployed yet).")

        # Build initial state for the workflow
        initial_state = {
            "scan_id": scan_id,
            "bukrs": company_code,
            "date_from": f"{fiscal_year}-01-01",
            "date_to": f"{fiscal_year}-12-31",
            "scan_type": scan_type,
            "detectors": detectors,
            "detector_configs": detector_configs,
            "started_at": started_at,
        }

        # Invoke the LangGraph workflow
        final_state = await scan_workflow.ainvoke(initial_state)

        status = final_state.get("status", "FAILED")
        scored = final_state.get("scored_anomalies", [])

        # Determine detectors used
        enabled = detectors or list(self.DETECTOR_CLASSES.keys())
        detectors_used = [
            name for name in enabled if name in self.DETECTOR_CLASSES
        ]

        result: dict[str, Any] = {
            "scan_id": scan_id,
            "status": status,
            "company_code": company_code,
            "fiscal_year": fiscal_year,
            "total_documents": final_state.get("total_documents", 0),
            "anomalies_found": final_state.get("anomalies_found", 0),
            "detectors_used": detectors_used,
            "severity_breakdown": self._severity_breakdown(scored),
            "started_at": started_at,
            "completed_at": final_state.get("completed_at"),
        }

        if status == "FAILED":
            result["error"] = final_state.get("error", "Unknown error")

        return result

    async def _update_scan_status(
        self,
        scan_id: str,
        status: ScanStatus,
        *,
        total_documents: int | None = None,
        anomalies_found: int | None = None,
        completed_at: str | None = None,
    ) -> None:
        payload: dict[str, Any] = {"Status": status.value}
        if total_documents is not None:
            payload["TotalDocuments"] = total_documents
        if anomalies_found is not None:
            payload["AnomaliesFound"] = anomalies_found
        if completed_at is not None:
            payload["CompletedAt"] = completed_at
        try:
            await self.sap.patch(
                f"{ZANM_SERVICE}/ScanRunSet('{scan_id}')",
                json=payload,
            )
        except SAPClientError:
            logger.warning("Could not update scan status in SAP for %s.", scan_id)

    async def _write_anomalies(
        self,
        scan_id: str,
        company_code: str,
        fiscal_year: str,
        scored: list[ScoredAnomaly],
    ) -> int:
        """Write scored anomalies to SAP Z table."""
        written = 0
        for anomaly in scored:
            anomaly_id = uuid.uuid4().hex[:32].upper()
            # Determine primary detector (highest-weighted trigger)
            primary_detector = anomaly.detectors_triggered[0] if anomaly.detectors_triggered else "unknown"
            try:
                await self.sap.post(
                    f"{ZANM_SERVICE}/AnomalySet",
                    json={
                        "AnomalyId": anomaly_id,
                        "ScanId": scan_id,
                        "RuleId": primary_detector,
                        "Severity": anomaly.severity.value,
                        "Status": AnomalyStatus.NEW.value,
                        "RiskScore": str(anomaly.risk_score),
                        "Title": anomaly.description[:200],
                        "Description": anomaly.description,
                        "CompanyCode": company_code,
                        "FiscalYear": fiscal_year,
                        "AffectedAmount": str(anomaly.amount or 0),
                        "Currency": anomaly.currency or "",
                    },
                )
                written += 1
            except SAPClientError:
                logger.warning("Failed to write anomaly %s to SAP.", anomaly_id)
        return written

    @staticmethod
    def _severity_breakdown(scored: list[ScoredAnomaly]) -> dict[str, int]:
        breakdown: dict[str, int] = {"LOW": 0, "MEDIUM": 0, "HIGH": 0, "CRITICAL": 0}
        for a in scored:
            breakdown[a.severity.value] += 1
        return breakdown

    # ------------------------------------------------------------------
    # Query methods
    # ------------------------------------------------------------------

    async def get_scans(self, *, page: int = 1, size: int = 20) -> dict[str, Any]:
        """List scan runs from SAP."""
        skip = (page - 1) * size
        qb = (
            ODataQueryBuilder()
            .orderby("StartedAt", descending=True)
            .top(size)
            .skip(skip)
            .inlinecount()
        )
        try:
            data = await self.sap.get(f"{ZANM_SERVICE}/ScanRunSet?{qb.build()}&$format=json")
            results = data.get("d", {}).get("results", data.get("value", []))
            count = int(data.get("d", {}).get("__count", len(results)))
            return {"items": results, "total": count, "page": page, "size": size}
        except SAPClientError as exc:
            logger.error("Failed to fetch scans: %s", exc)
            return {"items": [], "total": 0, "page": page, "size": size}

    async def get_scan(self, scan_id: str) -> dict[str, Any] | None:
        """Get a single scan run."""
        try:
            data = await self.sap.get(f"{ZANM_SERVICE}/ScanRunSet('{scan_id}')?$format=json")
            return data.get("d", data)
        except SAPClientError:
            return None

    async def get_anomalies(
        self,
        *,
        severity: str | None = None,
        detector: str | None = None,
        status: str | None = None,
        date_from: str | None = None,
        date_to: str | None = None,
        min_score: float | None = None,
        page: int = 1,
        size: int = 20,
    ) -> dict[str, Any]:
        """List anomalies with filters."""
        skip = (page - 1) * size
        qb = (
            ODataQueryBuilder()
            .orderby("RiskScore", descending=True)
            .top(size)
            .skip(skip)
            .inlinecount()
        )
        if severity:
            qb.filter(f"Severity eq '{severity}'")
        if detector:
            qb.filter(f"RuleId eq '{detector}'")
        if status:
            qb.filter(f"Status eq '{status}'")
        if date_from:
            qb.filter(f"CreatedAt ge datetime'{date_from}T00:00:00'")
        if date_to:
            qb.filter(f"CreatedAt le datetime'{date_to}T23:59:59'")
        if min_score is not None:
            qb.filter(f"RiskScore ge {min_score}")

        try:
            data = await self.sap.get(f"{ZANM_SERVICE}/AnomalySet?{qb.build()}&$format=json")
            results = data.get("d", {}).get("results", data.get("value", []))
            count = int(data.get("d", {}).get("__count", len(results)))
            return {"items": results, "total": count, "page": page, "size": size}
        except SAPClientError as exc:
            logger.error("Failed to fetch anomalies: %s", exc)
            return {"items": [], "total": 0, "page": page, "size": size}

    async def get_anomaly(self, anomaly_id: str) -> dict[str, Any] | None:
        """Get a single anomaly with full details."""
        try:
            data = await self.sap.get(
                f"{ZANM_SERVICE}/AnomalySet('{anomaly_id}')?$expand=to_Items&$format=json"
            )
            return data.get("d", data)
        except SAPClientError:
            return None

    async def update_anomaly_status(
        self,
        anomaly_id: str,
        *,
        status: str,
        assigned_to: str | None = None,
        resolution_note: str | None = None,
    ) -> dict[str, Any] | None:
        """Update anomaly status (reviewed, confirmed, false positive, resolved)."""
        payload: dict[str, Any] = {"Status": status}
        if assigned_to:
            payload["AssignedTo"] = assigned_to
        if resolution_note:
            payload["ResolutionNote"] = resolution_note
        try:
            await self.sap.patch(f"{ZANM_SERVICE}/AnomalySet('{anomaly_id}')", json=payload)
            return {"anomaly_id": anomaly_id, "status": status}
        except SAPClientError as exc:
            logger.error("Failed to update anomaly %s: %s", anomaly_id, exc)
            return None

    async def get_rules(self) -> list[dict]:
        """List all detection rules from SAP."""
        try:
            data = await self.sap.get(f"{ZANM_SERVICE}/DetectionRuleSet?$format=json")
            return data.get("d", {}).get("results", data.get("value", []))
        except SAPClientError:
            # Return built-in defaults if SAP is not available
            return [
                {
                    "RuleId": name,
                    "Name": cls.name if hasattr(cls, "name") else name,
                    "Description": cls.description if hasattr(cls, "description") else "",
                    "IsActive": True,
                    "ConfigJson": str(cls().get_default_config()),
                }
                for name, cls in self.DETECTOR_CLASSES.items()
            ]

    async def update_rule(
        self, rule_id: str, *, is_active: bool | None = None, config_json: str | None = None
    ) -> dict[str, Any] | None:
        """Update a detection rule configuration."""
        payload: dict[str, Any] = {}
        if is_active is not None:
            payload["IsActive"] = is_active
        if config_json is not None:
            payload["ConfigJson"] = config_json
        if not payload:
            return None
        try:
            await self.sap.patch(f"{ZANM_SERVICE}/DetectionRuleSet('{rule_id}')", json=payload)
            return {"rule_id": rule_id, **payload}
        except SAPClientError as exc:
            logger.error("Failed to update rule %s: %s", rule_id, exc)
            return None

    async def get_stats(self) -> dict[str, Any]:
        """Aggregate dashboard statistics."""
        try:
            # Get anomaly counts by severity
            data = await self.sap.get(f"{ZANM_SERVICE}/AnomalySet?$inlinecount=allpages&$top=0&$format=json")
            total = int(data.get("d", {}).get("__count", 0))
        except SAPClientError:
            total = 0

        by_severity: dict[str, int] = {}
        for sev in AnomalySeverity:
            try:
                qb = ODataQueryBuilder().filter(f"Severity eq '{sev.value}'").inlinecount().top(0)
                data = await self.sap.get(f"{ZANM_SERVICE}/AnomalySet?{qb.build()}&$format=json")
                by_severity[sev.value] = int(data.get("d", {}).get("__count", 0))
            except SAPClientError:
                by_severity[sev.value] = 0

        # Recent scans
        scans_data = await self.get_scans(page=1, size=5)

        return {
            "total_anomalies": total,
            "by_severity": by_severity,
            "by_detector": {},  # Would need GROUP BY which OData V2 doesn't natively support
            "recent_scans": scans_data["items"],
        }

    async def get_trends(self, *, period: str = "day", days: int = 30) -> list[dict]:
        """Time-series trend data for anomaly counts."""
        from datetime import datetime, timedelta

        end = datetime.utcnow()
        start = end - timedelta(days=days)
        qb = (
            ODataQueryBuilder()
            .filter(f"CreatedAt ge datetime'{start.strftime('%Y-%m-%dT00:00:00')}'")
            .select("CreatedAt", "Severity", "RiskScore")
            .top(5000)
        )
        try:
            data = await self.sap.get(f"{ZANM_SERVICE}/AnomalySet?{qb.build()}&$format=json")
            items = data.get("d", {}).get("results", data.get("value", []))
        except SAPClientError:
            items = []

        # Aggregate by period
        buckets: dict[str, dict[str, int]] = {}
        for item in items:
            created = item.get("CreatedAt", "")
            if not created:
                continue
            if period == "week":
                # Group by ISO week
                try:
                    dt = datetime.fromisoformat(created[:19])
                    key = f"{dt.isocalendar()[0]}-W{dt.isocalendar()[1]:02d}"
                except ValueError:
                    continue
            else:
                # Group by day
                key = created[:10]

            if key not in buckets:
                buckets[key] = {"total": 0, "LOW": 0, "MEDIUM": 0, "HIGH": 0, "CRITICAL": 0}
            buckets[key]["total"] += 1
            sev = item.get("Severity", "")
            if sev in buckets[key]:
                buckets[key][sev] += 1

        return [{"period": k, **v} for k, v in sorted(buckets.items())]
