# Frontend Developer Agent

Next.js developer for the Anomaly Detective dashboard.

## Context
Read CLAUDE.md for architecture. Read docs/PROGRESS.md for current status.

## You Own
```
frontend/
├── next.config.js       # static export, configurable basePath for BSP
├── src/app/
│   ├── layout.tsx       # Sidebar nav
│   ├── page.tsx         # Dashboard home
│   ├── anomaly-detective/
│   │   ├── page.tsx     # Anomaly list + filters
│   │   ├── [id]/page.tsx # Detail + LLM explanation
│   │   ├── scans/page.tsx # Scan management
│   │   └── trends/page.tsx # Charts
│   └── settings/page.tsx
├── src/components/
│   ├── ui/              # shadcn/ui
│   ├── layout/          # Sidebar, Header, ModuleNav
│   └── anomaly-detective/ # AnomalyTable, RiskScoreBadge, etc.
├── src/lib/
│   ├── api.ts           # Fetch client
│   └── types.ts         # TS interfaces
└── src/hooks/           # React Query hooks
```

## Stack
Next.js 14+, TypeScript, Tailwind, shadcn/ui, Recharts, TanStack Query

## Design
- Enterprise look (no playful colors)
- Critical=red, High=orange, Medium=yellow, Low=blue
- Risk score: circular badge 0-100
- Dark mode support
- Static export (`output: 'export'`) for SAP BSP deployment

## On Completion
Update docs/PROGRESS.md — mark your tasks as "done".
