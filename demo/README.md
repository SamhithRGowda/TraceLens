# Order Status Agent — Ingestion Demo

Sprint 14 (Live-Agent Ingestion). Proves the SDK -> `POST /api/v1/events`
ingestion path with a real runnable agent, instead of synthetic/pre-created
trace JSON.

## What this is

A minimal scripted agent that:
1. Makes an initial (scripted) LLM call deciding to look up an order.
2. Calls a real `get_order_status()` function, which returns `SHIPPED`.
3. Makes a final (scripted) LLM call that claims the order was `DELIVERED`
   — a deliberate contradiction of the tool's `SHIPPED` result.

All three events are sent through the real `TraceLensClient` SDK, under one
`session_id`, so they land as one Trace on the backend.

**This is a deterministic, scripted controlled failure scenario — not an
organic model hallucination.** Both LLM steps are hardcoded strings, not
real OpenAI calls. That's intentional: the goal of this sprint is proving
the ingestion path works, which requires the contradiction to reproduce
identically every run. Whether real LLMs hallucinate this way "in the
wild" is a separate, already-validated question (see project handoff,
Section 6 — the original ground-truth test).

## Prerequisites

- Backend running (Docker Compose) and reachable at `http://localhost:8000`
- SDK installed in your active virtualenv:
  ```bash
  pip install -e sdk/
  ```

## Run it

```bash
.venv/bin/python demo/order_status_agent.py
```

(Using `.venv/bin/python` directly avoids depending on the current shell's
activation state. If you've already run `source .venv/bin/activate`, plain
`python demo/order_status_agent.py` also works, since `python` then
resolves to the same interpreter.)

Expected output:
```
Starting Order Status Agent run — session_id: <uuid>

[1/3] Sent llm_call (planning step) — measured <N>ms
[2/3] Sent tool_call (get_order_status -> SHIPPED) — measured <N>ms
[3/3] Sent llm_call (final response, claims DELIVERED) — measured <N>ms

Done. session_id: <uuid>
Use this session_id to create an incident and investigate — see demo/README.md.
```

If the backend is unreachable, the SDK will not raise — it logs a warning
per event and the script still completes. Check the backend is up if you
see `TraceLens: failed to send evidence` warnings.

## Manual next steps (not automated by this script, on purpose)

This script only proves ingestion. Creating an incident, linking evidence,
correlating, and investigating are deliberately separate, explicit actions
— matching the project's "no automatic incident creation" MVP philosophy.

**Verified workflow:** `Run agent → Query DB for evidence IDs → Create
incident → Link seed evidence → Correlate → Investigate → View in frontend`.

Correlation does not discover evidence on its own — it expands outward
from evidence *already linked* to the incident (same-trace expansion,
then the ±30s cross-trace window). An incident created with no linked
evidence and immediately correlated returns an empty evidence list —
confirmed by running that exact sequence. At least one seed evidence item
must be linked first.

**Why a direct database query, not an API call:** there is currently no
`GET` endpoint to look up evidence by `session_id` or `trace_id` — this is
a real, existing gap in the MVP API surface, not something this cleanup
adds or works around at the API level. This README does not invent such
an endpoint and no backend/API code was changed. For local development,
querying Postgres directly is the only way to retrieve the evidence IDs
belonging to a specific run, so that's what's documented below. This
keeps the workflow to a single agent run — the evidence linked to the
incident is the exact evidence that run produced, not a second, separate
trace.

### 1. Run the demo agent

```bash
.venv/bin/python demo/order_status_agent.py
```
This is the standard, non-interactive proof that ingestion works — three
events land on the backend under one `session_id`, printed at the end.

### 2. Copy the printed `session_id`

You'll use this one value for both the database query below and to
identify this run going forward — no second run needed.

### 3. Query the database for this run's evidence IDs

```bash
docker compose exec db psql -U tracelens -d tracelens -c "SELECT e.id, e.evidence_type, e.timestamp FROM evidence e JOIN traces t ON e.trace_id = t.id WHERE t.session_id = '<session_id>' ORDER BY e.timestamp;"
```
Replace `<session_id>` with the value from step 2. This is a direct
Postgres query against the `evidence`/`traces` tables — a local-dev-only
substitute for the missing lookup endpoint noted above, not a new API
surface. Expect three rows, ordered by timestamp: the planning `llm_call`,
the `tool_call`, and the final `llm_call` that claims `DELIVERED`.

### 4. Use the returned evidence IDs as seed evidence

