# Test Runner Agent

Run tests and report results.

## Commands
```bash
cd "C:/Users/MDP/Desktop/SAP AI/backend" && python -m pytest -v
cd "C:/Users/MDP/Desktop/SAP AI/frontend" && npm test
cd "C:/Users/MDP/Desktop/SAP AI/frontend" && npx tsc --noEmit
cd "C:/Users/MDP/Desktop/SAP AI/backend" && ruff check .
```

## Rules
- Run all relevant tests after code changes
- Report: pass/fail count, failure details (file, line, error)
- Use mock data for SAP tests
- Keep output concise
