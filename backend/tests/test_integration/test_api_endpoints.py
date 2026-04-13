"""End-to-end integration tests for all API endpoints.

Mocks _get_service() so no real SAP connection is needed.
"""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient, ASGITransport

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from main import app


@pytest.fixture
def mock_service():
    """Mock the entire service layer."""
    svc = AsyncMock()
    with patch("modules.anomaly_detective.router._get_service", return_value=svc):
        yield svc


@pytest.fixture
async def client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c


# --- Health ---

class TestHealth:
    @pytest.mark.asyncio
    async def test_health(self, client: AsyncClient):
        resp = await client.get("/health")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"


# --- Scans ---

class TestScans:
    @pytest.mark.asyncio
    async def test_create_scan(self, client: AsyncClient, mock_service: AsyncMock):
        mock_service.run_scan.return_value = {
            "scan_id": "S001", "status": "COMPLETED", "company_code": "1000",
            "fiscal_year": "2025", "total_documents": 10, "anomalies_found": 2,
            "detectors_used": ["amount"], "severity_breakdown": {"HIGH": 2},
            "started_at": "2025-01-01T00:00:00", "completed_at": "2025-01-01T00:01:00",
        }
        resp = await client.post(
            "/api/v1/anomaly-detective/scans",
            json={"company_code": "1000", "fiscal_year": "2025", "scan_type": "FULL"},
        )
        assert resp.status_code == 200
        assert resp.json()["scan_id"] == "S001"
        assert resp.json()["status"] == "COMPLETED"

    @pytest.mark.asyncio
    async def test_create_scan_missing_fields(self, client: AsyncClient):
        resp = await client.post("/api/v1/anomaly-detective/scans", json={})
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_list_scans(self, client: AsyncClient, mock_service: AsyncMock):
        mock_service.get_scans.return_value = {
            "items": [{"ScanId": "S001"}], "total": 1, "page": 1, "size": 20,
        }
        resp = await client.get("/api/v1/anomaly-detective/scans")
        assert resp.status_code == 200
        assert resp.json()["total"] == 1

    @pytest.mark.asyncio
    async def test_get_scan_found(self, client: AsyncClient, mock_service: AsyncMock):
        mock_service.get_scan.return_value = {"ScanId": "S001", "Status": "COMPLETED"}
        resp = await client.get("/api/v1/anomaly-detective/scans/S001")
        assert resp.status_code == 200
        assert resp.json()["ScanId"] == "S001"

    @pytest.mark.asyncio
    async def test_get_scan_not_found(self, client: AsyncClient, mock_service: AsyncMock):
        mock_service.get_scan.return_value = None
        resp = await client.get("/api/v1/anomaly-detective/scans/NOPE")
        assert resp.status_code == 404


# --- Anomalies ---

