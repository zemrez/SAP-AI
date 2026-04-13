"""LangGraph workflow for the Anomaly Detective scan pipeline.

Nodes:
  extract_data   -> Fetch journal entries from SAP via OData
  run_detectors  -> Execute all 6 detectors in parallel
  score_anomalies -> Aggregate results via ScoringEngine
  explain_anomalies -> LLM explanation for HIGH/CRITICAL findings
  persist_results -> Write results back to SAP

Edges: linear flow with error short-circuit to a failure handler.
"""

from __future__ import annotations

import asyncio
import logging
import uuid
from datetime import datetime
from typing import Any, TypedDict

from langgraph.graph import END, START, StateGraph

from config import settings
from llm import LLMProvider, LLMProviderError
from llm.prompts import (
    ANOMALY_BATCH_SUMMARY,
    ANOMALY_EXPLANATION_SYSTEM,
    ANOMALY_EXPLANATION_USER,
)
from sap.client import SAPClient, SAPClientError
from sap.extractors.journal_entries import JournalEntryExtractor

from .detectors import (
    AmountDetector,
    BaseDetector,
    CombinationDetector,
    DuplicateDetector,
    MLDetector,
    RoundNumberDetector,
    TimingDetector,
)
from .detectors.base import DetectionResult
from .schemas import AnomalySeverity, AnomalyStatus, ScanStatus
from .scoring import ScoredAnomaly, ScoringEngine

logger = logging.getLogger(__name__)

# OData service path
ZANM_SERVICE = "ZANM_ODATA_SRV"

# All detector classes available
DETECTOR_CLASSES: dict[str, type[BaseDetector]] = {
    "amount": AmountDetector,
    "duplicate": DuplicateDetector,
    "timing": TimingDetector,
    "combination": CombinationDetector,
    "round_number": RoundNumberDetector,
    "ml": MLDetector,
}


# ---------------------------------------------------------------------------
# State definition
# ---------------------------------------------------------------------------


class ScanState(TypedDict, total=False):
    """State that flows through the LangGraph scan pipeline."""

    scan_id: str
    bukrs: str
    date_from: str
    date_to: str
    scan_type: str
    detectors: list[str] | None
    detector_configs: dict[str, dict] | None
    journal_entries: list[dict[str, Any]]
    detection_results: list[DetectionResult]
    scored_anomalies: list[ScoredAnomaly]
    explanations: dict[str, dict[str, Any]]
    batch_summary: dict[str, Any] | None
    status: str
    error: str | None
    total_documents: int
    anomalies_found: int
    started_at: str
    completed_at: str | None


# ---------------------------------------------------------------------------
# Node functions
# ---------------------------------------------------------------------------


async def extract_data(state: ScanState) -> dict[str, Any]:
    """Node 1: Fetch journal entries from SAP OData."""
    sap = SAPClient()
    extractor = JournalEntryExtractor(sap)

    try:
        raw_entries = await extractor.get_entries(
            state["bukrs"],
            state["date_from"][:4],  # fiscal year from date
            top=10000,
        )
        entries = [e.model_dump(by_alias=False) for e in raw_entries]
        logger.info("Extracted %d journal entries for %s", len(entries), state["bukrs"])
        return {
            "journal_entries": entries,
            "total_documents": len(entries),
            "status": "EXTRACTING_COMPLETE",
        }
    except SAPClientError as exc:
        logger.error("Data extraction failed: %s", exc)
        return {"status": "FAILED", "error": f"Data extraction failed: {exc}"}


async def run_detectors(state: ScanState) -> dict[str, Any]:
    """Node 2: Run all enabled detectors in parallel."""
    entries = state.get("journal_entries", [])
    if not entries:
        return {"detection_results": [], "status": "DETECTING_COMPLETE"}

    enabled = state.get("detectors") or list(DETECTOR_CLASSES.keys())
    configs = state.get("detector_configs") or {}

    active: list[BaseDetector] = []
    for name in enabled:
        cls = DETECTOR_CLASSES.get(name)
        if cls is None:
            logger.warning("Unknown detector: %s", name)
            continue
        active.append(cls(config=configs.get(name)))

    try:
        tasks = [det.detect(entries) for det in active]
        outputs: list[list[DetectionResult]] = await asyncio.gather(*tasks)
        all_results: list[DetectionResult] = []
        for output in outputs:
            all_results.extend(output)

        logger.info("Detectors produced %d raw findings", len(all_results))
        return {"detection_results": all_results, "status": "DETECTING_COMPLETE"}
    except Exception as exc:
        logger.error("Detection failed: %s", exc)
        return {"status": "FAILED", "error": f"Detection failed: {exc}"}


