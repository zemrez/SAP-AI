"""Anomaly Detective API endpoints -- Phase 2 implementation."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from .schemas import AnomalySeverity, AnomalyStatus
from .service import AnomalyDetectiveService

router = APIRouter()

# Shared service instance (uses default SAPClient from config)
_service: AnomalyDetectiveService | None = None


def _get_service() -> AnomalyDetectiveService:
    global _service
    if _service is None:
        import os
        if os.getenv("DEMO_MODE", "").lower() in ("true", "1", "yes"):
            from .demo_service import DemoService
            _service = DemoService()  # type: ignore[assignment]
        else:
            _service = AnomalyDetectiveService()
    return _service


# ------------------------------------------------------------------
# Request / Response models
# ------------------------------------------------------------------


class CreateScanRequest(BaseModel):
    company_code: str = Field(..., max_length=4, description="SAP company code (BUKRS)")
    fiscal_year: str = Field(..., max_length=4, description="Fiscal year")
    scan_type: str = Field("FULL", description="Scan type: FULL, INCREMENTAL")
    detectors: list[str] | None = Field(None, description="List of detector names to enable")
    detector_configs: dict[str, dict] | None = Field(None, description="Per-detector config overrides")


class ScanSummaryResponse(BaseModel):
    scan_id: str
    status: str
    company_code: str | None = None
    fiscal_year: str | None = None
    total_documents: int = 0
    anomalies_found: int = 0
    detectors_used: list[str] = Field(default_factory=list)
    severity_breakdown: dict[str, int] = Field(default_factory=dict)
    started_at: str | None = None
    completed_at: str | None = None
    error: str | None = None


class PaginatedResponse(BaseModel):
    items: list[dict[str, Any]] = Field(default_factory=list)
    total: int = 0
    page: int = 1
    size: int = 20


class UpdateAnomalyRequest(BaseModel):
    status: str = Field(..., description="New status: REVIEWED, CONFIRMED, FALSE_POSITIVE, RESOLVED")
    assigned_to: str | None = Field(None, max_length=12)
    resolution_note: str | None = Field(None, max_length=1000)


class UpdateRuleRequest(BaseModel):
    is_active: bool | None = None
    config_json: str | None = None


class StatsResponse(BaseModel):
    total_anomalies: int = 0
    by_severity: dict[str, int] = Field(default_factory=dict)
    by_detector: dict[str, int] = Field(default_factory=dict)
    recent_scans: list[dict[str, Any]] = Field(default_factory=list)


# ------------------------------------------------------------------
# Scan endpoints
# ------------------------------------------------------------------


@router.post("/scans", response_model=ScanSummaryResponse)
async def create_scan(body: CreateScanRequest) -> ScanSummaryResponse:
    """Trigger a new anomaly detection scan."""
    svc = _get_service()
    result = await svc.run_scan(
        body.company_code,
        body.fiscal_year,
        scan_type=body.scan_type,
        detectors=body.detectors,
        detector_configs=body.detector_configs,
    )
    return ScanSummaryResponse(**result)


@router.get("/scans", response_model=PaginatedResponse)
async def list_scans(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
) -> PaginatedResponse:
    """List all scan runs with pagination."""
    svc = _get_service()
    data = await svc.get_scans(page=page, size=size)
    return PaginatedResponse(**data)


@router.get("/scans/{scan_id}")
async def get_scan(scan_id: str) -> dict[str, Any]:
    """Get scan run details."""
    svc = _get_service()
    result = await svc.get_scan(scan_id)
    if result is None:
        raise HTTPException(status_code=404, detail=f"Scan {scan_id} not found")
    return result


# ------------------------------------------------------------------
# Anomaly endpoints
# ------------------------------------------------------------------


@router.get("/anomalies", response_model=PaginatedResponse)
async def list_anomalies(
    severity: str | None = Query(None, description="Filter by severity: LOW, MEDIUM, HIGH, CRITICAL"),
    detector: str | None = Query(None, description="Filter by detector name / rule ID"),
    status: str | None = Query(None, description="Filter by status: NEW, REVIEWED, CONFIRMED, FALSE_POSITIVE, RESOLVED"),
    date_from: str | None = Query(None, description="Start date (YYYY-MM-DD)"),
    date_to: str | None = Query(None, description="End date (YYYY-MM-DD)"),
    min_score: float | None = Query(None, ge=0, le=100, description="Minimum risk score"),
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
) -> PaginatedResponse:
    """List anomalies with optional filters and pagination."""
    svc = _get_service()
    data = await svc.get_anomalies(
        severity=severity,
        detector=detector,
        status=status,
        date_from=date_from,
        date_to=date_to,
        min_score=min_score,
        page=page,
        size=size,
    )
    return PaginatedResponse(**data)


@router.get("/anomalies/{anomaly_id}")
async def get_anomaly(anomaly_id: str) -> dict[str, Any]:
    """Get a single anomaly with full details."""
    svc = _get_service()
    result = await svc.get_anomaly(anomaly_id)
    if result is None:
        raise HTTPException(status_code=404, detail=f"Anomaly {anomaly_id} not found")
    return result


@router.patch("/anomalies/{anomaly_id}")
async def update_anomaly(anomaly_id: str, body: UpdateAnomalyRequest) -> dict[str, Any]:
    """Update anomaly status (review, confirm, mark as false positive, resolve)."""
    svc = _get_service()
    result = await svc.update_anomaly_status(
        anomaly_id,
        status=body.status,
        assigned_to=body.assigned_to,
        resolution_note=body.resolution_note,
    )
    if result is None:
        raise HTTPException(status_code=404, detail=f"Anomaly {anomaly_id} not found or update failed")
    return result


# ------------------------------------------------------------------
# Rules endpoints
# ------------------------------------------------------------------


@router.get("/rules")
async def list_rules() -> list[dict[str, Any]]:
    """List all detection rules and their configurations."""
    svc = _get_service()
    return await svc.get_rules()


@router.put("/rules/{rule_id}")
async def update_rule(rule_id: str, body: UpdateRuleRequest) -> dict[str, Any]:
    """Update a detection rule configuration."""
    svc = _get_service()
    result = await svc.update_rule(
        rule_id,
        is_active=body.is_active,
        config_json=body.config_json,
    )
    if result is None:
        raise HTTPException(status_code=404, detail=f"Rule {rule_id} not found or no changes provided")
    return result


# ------------------------------------------------------------------
# Stats endpoints
# ------------------------------------------------------------------


@router.get("/stats", response_model=StatsResponse)
async def get_stats() -> StatsResponse:
    """Dashboard statistics: total anomalies, breakdowns, recent scans."""
    svc = _get_service()
    data = await svc.get_stats()
    return StatsResponse(**data)


@router.get("/stats/trends")
async def get_trends(
    period: str = Query("day", description="Aggregation period: day or week"),
    days: int = Query(30, ge=1, le=365, description="Number of days to look back"),
) -> list[dict[str, Any]]:
    """Time-series anomaly count data for charts."""
    svc = _get_service()
    return await svc.get_trends(period=period, days=days)
