# SAP Anomaly Detective

## What
SAP add-on: detects financial anomalies in ERP data. Module 1 of Financial Intelligence Platform.

## Architecture
- ABAP: Z tables (ZANM_*), CDS views, OData services, BSP app, auth
- Python sidecar (same network): FastAPI + LangGraph + ML + LLM
- Frontend: Next.js static export → SAP BSP → Fiori Launchpad
- LLM: Gemini/GPT-4o (only anomaly summaries, never raw data)
- No external DB — SAP Z tables only
- Deploy: 1 Transport Request + 1 install script (no Docker)

## Structure
```
abap/                  # ABAP artifacts
backend/               # Python sidecar
  sap/                 # SAP OData client (shared)
  llm/                 # LLM abstraction (shared)
  modules/             # Feature modules
    anomaly_detective/ # Module 1
frontend/              # Next.js (static export)
```

## Commands
```bash
cd backend && .venv/Scripts/uvicorn main:app --port 8011 --reload
cd frontend && npm run dev
cd frontend && npm run build   # static export
```

## Rules
- ABAP: Z prefix, OO classes, BUKRS-level auth
- Python: type hints, Pydantic, async/await
- Frontend: TypeScript strict, shadcn/ui, Tailwind
- English comments, modular structure

## Progress
Check docs/PROGRESS.md for current phase and completed work.