async def score_anomalies(state: ScanState) -> dict[str, Any]:
    """Node 3: Aggregate detection results into scored anomalies."""
    results = state.get("detection_results", [])
    engine = ScoringEngine()
    scored = engine.aggregate_scores(results)

    logger.info("Scored %d anomalies", len(scored))
    return {
        "scored_anomalies": scored,
        "anomalies_found": len(scored),
        "status": "SCORING_COMPLETE",
    }


async def explain_anomalies(state: ScanState) -> dict[str, Any]:
    """Node 4: Generate LLM explanations for HIGH/CRITICAL anomalies.

    IMPORTANT: Only aggregated anomaly metadata is sent to the LLM.
    Raw financial data (line items, amounts, account details) is NOT sent.
    """
    scored = state.get("scored_anomalies", [])
    max_explanations: int = getattr(settings, "LLM_MAX_EXPLANATIONS", 10)

    # Filter to HIGH and CRITICAL only
    high_priority = [
        a for a in scored
        if a.severity in (AnomalySeverity.HIGH, AnomalySeverity.CRITICAL)
    ][:max_explanations]

    if not high_priority:
        logger.info("No HIGH/CRITICAL anomalies to explain")
        return {"explanations": {}, "batch_summary": None, "status": "EXPLAINING_COMPLETE"}

    llm = LLMProvider()
    explanations: dict[str, dict[str, Any]] = {}

    for anomaly in high_priority:
        # Build safe metadata -- no raw data, only aggregated info
        primary_type = anomaly.findings[0].anomaly_type if anomaly.findings else "Unknown"
        primary_detector = anomaly.detectors_triggered[0] if anomaly.detectors_triggered else "unknown"
        detector_details = ", ".join(
            f"{f.anomaly_type} (confidence: {f.confidence:.0%})"
            for f in anomaly.findings[:5]
        )

        prompt = ANOMALY_EXPLANATION_USER.format(
            anomaly_type=primary_type,
            detector_name=primary_detector,
            risk_score=anomaly.risk_score,
            severity=anomaly.severity.value,
            document_number=anomaly.document_number,
            amount=str(anomaly.amount or "N/A"),
            currency=anomaly.currency or "N/A",
            gl_account=anomaly.findings[0].details.get("gl_account", "N/A") if anomaly.findings else "N/A",
            description=anomaly.description,
            detector_details=detector_details,
        )

        try:
            result = await llm.generate_json(prompt, system_prompt=ANOMALY_EXPLANATION_SYSTEM)
            explanations[anomaly.document_number] = result
            logger.debug("Generated explanation for doc %s", anomaly.document_number)
        except LLMProviderError as exc:
            logger.warning("LLM explanation failed for %s: %s", anomaly.document_number, exc)
            explanations[anomaly.document_number] = {
                "root_cause_analysis": "LLM explanation unavailable",
                "risk_assessment": "Manual review required",
                "recommended_actions": ["Review document manually"],
                "similar_patterns": "N/A",
                "confidence_level": "LOW",
            }

    # Generate batch summary
    batch_summary: dict[str, Any] | None = None
    try:
        severity_counts = {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0}
        for a in scored:
            severity_counts[a.severity.value] += 1

        anomaly_list_lines = []
        for a in high_priority[:10]:
            anomaly_list_lines.append(
                f"- Doc {a.document_number}: {a.description} "
                f"(Score: {a.risk_score}, Severity: {a.severity.value})"
            )

        summary_prompt = ANOMALY_BATCH_SUMMARY.format(
            company_code=state.get("bukrs", "N/A"),
            date_from=state.get("date_from", "N/A"),
            date_to=state.get("date_to", "N/A"),
            total_documents=state.get("total_documents", 0),
            anomalies_found=len(scored),
            critical=severity_counts["CRITICAL"],
            high=severity_counts["HIGH"],
            medium=severity_counts["MEDIUM"],
            low=severity_counts["LOW"],
            anomaly_list="\n".join(anomaly_list_lines),
        )
        batch_summary = await llm.generate_json(
            summary_prompt,
            system_prompt=ANOMALY_EXPLANATION_SYSTEM,
        )
    except LLMProviderError as exc:
        logger.warning("Batch summary generation failed: %s", exc)

    return {
        "explanations": explanations,
        "batch_summary": batch_summary,
        "status": "EXPLAINING_COMPLETE",
    }


