"""Pydantic models for the Anomaly Detective module.

These mirror the ABAP Z table structures that back the OData communication:
- ZANM_SCAN_RUN   -> ScanRun
- ZANM_ANOMALY    -> Anomaly
- ZANM_DET_RULE   -> DetectionRule
- ZANM_RULE_PARAM -> RuleParameter
- ZANM_ANOM_ITEM  -> AnomalyItem
- ZANM_SCAN_LOG   -> ScanLog
"""

from datetime import datetime
from decimal import Decimal
from enum import Enum

from pydantic import BaseModel, Field


class ScanStatus(str, Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class AnomalySeverity(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class AnomalyStatus(str, Enum):
    NEW = "NEW"
    REVIEWED = "REVIEWED"
    CONFIRMED = "CONFIRMED"
    FALSE_POSITIVE = "FALSE_POSITIVE"
    RESOLVED = "RESOLVED"


class DetectionRuleType(str, Enum):
    BENFORD = "BENFORD"
    DUPLICATE = "DUPLICATE"
    ROUND_AMOUNT = "ROUND_AMOUNT"
    WEEKEND_POSTING = "WEEKEND_POSTING"
    THRESHOLD = "THRESHOLD"
    ML_ISOLATION_FOREST = "ML_ISOLATION_FOREST"


# -- ZANM_SCAN_RUN --
class ScanRun(BaseModel):
    """Mirrors ZANM_SCAN_RUN Z table."""

    scan_id: str = Field(..., alias="ScanId", max_length=32)
    company_code: str = Field(..., alias="CompanyCode", max_length=4)
    fiscal_year: str = Field(..., alias="FiscalYear", max_length=4)
    status: ScanStatus = Field(ScanStatus.PENDING, alias="Status")
    started_at: datetime | None = Field(None, alias="StartedAt")
    completed_at: datetime | None = Field(None, alias="CompletedAt")
    total_documents: int = Field(0, alias="TotalDocuments")
    anomalies_found: int = Field(0, alias="AnomaliesFound")
    created_by: str = Field("", alias="CreatedBy")
    created_at: datetime | None = Field(None, alias="CreatedAt")

    model_config = {"populate_by_name": True}


# -- ZANM_ANOMALY --
class Anomaly(BaseModel):
    """Mirrors ZANM_ANOMALY Z table."""

    anomaly_id: str = Field(..., alias="AnomalyId", max_length=32)
    scan_id: str = Field(..., alias="ScanId", max_length=32)
    rule_id: str = Field(..., alias="RuleId", max_length=20)
    severity: AnomalySeverity = Field(..., alias="Severity")
    status: AnomalyStatus = Field(AnomalyStatus.NEW, alias="Status")
    risk_score: Decimal = Field(..., alias="RiskScore")
    title: str = Field(..., alias="Title", max_length=200)
    description: str = Field("", alias="Description")
    ai_summary: str = Field("", alias="AiSummary")
    company_code: str = Field(..., alias="CompanyCode", max_length=4)
    fiscal_year: str = Field(..., alias="FiscalYear", max_length=4)
    affected_amount: Decimal = Field(Decimal("0"), alias="AffectedAmount")
    currency: str = Field("", alias="Currency", max_length=5)
    created_at: datetime | None = Field(None, alias="CreatedAt")

    model_config = {"populate_by_name": True}


# -- ZANM_ANOM_ITEM --
class AnomalyItem(BaseModel):
    """Mirrors ZANM_ANOM_ITEM Z table — links anomaly to SAP documents."""

    item_id: str = Field(..., alias="ItemId", max_length=32)
    anomaly_id: str = Field(..., alias="AnomalyId", max_length=32)
    accounting_document: str = Field(..., alias="AccountingDocument", max_length=10)
    accounting_document_item: str = Field("", alias="AccountingDocumentItem", max_length=3)
    company_code: str = Field(..., alias="CompanyCode", max_length=4)
    fiscal_year: str = Field(..., alias="FiscalYear", max_length=4)
    amount: Decimal = Field(..., alias="Amount")
    currency: str = Field("", alias="Currency", max_length=5)

    model_config = {"populate_by_name": True}


# -- ZANM_DET_RULE --
class DetectionRule(BaseModel):
    """Mirrors ZANM_DET_RULE Z table."""

    rule_id: str = Field(..., alias="RuleId", max_length=20)
    rule_type: DetectionRuleType = Field(..., alias="RuleType")
    name: str = Field(..., alias="Name", max_length=100)
    description: str = Field("", alias="Description")
    is_active: bool = Field(True, alias="IsActive")
    severity_default: AnomalySeverity = Field(AnomalySeverity.MEDIUM, alias="SeverityDefault")

    model_config = {"populate_by_name": True}


# -- ZANM_RULE_PARAM --
class RuleParameter(BaseModel):
    """Mirrors ZANM_RULE_PARAM Z table."""

    rule_id: str = Field(..., alias="RuleId", max_length=20)
    param_name: str = Field(..., alias="ParamName", max_length=40)
    param_value: str = Field(..., alias="ParamValue", max_length=200)
    param_description: str = Field("", alias="ParamDescription")

    model_config = {"populate_by_name": True}


# -- ZANM_SCAN_LOG --
class ScanLog(BaseModel):
    """Mirrors ZANM_SCAN_LOG Z table."""

    log_id: str = Field(..., alias="LogId", max_length=32)
    scan_id: str = Field(..., alias="ScanId", max_length=32)
    log_level: str = Field("INFO", alias="LogLevel", max_length=10)
    message: str = Field(..., alias="Message")
    timestamp: datetime | None = Field(None, alias="Timestamp")

    model_config = {"populate_by_name": True}
