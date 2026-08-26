# TraceLens

**AI Incident Intelligence for Agentic Systems**

TraceLens turns agent execution traces into structured incident investigations. It helps developers move from:

**Trace → Incident → Evidence → Diagnosis → Remediation → Resolution**

AI agents can fail in ways that are difficult to debug — hallucinations, tool misuse, prompt injection, missing context, infinite loops, and context failures. The evidence for what went wrong is usually scattered across LLM calls, tool calls, and timestamps. TraceLens provides a workflow for collecting the relevant evidence around an incident and investigating what actually happened.

This is a focused working prototype, not a production observability platform. See [Current Limitations](#current-limitations) for what that means in practice.

---

## Table of Contents

- [Workflow](#workflow)
- [Architecture](#architecture)
- [Tech Stack](#tech-stack)
- [Investigation Details](#investigation-details)
- [Engineering Highlights](#engineering-highlights)
- [Failure Modes](#failure-modes)
- [Evaluation](#evaluation)
- [Project Structure](#project-structure)
- [Running Locally](#running-locally)
- [Demo Flow](#demo-flow)
- [Current Limitations](#current-limitations)

---

## Workflow

1. Select a trace
2. Create an incident
3. Link and correlate relevant evidence
4. Build an ordered evidence bundle
5. Detect certain structural failure signals deterministically
6. Use an LLM for semantic diagnosis
7. Validate the investigation output before persistence
8. Generate advisory remediation
9. Manually resolve the incident

---

## Architecture

```
                Agent Execution Traces
                         │
                         ▼
                ┌─────────────────┐
                │   Trace Library │
                └────────┬────────┘
                         │
                         ▼
                ┌─────────────────┐
                │ Incident Service│
                │                 │
                │ Link + Correlate│
                └────────┬────────┘
                         │
                         ▼
                ┌─────────────────┐
                │ Evidence Bundle │
                │  chronological  │
                │     ordering    │
                └────────┬────────┘
                         │
                         ▼
          ┌───────────────────────────┐
          │    Investigation Engine   │
          │                           │
          │  Deterministic Signals    │
          │            +              │
          │       LLM Diagnosis       │
          └─────────────┬─────────────┘
                        │
                        ▼
               ┌──────────────────┐
               │   Investigation  │
               │ + Evidence       │
               │   Citations      │
               └────────┬─────────┘
                        │
                        ▼
               ┌──────────────────┐
               │    Remediation   │
               │     Advisory     │
               └────────┬─────────┘
                        │
                        ▼
               ┌──────────────────┐
               │     Resolve      │
               └──────────────────┘
```

PostgreSQL is the persistence layer throughout — incidents, evidence, investigations, and the relationships between them (including which evidence was manually linked vs. discovered through correlation) are all stored relationally.

---

## Tech Stack

**Frontend:** React, TypeScript, Vite
**Backend:** Python, FastAPI, SQLAlchemy
**Database:** PostgreSQL
**AI:** OpenAI API
**Infrastructure:** Docker / Docker Compose

---

## Investigation Details

### Trace Selection

The Trace Library contains curated agent executions representing different failure scenarios. Traces contain events such as LLM calls, tool calls, timestamps, outputs, and execution metadata.

### Incident Creation

Selecting a trace provides the evidence associated with that execution. Incident creation links the selected evidence and performs correlation on the backend. Evidence relationships preserve provenance, so manually selected evidence can be distinguished from evidence discovered through correlation.

### Evidence Bundle

The investigation engine builds an evidence bundle from linked incident evidence. Evidence is ordered chronologically before being provided to the investigation layer, so sequence-dependent failures can be reasoned about using actual execution order rather than incidental database ordering.

### Deterministic Signals

TraceLens contains a deterministic evidence-signal layer. The current implementation can identify structural patterns including:

- context truncation / context-length failures
- repeated identical tool calls associated with loops
- missing-context signals from failed retrieval followed by an unsupported response

Where appropriate, an authoritative deterministic signal can constrain the investigation category before the LLM diagnosis is persisted, rather than leaving a structurally obvious failure entirely up to semantic classification.

### LLM Diagnosis

The LLM handles semantic investigation. The investigation produces a failure category, a confidence score, a plain-language explanation, and cited evidence.

Investigation output is validated before persistence:

- category is constrained to the supported taxonomy
- confidence is constrained to a valid range
- cited evidence IDs must be valid and belong to the incident
- duplicate citations are removed

### Remediation

TraceLens can generate advisory remediation based on the investigation and its cited evidence. Remediation is advisory only — TraceLens does not automatically modify the underlying agent or production system.

### Resolution

Incidents can be manually resolved after investigation and remediation.

---

## Engineering Highlights

**Deterministic + LLM hybrid investigation.** Some failure signatures are structural facts about the evidence, not semantic judgments — three identical tool calls in a row, an explicit context-length error. Those are detected in code and can act as an authoritative signal, rather than leaving every classification decision to the LLM.

**Evidence provenance.** Every incident-evidence relationship records whether that evidence was linked manually or discovered through correlation, so the evidence set is auditable rather than an opaque list.

**LLM output validation.** The model's category, confidence, and cited evidence IDs are checked before anything is persisted — off-taxonomy categories fall back to a known value, confidence is clamped to a valid range, and citations must reference evidence that's actually linked to the incident.

**Chronological evidence ordering.** Evidence is explicitly sorted by timestamp before being passed to the investigation layer, since several failure categories depend on sequence (a later response contradicting an earlier tool result, a call repeating without state change).

**Transactional incident creation.** When an incident is created from a selected trace, linking the seed evidence and running correlation happen in the same transaction as creating the incident itself. Either the incident exists fully assembled, or it doesn't exist at all.

**Failure-safe frontend workflow.** Investigation and remediation actions are explicit, user-triggered steps. A failed action surfaces an error without discarding or blanking the rest of the incident view.

---

## Failure Modes

The Trace Library covers scenarios involving:

- hallucination
- tool misuse
- prompt injection
- infinite loops
- missing context
- context overflow
- other / healthy control cases

These categories are not always cleanly separable. Several of them describe overlapping failure shapes — for example, a response that contradicts a tool's output can reasonably read as either a hallucination or a form of tool misuse, depending on how the ambiguity is resolved. This overlap is a real property of the taxonomy, not a bug, and it directly affects the evaluation results below.

---

## Evaluation

TraceLens includes a small, curated development evaluation: nine hand-built scenarios, each targeting one taxonomy category, run through the full investigation pipeline.

**Result: 4/9 (44.4%) matched the intended category.**

| Scenario                      | Expected         | Actual           | Result |
| ----------------------------- | ---------------- | ---------------- | ------ |
| order-status-contradiction    | hallucination    | tool_misuse      | FAIL   |
| account-context-mixup         | hallucination    | tool_misuse      | FAIL   |
| wrong-tool-refund             | tool_misuse      | other            | FAIL   |
| kb-prompt-injection           | prompt_injection | prompt_injection | PASS   |
| payment-retry-loop            | infinite_loop    | infinite_loop    | PASS   |
| missing-claim-context         | missing_context  | missing_context  | PASS   |
| context-overflow-truncation   | context_overflow | context_overflow | PASS   |
| stale-pricing-doc             | tool_misuse      | hallucination    | FAIL   |
| unauthorized-financial-advice | other            | tool_misuse      | FAIL   |

The deterministic signal layer fired correctly in every case it was designed to cover, with zero false positives:

- `context-overflow-truncation` → authoritative `context_overflow` → PASS
- `payment-retry-loop` → authoritative `infinite_loop` → PASS
- `missing-claim-context` → `missing_context` premise → PASS

A separate healthy control scenario (a routine password-reset execution with no failure) returned `other` and was left unscored, since it isn't a member of the failure taxonomy being evaluated.

**This is a small curated development evaluation, not a production accuracy benchmark.** Nine scenarios is not a statistically meaningful sample, and the scenarios were authored specifically to stress-test the taxonomy rather than sampled from real traffic. The failures above are concentrated in exactly the categories the taxonomy overlap section describes: `hallucination` vs. `tool_misuse`, and cases involving `other` as a catch-all. These are primarily LLM semantic-classification errors on genuinely ambiguous category boundaries, not signal-layer failures — the deterministic layer is the one part of the pipeline that scored cleanly across the board.

---

## Project Structure

```
TraceLens/
├── backend/
│   ├── app/
│   │   ├── api/
│   │   ├── integrations/
│   │   ├── models/
│   │   ├── repositories/
│   │   ├── schemas/
│   │   └── services/
│   └── tests/
│
├── frontend/
│   └── src/
│       ├── components/
│       ├── pages/
│       ├── services/
│       └── types/
│
└── demo/
    ├── trace_library.json
    ├── trace_library_eval.json
    └── eval_trace_library.py
```

- `backend/app/services` — incident creation, correlation, and investigation orchestration
- `backend/app/integrations` — LLM prompt construction and the OpenAI client
- `backend/app/repositories` — persistence access
- `frontend/src/pages` — the incident workflow UI
- `demo/` — the curated Trace Library and its evaluation harness

---

## Running Locally

```bash
docker compose up --build
```

The application runs entirely through Docker Compose (backend, frontend, and PostgreSQL). Once running, the Trace Library can be used to walk through the full investigation workflow — from selecting a curated trace to resolving the resulting incident — without needing external agent traffic.

---

## Demo Flow

```
Select Trace
     ↓
Create Incident
     ↓
Review Evidence
     ↓
Investigate
     ↓
Review Diagnosis
     ↓
Get Remediation
     ↓
Resolve
```

---

## Current Limitations

- Uses curated trace data rather than live production ingestion
- Semantic classification is LLM-dependent and inherits its variability
- Overlapping failure-mode definitions can make classification genuinely ambiguous, as the evaluation results show
- No authentication or multi-tenant deployment layer
- Remediation is advisory only and does not automatically execute changes against the underlying agent or system
- Evaluation currently covers a small, curated scenario set rather than production-scale data
