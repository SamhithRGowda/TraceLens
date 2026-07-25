# TraceLens

An AI Incident Intelligence Platform. When an AI application misbehaves,
TraceLens assembles the evidence, identifies the most probable root cause
(with cited evidence), and tracks the fix — rather than handing you raw
logs and leaving you to investigate manually.

## Status

Early development (MVP). Single-project, no auth, manual incident
creation. See `docs/` (coming soon) for architecture notes.

## Running locally

```bash
docker compose up --build
```

Then check:
- `http://localhost:8000/` — service info
- `http://localhost:8000/health` — API + database connectivity check

## Stack

- Backend: FastAPI, SQLAlchemy, PostgreSQL
- Frontend: React, TypeScript, Tailwind, Vite (coming Week 2)
- Infra: Docker
