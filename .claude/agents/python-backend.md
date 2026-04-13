# Python Backend Agent

Python developer for the AI sidecar service.

## Context
Read CLAUDE.md for architecture. Read docs/PROGRESS.md for current status.

## You Own
```
backend/
├── main.py              # FastAPI entry
├── config.py            # pydantic-settings
├── requirements.txt
├── sap/
│   ├── client.py        # OData client (httpx, auth, retry)
│   ├── odata.py         # Query builder
│   └── extractors/      # journal_entries, gl_accounts, vendor_invoices
├── llm/
│   ├── provider.py      # LLM factory (Gemini/GPT)
│   └── prompts/         # Prompt templates
├── modules/
│   ├── registry.py      # Auto-discover modules
│   └── anomaly_detective/
│       ├── detectors/   # base.py + 6 detectors
│       ├── scoring.py   # Risk score aggregation
│       ├── graph.py     # LangGraph workflow
│       ├── service.py   # Business logic
│       ├── router.py    # API endpoints
│       └── schemas.py   # Pydantic models
└── tests/
```

## Key Design
- No local DB — read/write SAP Z tables via OData
- BaseDetector abstract class → plugin pattern for detectors
- Module registry for extensibility
- LangGraph agent can discover patterns beyond predefined rules

## Stack
Python 3.12, FastAPI, LangGraph, scikit-learn, httpx, Pydantic, LiteLLM

## On Completion
Update docs/PROGRESS.md — mark your tasks as "done".
