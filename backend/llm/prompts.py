"""Prompt templates for LLM-powered anomaly analysis.

All templates use Python str.format() for variable substitution.
IMPORTANT: Only aggregated anomaly metadata is sent to the LLM --
never raw financial data, line items, or personally identifiable information.
"""

# ---------------------------------------------------------------------------
# System prompt: establishes the AI persona
# ---------------------------------------------------------------------------

ANOMALY_EXPLANATION_SYSTEM: str = (
    "You are an expert SAP financial auditor and forensic accountant AI assistant. "
    "You analyze anomalies detected in SAP ERP financial data. "
    "Your role is to:\n"
    "- Provide clear, actionable root cause analysis\n"
    "- Assess risk from a financial audit perspective\n"
    "- Recommend concrete next steps for the audit team\n"
    "- Identify patterns that may indicate fraud, error, or control weakness\n\n"
    "You receive only aggregated anomaly metadata -- never raw transaction data. "
    "Always respond in structured, professional language suitable for audit reports. "
    "When uncertain, state your confidence level and suggest further investigation."
)

# ---------------------------------------------------------------------------
# Single anomaly explanation
# ---------------------------------------------------------------------------

ANOMALY_EXPLANATION_USER: str = (
    "Analyze the following anomaly detected in SAP financial data:\n\n"
    "**Anomaly Details:**\n"
    "- Type: {anomaly_type}\n"
    "- Detector: {detector_name}\n"
    "- Risk Score: {risk_score}/100\n"
    "- Severity: {severity}\n"
    "- Document Number: {document_number}\n"
    "- Amount: {amount} {currency}\n"
    "- GL Account: {gl_account}\n"
    "- Description: {description}\n"
    "- Detector Details: {detector_details}\n\n"
    "Provide your analysis in the following JSON format:\n"
    "{{\n"
    '  "root_cause_analysis": "Detailed explanation of likely root causes",\n'
    '  "risk_assessment": "Assessment of financial and compliance risk",\n'
    '  "recommended_actions": ["action 1", "action 2", "action 3"],\n'
    '  "similar_patterns": "Description of similar patterns to watch for",\n'
    '  "confidence_level": "HIGH/MEDIUM/LOW"\n'
    "}}"
)

# ---------------------------------------------------------------------------
# Batch summary for a scan run
# ---------------------------------------------------------------------------

ANOMALY_BATCH_SUMMARY: str = (
    "You are reviewing the results of an SAP financial anomaly detection scan.\n\n"
    "**Scan Overview:**\n"
    "- Company Code: {company_code}\n"
    "- Scan Period: {date_from} to {date_to}\n"
    "- Total Documents Scanned: {total_documents}\n"
    "- Anomalies Found: {anomalies_found}\n"
    "- Severity Breakdown: CRITICAL={critical}, HIGH={high}, MEDIUM={medium}, LOW={low}\n\n"
    "**Top Anomalies:**\n"
    "{anomaly_list}\n\n"
    "Provide an executive summary in the following JSON format:\n"
    "{{\n"
    '  "executive_summary": "2-3 sentence overview of findings",\n'
    '  "key_risk_areas": ["area 1", "area 2", "area 3"],\n'
    '  "top_recommendations": ["recommendation 1", "recommendation 2", "recommendation 3"],\n'
    '  "overall_risk_level": "HIGH/MEDIUM/LOW",\n'
    '  "requires_immediate_attention": true/false\n'
    "}}"
)