class TestAnomalies:
    @pytest.mark.asyncio
    async def test_list_anomalies(self, client: AsyncClient, mock_service: AsyncMock):
        mock_service.get_anomalies.return_value = {
            "items": [{"AnomalyId": "A001"}, {"AnomalyId": "A002"}],
            "total": 2, "page": 1, "size": 20,
        }
        resp = await client.get("/api/v1/anomaly-detective/anomalies")
        assert resp.status_code == 200
        assert resp.json()["total"] == 2

    @pytest.mark.asyncio
    async def test_list_anomalies_filters(self, client: AsyncClient, mock_service: AsyncMock):
        mock_service.get_anomalies.return_value = {"items": [], "total": 0, "page": 1, "size": 10}
        resp = await client.get(
            "/api/v1/anomaly-detective/anomalies",
            params={"severity": "CRITICAL", "min_score": 80, "page": 1, "size": 10},
        )
        assert resp.status_code == 200
        kw = mock_service.get_anomalies.call_args[1]
        assert kw["severity"] == "CRITICAL"
        assert kw["min_score"] == 80.0

    @pytest.mark.asyncio
    async def test_get_anomaly_found(self, client: AsyncClient, mock_service: AsyncMock):
        mock_service.get_anomaly.return_value = {"AnomalyId": "A001", "Severity": "HIGH"}
        resp = await client.get("/api/v1/anomaly-detective/anomalies/A001")
        assert resp.status_code == 200
        assert resp.json()["AnomalyId"] == "A001"

    @pytest.mark.asyncio
    async def test_get_anomaly_not_found(self, client: AsyncClient, mock_service: AsyncMock):
        mock_service.get_anomaly.return_value = None
        resp = await client.get("/api/v1/anomaly-detective/anomalies/NOPE")
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_update_anomaly_success(self, client: AsyncClient, mock_service: AsyncMock):
        mock_service.update_anomaly_status.return_value = {"anomaly_id": "A001", "status": "RESOLVED"}
        resp = await client.patch(
            "/api/v1/anomaly-detective/anomalies/A001",
            json={"status": "RESOLVED", "resolution_note": "OK"},
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "RESOLVED"

    @pytest.mark.asyncio
    async def test_update_anomaly_not_found(self, client: AsyncClient, mock_service: AsyncMock):
        mock_service.update_anomaly_status.return_value = None
        resp = await client.patch(
            "/api/v1/anomaly-detective/anomalies/NOPE",
            json={"status": "RESOLVED"},
        )
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_update_anomaly_invalid_body(self, client: AsyncClient):
        resp = await client.patch("/api/v1/anomaly-detective/anomalies/A001", json={})
        assert resp.status_code == 422


# --- Rules ---

class TestRules:
    @pytest.mark.asyncio
    async def test_list_rules(self, client: AsyncClient, mock_service: AsyncMock):
        mock_service.get_rules.return_value = [
            {"RuleId": "amount", "Name": "Amount", "IsActive": True},
            {"RuleId": "duplicate", "Name": "Duplicate", "IsActive": True},
        ]
        resp = await client.get("/api/v1/anomaly-detective/rules")
        assert resp.status_code == 200
        assert len(resp.json()) == 2

    @pytest.mark.asyncio
    async def test_update_rule_success(self, client: AsyncClient, mock_service: AsyncMock):
        mock_service.update_rule.return_value = {"rule_id": "amount", "IsActive": False}
        resp = await client.put(
            "/api/v1/anomaly-detective/rules/amount",
            json={"is_active": False},
        )
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_update_rule_not_found(self, client: AsyncClient, mock_service: AsyncMock):
        mock_service.update_rule.return_value = None
        resp = await client.put(
            "/api/v1/anomaly-detective/rules/nope",
            json={"is_active": False},
        )
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_update_rule_no_changes(self, client: AsyncClient, mock_service: AsyncMock):
        mock_service.update_rule.return_value = None
        resp = await client.put("/api/v1/anomaly-detective/rules/amount", json={})
        assert resp.status_code == 404


# --- Stats & Trends ---

class TestStats:
    @pytest.mark.asyncio
    async def test_get_stats(self, client: AsyncClient, mock_service: AsyncMock):
        mock_service.get_stats.return_value = {
            "total_anomalies": 42, "by_severity": {"HIGH": 20, "LOW": 22},
            "by_detector": {}, "recent_scans": [],
        }
        resp = await client.get("/api/v1/anomaly-detective/stats")
        assert resp.status_code == 200
        assert resp.json()["total_anomalies"] == 42

    @pytest.mark.asyncio
    async def test_get_trends(self, client: AsyncClient, mock_service: AsyncMock):
        mock_service.get_trends.return_value = [
            {"period": "2025-01-01", "total": 5},
        ]
        resp = await client.get(
            "/api/v1/anomaly-detective/stats/trends",
            params={"period": "day", "days": 7},
        )
        assert resp.status_code == 200
        assert len(resp.json()) == 1

    @pytest.mark.asyncio
    async def test_get_trends_invalid_days(self, client: AsyncClient, mock_service: AsyncMock):
        resp = await client.get(
            "/api/v1/anomaly-detective/stats/trends",
            params={"days": 0},
        )
        assert resp.status_code == 422
