"""
Investigation-output validation tests.

Covers the validation gate added to investigation_service: the LLM's
response is no longer trusted straight into the Investigation row.

Dependency-free by design, same as test_correlation_regression.py (no
pytest installed; adding a test framework is still out of scope). Plain
functions + assert statements, run directly. Backend dependencies live in
the container, not .venv:

    docker compose exec -T backend python - < backend/tests/test_investigation_validation.py

Two parts:

  Part 1 — pure helpers (_validated_category / _validated_confidence /
  _validated_cited_ids). No DB, no LLM, no network.

  Part 2 — one end-to-end pass through run_investigation with
  call_llm_json stubbed out (so no OpenAI request is made and nothing is
  billed), asserting that a deliberately poisoned response is sanitised
  before it's persisted, and that the evidence bundle handed to the model
  is in chronological order.

Part 2 runs against the REAL local Postgres (SessionLocal — there is no
in-memory fallback in this codebase), creates all its own rows under a
uniquely generated project namespace, and deletes everything it created
in a `finally` block in FK-safe order.
"""

from datetime import datetime, timedelta, timezone
from uuid import uuid4

from app.core.database import SessionLocal
from app.models.project import Project
from app.models.trace import Trace
from app.models.evidence import Evidence
from app.models.incident import Incident
from app.models.incident_evidence import IncidentEvidence
from app.models.investigation import Investigation
from app.repositories.project_repository import get_or_create_project
from app.repositories import incident_repository
from app.integrations.llm.prompts import TAXONOMY
from app.services import investigation_service
from app.services.investigation_service import (
    _validated_category,
    _validated_cited_ids,
    _validated_confidence,
)


# ---------------------------------------------------------------------
# Part 1: pure validation helpers
# ---------------------------------------------------------------------

def test_category_validation():
    # Every real taxonomy name must survive untouched — the gate must not
    # quietly narrow the taxonomy it's defending.
    for entry in TAXONOMY:
        name = entry["name"]
        assert _validated_category(name) == name, (
            f"FAIL: valid taxonomy category {name!r} was not preserved."
        )
    print(f"PASS (category): all {len(TAXONOMY)} taxonomy names preserved.")

    # Off-taxonomy strings and non-strings both fall back to "other".
    for bad in ["rate_limit", "Hallucination", "HALLUCINATION", "", "  ", None, 3, ["hallucination"]]:
        assert _validated_category(bad) == "other", (
            f"FAIL: invalid category {bad!r} did not fall back to 'other'."
        )
    print("PASS (category): off-taxonomy and non-string values fall back to 'other'.")


def test_confidence_validation():
    # In-range values pass through unchanged, including the boundaries.
    for good in [0.0, 0.5, 0.87, 1.0]:
        assert _validated_confidence(good) == good, (
            f"FAIL: in-range confidence {good!r} was altered."
        )
    # ints in range are valid numerics, coerced to float.
    assert _validated_confidence(1) == 1.0
    assert _validated_confidence(0) == 0.0
    print("PASS (confidence): in-range values preserved.")

    # Out of range clamps to the nearest bound rather than persisting a
    # value the UI's percentage/bar can't render honestly.
    assert _validated_confidence(1.4) == 1.0, "FAIL: 1.4 did not clamp to 1.0."
    assert _validated_confidence(95) == 1.0, "FAIL: 95 (percent-style) did not clamp to 1.0."
    assert _validated_confidence(-0.2) == 0.0, "FAIL: -0.2 did not clamp to 0.0."
    print("PASS (confidence): out-of-range values clamped into [0, 1].")

    # Non-numeric / non-finite can't be clamped into anything meaningful,
    # so they become 0.0 instead of breaking the column's float contract.
    # True is checked explicitly: bool is an int subclass, so an unguarded
    # clamp would turn it into a confident 1.0.
    for bad in ["0.9", "high", None, {}, [], float("nan"), float("inf"), float("-inf"), True, False]:
        result = _validated_confidence(bad)
        assert result == 0.0, f"FAIL: non-numeric confidence {bad!r} became {result!r}, expected 0.0."
    print("PASS (confidence): non-numeric and non-finite values become 0.0.")