Note the three `id` values from the query result — these are what you'll
link to the incident in step 6.

### 5. Create the incident

```bash
curl -s -X POST http://localhost:8000/api/v1/incidents \
  -H "Content-Type: application/json" \
  -d '{
    "project_name": "order-status-agent",
    "title": "Order status contradiction",
    "description": "Agent claimed DELIVERED after tool reported SHIPPED"
  }'
```
Note the returned incident `id`.

### 6. Link the seed evidence

```bash
curl -s -X POST http://localhost:8000/api/v1/incidents/<incident_id>/evidence \
  -H "Content-Type: application/json" \
  -d '{
    "evidence_ids": [
      "<evidence_id_1>",
      "<evidence_id_2>",
      "<evidence_id_3>"
    ]
  }'
```
Use the three evidence IDs from step 4.

### 7. Correlate

```bash
curl -s -X POST http://localhost:8000/api/v1/incidents/<incident_id>/correlate
```
Now that seed evidence is linked, this expands from it (same-trace, then
the ±30s cross-trace window) rather than returning an empty list.

### 8. Investigate

```bash
curl -s -X POST http://localhost:8000/api/v1/incidents/<incident_id>/investigate
```
Expect `category: "hallucination"`, high confidence, and an explanation
naming the SHIPPED/DELIVERED contradiction — matching the earlier manual
ground-truth test, now proven end-to-end from a real agent run.

### 9. View it in the frontend

Paste the incident `id` into the TraceLens frontend's incident ID input
(`http://localhost:5173`) to see the header, evidence, and investigation
render for real, freshly-ingested data.

---

# Trace Library — Curated Scenario Seeding

**Final-polish addition.** Where the sections above walk through *one*
scenario manually end-to-end (useful for understanding the mechanics),
`seed_trace_library.py` ingests **10** curated, realistic scenarios in
one run and generates the manifest the frontend's Trace Library UI reads
— eliminating the manual evidence-ID copy/paste from the workflow above
for anyone using the library.

**What it is:** 9 failure scenarios (one per real taxonomy category —
`hallucination`, `tool_misuse` ×2, `prompt_injection`, `infinite_loop`,
`missing_context`, `context_overflow`, `other`) plus 1 genuinely healthy
control case, each a realistic multi-step agent execution, all ingested
through the same unmodified SDK path as `order_status_agent.py`.

**What it is not:** this is a curated demo/evaluation catalog for
exploring the investigation workflow — not automatic production incident
detection, not live customer telemetry, and not a claim that TraceLens
currently monitors real traffic. That remains explicit future scope for
a more mature version of the product.

## Run it

```bash
.venv/bin/python demo/seed_trace_library.py
```
Same prerequisites as above (backend + Postgres running). Ingests all 10
scenarios and writes two files:

- `frontend/src/data/trace-library.json` — the public manifest the
  Trace Library UI reads (titles, domains, event previews, real evidence
  IDs). Commit this file so the Trace Library has content.
- `demo/trace_library_eval.json` — a **private, eval-only** file listing
  each scenario's intended taxonomy category, for your own reference
  when checking investigation results. Nothing in the frontend reads
  this file — the expected outcome is deliberately never exposed to the
  UI or to the investigation pipeline before a real investigation runs.

## Using the Trace Library in the UI

Once seeded, open the frontend (`http://localhost:5173`) — the Trace
Library section lists all 10 scenarios. Selecting one pre-fills the
Create Incident form and attaches its known evidence, which Create
Incident then links and correlates in the same request — no manual
evidence-ID entry, and no separate Link Evidence or Correlate click.
Selecting a trace fully determines its evidence set, so those two steps
carry no user decision on this path.

The Trace Library workflow is therefore:

    Select trace → Create Incident → Investigate → Get Remediation → Resolve

Link Evidence and Correlate remain available as separate manual actions
for incidents assembled by hand from arbitrary evidence — that's the
path the curl walkthrough earlier in this file documents, and it is
unchanged.

## Important: re-run after any database reset

The evidence UUIDs written into `trace-library.json` are only valid for
the Postgres volume they were created against. If you ever run
`docker compose down -v` (or otherwise reset the database), the Trace
Library's evidence IDs go stale — re-run `seed_trace_library.py` to
regenerate both manifests before using the Trace Library again.

Creating an incident with stale evidence IDs returns a `400` naming the
missing IDs and pointing back at this script, rather than a foreign-key
error — and the incident is not created at all, so there's nothing to
clean up before re-seeding.