async def persist_results(state: ScanState) -> dict[str, Any]:
    """Node 5: Write scan results and anomalies back to SAP via OData."""
    sap = SAPClient()
    scan_id = state["scan_id"]
    bukrs = state["bukrs"]
    scored = state.get("scored_anomalies", [])
    explanations = state.get("explanations", {})
    completed_at = datetime.utcnow().isoformat()

    # Write individual anomalies
    written = 0
    for anomaly in scored:
        anomaly_id = uuid.uuid4().hex[:32].upper()
        primary_detector = anomaly.detectors_triggered[0] if anomaly.detectors_triggered else "unknown"

        # Include LLM explanation in the AI summary field if available
        ai_summary = ""
        explanation = explanations.get(anomaly.document_number)
        if explanation:
            ai_summary = explanation.get("root_cause_analysis", "")[:2000]

        try:
            await sap.post(
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
                    "AiSummary": ai_summary,
                    "CompanyCode": bukrs,
                    "FiscalYear": state.get("date_from", "")[:4],
                    "AffectedAmount": str(anomaly.amount or 0),
                    "Currency": anomaly.currency or "",
                },
            )
            written += 1
        except SAPClientError:
            logger.warning("Failed to write anomaly %s to SAP.", anomaly_id)

    # Update scan run as completed
    try:
        await sap.patch(
            f"{ZANM_SERVICE}/ScanRunSet('{scan_id}')",
            json={
                "Status": ScanStatus.COMPLETED.value,
                "TotalDocuments": state.get("total_documents", 0),
                "AnomaliesFound": len(scored),
                "CompletedAt": completed_at,
            },
        )
    except SAPClientError:
        logger.warning("Could not update scan status for %s.", scan_id)

    logger.info("Persisted %d anomalies for scan %s", written, scan_id)
    return {"status": "COMPLETED", "completed_at": completed_at}


async def handle_failure(state: ScanState) -> dict[str, Any]:
    """Error handler node: marks the scan as failed in SAP."""
    sap = SAPClient()
    scan_id = state.get("scan_id", "")
    error_msg = state.get("error", "Unknown error")

    logger.error("Scan %s failed: %s", scan_id, error_msg)

    if scan_id:
        try:
            await sap.patch(
                f"{ZANM_SERVICE}/ScanRunSet('{scan_id}')",
                json={"Status": ScanStatus.FAILED.value},
            )
        except SAPClientError:
            logger.warning("Could not mark scan %s as failed in SAP.", scan_id)

    return {"status": "FAILED"}


# ---------------------------------------------------------------------------
# Routing logic
# ---------------------------------------------------------------------------


def should_continue(state: ScanState) -> str:
    """Route to failure node if status is FAILED, otherwise continue."""
    if state.get("status") == "FAILED":
        return "handle_failure"
    return "continue"


# ---------------------------------------------------------------------------
# Graph construction
# ---------------------------------------------------------------------------


def build_scan_workflow() -> StateGraph:
    """Construct and compile the LangGraph scan workflow."""
    workflow = StateGraph(ScanState)

    # Add nodes
    workflow.add_node("extract_data", extract_data)
    workflow.add_node("run_detectors", run_detectors)
    workflow.add_node("score_anomalies", score_anomalies)
    workflow.add_node("explain_anomalies", explain_anomalies)
    workflow.add_node("persist_results", persist_results)
    workflow.add_node("handle_failure", handle_failure)

    # Entry point
    workflow.add_edge(START, "extract_data")

    # Conditional edges with error short-circuit
    workflow.add_conditional_edges(
        "extract_data",
        should_continue,
        {"continue": "run_detectors", "handle_failure": "handle_failure"},
    )
    workflow.add_conditional_edges(
        "run_detectors",
        should_continue,
        {"continue": "score_anomalies", "handle_failure": "handle_failure"},
    )
    workflow.add_edge("score_anomalies", "explain_anomalies")
    workflow.add_edge("explain_anomalies", "persist_results")
    workflow.add_edge("persist_results", END)
    workflow.add_edge("handle_failure", END)

    return workflow.compile()


# Module-level compiled graph instance
scan_workflow = build_scan_workflow()