def test_cited_ids_validation():
    linked_a, linked_b = uuid4(), uuid4()
    not_linked = uuid4()
    linked = {linked_a, linked_b}

    # Linked ids are kept, in the order cited, as strings (JSONB column).
    kept = _validated_cited_ids([str(linked_b), str(linked_a)], linked)
    assert kept == [str(linked_b), str(linked_a)], f"FAIL: citation order not preserved: {kept}"
    print("PASS (cited ids): linked ids kept in cited order.")

    # An id that exists but isn't linked to *this* incident is dropped —
    # this is the case that makes "evidence-backed" enforceable.
    kept = _validated_cited_ids([str(linked_a), str(not_linked)], linked)
    assert kept == [str(linked_a)], f"FAIL: unlinked id was not dropped: {kept}"
    print("PASS (cited ids): id not linked to this incident dropped.")

    # Anything that isn't a parseable UUID is dropped, not stored — a
    # non-UUID string used to commit fine and then 500 every subsequent
    # GET /incidents/{id}/investigations.
    kept = _validated_cited_ids(
        ["evidence-1", "", None, 42, {}, "not-a-uuid", str(linked_a)], linked
    )
    assert kept == [str(linked_a)], f"FAIL: unparseable ids were not dropped: {kept}"
    print("PASS (cited ids): unparseable ids dropped.")

    # Duplicates collapse; a repeated citation isn't extra evidence.
    kept = _validated_cited_ids([str(linked_a), str(linked_a), str(linked_b)], linked)
    assert kept == [str(linked_a), str(linked_b)], f"FAIL: duplicates not collapsed: {kept}"
    print("PASS (cited ids): duplicate citations collapsed.")

    # Wrong shape entirely, and the all-invented case, both yield [].
    assert _validated_cited_ids("not a list", linked) == []
    assert _validated_cited_ids(None, linked) == []
    assert _validated_cited_ids([str(not_linked)], linked) == []
    print("PASS (cited ids): non-list input and all-invented citations yield [].")


# ---------------------------------------------------------------------
# Part 2: run_investigation end-to-end, with the LLM stubbed
# ---------------------------------------------------------------------

def make_evidence(db, trace_id, timestamp, note):
    evidence = Evidence(
        trace_id=trace_id,
        evidence_type="llm_call",
        payload={"note": note},
        timestamp=timestamp,
    )
    db.add(evidence)
    db.flush()
    return evidence


