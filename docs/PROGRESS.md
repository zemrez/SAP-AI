# Progress Tracker

## Current Phase: 4 — Polish (done)

### Phase 1: Foundation
| Task | Agent | Status |
|------|-------|--------|
| Z table definitions | abap-architect | done — 5 tables: ZANM_SCAN_RUN, ZANM_ANOMALY, ZANM_DET_RULE, ZANM_CONFIG, ZANM_ML_MODEL |
| CDS views + OData services | abap-architect | done — 5 CDS views (2 interface, 1 journal, 2 consumption) + OData V4 service def/bindings + auth object + 2 utility classes |
| Data elements & domains | abap-architect | done — 6 domains (ZANM_D_SCAN_STATUS, ZANM_D_SEVERITY, ZANM_D_ANOM_STATUS, ZANM_D_RISK_SCORE, ZANM_D_DETECTOR, ZANM_D_SCAN_TYPE) + 6 matching data elements in abap/dictionary/ |
| Business logic classes | abap-architect | done — ZCL_ANM_ORCHESTRATOR (scan lifecycle + HTTP sidecar call), ZCL_ANM_SAP_READER (BKPF/BSEG/BSIK/BSAK/FAGLFLEXT reads), ZCL_ANM_ODATA_HANDLER (CRUD + filtered list + deep entity), ZCL_ANM_CONFIG_MANAGER (config CRUD + defaults), ZCL_ANM_RULE_MANAGER (rule CRUD + 6 default detector configs) |
| Exception class | abap-architect | done — ZCX_ANM_EXCEPTION (CX_STATIC_CHECK, 6 text IDs, MV_DETAILS attribute) |
| Background job program | abap-architect | done — ZANM_SCHEDULED_SCAN report (SM36, selection screen, BAL logging, error handling) |
| Job scheduler class | abap-architect | done — ZCL_ANM_JOB_SCHEDULER (SM36 JOB_OPEN/CLOSE, cancel, status check) |
| FastAPI scaffold + config | python-backend | done — FastAPI app, config.py (pydantic-settings), CORS, health endpoint, module registry, .env.example |
| SAP OData client | python-backend | done — SAPClient (httpx async, CSRF, retry/backoff), ODataQueryBuilder, 3 extractors (journal entries, GL accounts, vendor invoices), Pydantic schemas, anomaly_detective module scaffold, 16 passing tests |
| Next.js init + layout | frontend-dev | done — Next.js 16 static export, shadcn/ui, TanStack Query, Sidebar+Header layout, dashboard page, anomaly-detective/scans/trends/settings placeholder pages, RiskScoreBadge, api.ts + types.ts |

### Phase 2: Detection Engine
| Task | Agent | Status |
|------|-------|--------|
| BaseDetector + 5 detectors | python-backend | done — BaseDetector ABC + DetectionResult model in detectors/base.py; AmountDetector (std dev outlier + negative-on-positive), DuplicateDetector (exact + near duplicate), TimingDetector (off-hours + weekend + holiday), CombinationDetector (rare GL pairs), RoundNumberDetector (round amounts + Benford's law) |
| ML detector (Isolation Forest) | python-backend | done — MLDetector with 7-feature extraction (log amount, hour, day_of_week, is_weekend, account/vendor frequency, is_round), IsolationForest fit_model + detect, auto-fits if no pre-trained model |
| Scoring engine | python-backend | done — ScoringEngine aggregates DetectionResults by document, weighted-sum scoring (6 detector weights), severity assignment (LOW/MEDIUM/HIGH/CRITICAL), ScoredAnomaly model |
| API endpoints (router + schemas) | python-backend | done — 10 real endpoints replacing placeholders: POST/GET scans, GET/PATCH anomalies, GET/PUT rules, GET stats + trends; Pydantic request/response models; AnomalyDetectiveService orchestrating SAP read->detect->score->write; 35 passing tests (24 detector + 11 scoring) |

### Phase 3: AI Integration
| Task | Agent | Status |
|------|-------|--------|
| LLM provider + prompts | python-backend | done — backend/llm/provider.py (litellm factory, Gemini/GPT-4o), backend/llm/prompts.py (explanation + batch summary templates) |
| LangGraph workflow | python-backend | done — workflow.py (StateGraph: extract→detect→score→explain→persist), ScanState TypedDict, error handling, 83 total tests passing |
| Dashboard UI (anomaly list) | frontend-dev | done — Full anomaly table with filters (severity/status), sorting, pagination, bulk actions, search |
| Anomaly detail page | frontend-dev | done — Detail page with risk score, AI explanation card, assignment, resolution notes, activity timeline (query param route: /detail?id=) |
| Scan management page | frontend-dev | done — New scan dialog, scans table with status badges, auto-refresh for running scans |

### Phase 4: Polish
| Task | Agent | Status |
|------|-------|--------|
| Trend analysis page | frontend-dev | done — recharts charts (line, area, bar, pie), summary cards, granularity toggle, top detectors |
| Detection rules config UI | frontend-dev | done — rule cards with toggle/slider/input, presets (conservative/balanced/aggressive), save/reset, per-rule save |
| Scheduled scans (ABAP job) | abap-architect | done — ZANM_SCHEDULED_SCAN report + ZCL_ANM_JOB_SCHEDULER class |
| End-to-end testing | test-runner | done — 20 integration tests (health, scans, anomalies, rules, stats, trends), 103 total tests passing |