def test_run_investigation_sanitises_and_orders():
    db = SessionLocal()

    run_id = uuid4().hex[:8]
    project_name = f"investigation-validation-test-{run_id}"

    project = None
    incident = None
    real_call_llm_json = investigation_service.call_llm_json
    captured = {}

    try:
        # --- Seed data ------------------------------------------------
        project = get_or_create_project(db, project_name)
        t0 = datetime.now(timezone.utc)

        trace = Trace(
            project_id=project.id,
            session_id=f"session-{run_id}",
            started_at=t0,
            ended_at=t0 + timedelta(seconds=10),
        )
        db.add(trace)
        db.flush()

        # Inserted out of chronological order on purpose: the linking
        # relationship has no ORDER BY, so if the service didn't sort,
        # the bundle would reach the model in roughly this order.
        e_last = make_evidence(db, trace.id, t0 + timedelta(seconds=10), "third step")
        e_first = make_evidence(db, trace.id, t0, "first step")
        e_middle = make_evidence(db, trace.id, t0 + timedelta(seconds=5), "second step")

        # Linked to a *different* incident's trace, never to ours — stands
        # in for an id the model could plausibly invent.
        unlinked = make_evidence(db, trace.id, t0 + timedelta(seconds=3), "never linked")

        db.commit()

        incident = incident_repository.create_incident(
            db, project.id, "Validation gate test incident", "created by test_investigation_validation.py"
        )
        db.commit()

        incident_repository.link_evidence(
            db, incident.id, [e_last.id, e_first.id, e_middle.id], linked_by="manual"
        )
        db.commit()

        # --- Stub the LLM with a deliberately poisoned response -------
        # No OpenAI request is made. Every field is invalid in a different
        # way, so one run exercises all three validators at once.
        def fake_call_llm_json(system_prompt, user_prompt, model=None):
            captured["user_prompt"] = user_prompt
            return {
                "category": "rate_limit_exceeded",  # off-taxonomy
                "confidence": 95,                   # percent-style, out of [0, 1]
                "explanation": "Stubbed explanation for the validation test.",
                "cited_evidence_ids": [
                    str(e_first.id),      # valid
                    str(unlinked.id),     # exists, not linked to this incident
                    str(uuid4()),         # invented outright
                    "evidence-1",         # not a UUID at all
                    str(e_first.id),      # duplicate
                ],
            }

        investigation_service.call_llm_json = fake_call_llm_json

        investigation = investigation_service.run_investigation(db, incident.id)
        assert investigation is not None, "FAIL: run_investigation returned None for a valid incident."

        # --- Ordering: bundle reaches the model chronologically -------
        prompt = captured["user_prompt"]
        positions = [prompt.find(str(e.id)) for e in (e_first, e_middle, e_last)]
        assert all(p >= 0 for p in positions), (
            f"FAIL: not all linked evidence ids appeared in the prompt: {positions}"
        )
        assert positions == sorted(positions), (
            "FAIL: evidence bundle was not sorted chronologically before being sent "
            f"to the model (prompt positions: {positions})."
        )
        print("PASS (ordering): evidence bundle sent to the model in timestamp order.")

        # --- Persisted row is sanitised -------------------------------
        db.refresh(investigation)

        assert investigation.category == "other", (
            f"FAIL: off-taxonomy category persisted as {investigation.category!r}."
        )
        print("PASS (persisted): off-taxonomy category stored as 'other'.")

        assert investigation.confidence == 1.0, (
            f"FAIL: confidence 95 persisted as {investigation.confidence!r}, expected 1.0."
        )
        print("PASS (persisted): out-of-range confidence clamped to 1.0.")

        assert investigation.cited_evidence_ids == [str(e_first.id)], (
            "FAIL: cited_evidence_ids was not reduced to linked evidence only: "
            f"{investigation.cited_evidence_ids}"
        )
        print("PASS (persisted): only linked, parseable, deduped citations stored.")

        # --- Existing behaviour still intact --------------------------
        db.refresh(incident)
        assert incident.status == "investigating", (
            f"FAIL: the open -> investigating nudge regressed (status={incident.status!r})."
        )
        print("PASS (unchanged): open -> investigating status nudge still applies.")

        print("\nAll validation-gate cases passed.")

    finally:
        investigation_service.call_llm_json = real_call_llm_json

        # Explicit cleanup, FK-safe order, runs even if an assertion above
        # failed. Every row created here lives under the unique
        # project_name, so real demo data is never touched.
        try:
            if incident is not None:
                db.query(IncidentEvidence).filter(IncidentEvidence.incident_id == incident.id).delete()
                db.query(Investigation).filter(Investigation.incident_id == incident.id).delete()
            if project is not None:
                trace_ids_subq = db.query(Trace.id).filter(Trace.project_id == project.id).subquery()
                db.query(Evidence).filter(Evidence.trace_id.in_(trace_ids_subq)).delete(synchronize_session=False)
            if incident is not None:
                db.query(Incident).filter(Incident.id == incident.id).delete()
            if project is not None:
                db.query(Trace).filter(Trace.project_id == project.id).delete()
                db.query(Project).filter(Project.id == project.id).delete()
            db.commit()
        except Exception as cleanup_exc:
            db.rollback()
            print(f"WARNING: cleanup failed, test data may remain (project_name={project_name}): {cleanup_exc}")
            raise
        finally:
            db.close()


def run():
    test_category_validation()
    test_confidence_validation()
    test_cited_ids_validation()
    test_run_investigation_sanitises_and_orders()


if __name__ == "__main__":
    run()
