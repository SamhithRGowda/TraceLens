"""
Sprint 15 — Correlation window regression test.

Dependency-free by design (no pytest — not currently installed, and
adding a test framework is out of scope for this sprint; see Sprint 15
analysis). Plain functions + assert statements, run directly:

    .venv/bin/python backend/tests/test_correlation_regression.py

Runs against the REAL local Postgres (via SessionLocal / the same engine
the app uses — there is no in-memory/SQLite fallback in this codebase).
Creates all its own rows under a uniquely generated project/session
namespace per run, and explicitly deletes everything it created in a
`finally` block, in FK-safe order, so this never touches or collides
with real demo data (e.g. the "order-status-agent" project).

Scenario, all seeded around one reference instant t0:

    Trace A (target, seeded)   started_at = t0,      ended_at = t0
      - evidence_seed           timestamp = t0          <- manually "linked" (seed)
      - evidence_same_trace     timestamp = t0 + 5s      <- NOT linked directly;
                                                              should still be pulled
                                                              in via same-trace
                                                              expansion (case A)
    Trace B (+20s, in-window)  started_at = t0 + 20s
      - evidence_b              timestamp = t0 + 20s     <- should be included (case B)
    Trace C (+40s, Sprint 14 case) started_at = t0 + 40s
      - evidence_c              timestamp = t0 + 40s     <- should be EXCLUDED (case C)
    Trace D (+50s, clearly outside) started_at = t0 + 50s
      - evidence_d              timestamp = t0 + 50s     <- should be EXCLUDED (case D)

Window boundary check against the new 30s default: incident window is
[trace_A.started_at - 30s, trace_A.ended_at + 30s] = [t0-30s, t0+30s].
  - Trace B (t0+20s) starts inside that window -> included.
  - Trace C (t0+40s) starts after t0+30s -> excluded. This is the exact
    ~40s offset from the real Sprint 14 false positive.
  - Trace D (t0+50s) starts well after t0+30s -> excluded.
"""

from datetime import datetime, timedelta, timezone
from uuid import uuid4

from app.core.database import SessionLocal
from app.models.project import Project
from app.models.trace import Trace
from app.models.evidence import Evidence
from app.models.incident import Incident
from app.models.incident_evidence import IncidentEvidence
from app.repositories.project_repository import get_or_create_project
from app.repositories import incident_repository
from app.services.correlation_service import correlate_incident_evidence


def make_evidence(db, trace_id, timestamp, evidence_type="llm_call"):
    evidence = Evidence(
        trace_id=trace_id,
        evidence_type=evidence_type,
        payload={"note": "sprint-15 regression test evidence"},
        timestamp=timestamp,
    )
    db.add(evidence)
    db.flush()
    return evidence


def make_trace(db, project_id, session_id, started_at, ended_at=None):
    trace = Trace(
        project_id=project_id,
        session_id=session_id,
        started_at=started_at,
        ended_at=ended_at or started_at,
    )
    db.add(trace)
    db.flush()
    return trace


def run():
    db = SessionLocal()

    # Unique per run so repeated runs never collide with each other or
    # with real data — nothing here reuses a fixed name.
    run_id = uuid4().hex[:8]
    project_name = f"sprint15-correlation-test-{run_id}"

    project = None
    incident = None

    try:
        # --- Seed data -----------------------------------------------
        project = get_or_create_project(db, project_name)

        t0 = datetime.now(timezone.utc)

        trace_a = make_trace(db, project.id, f"session-a-{run_id}", started_at=t0)
        trace_b = make_trace(db, project.id, f"session-b-{run_id}", started_at=t0 + timedelta(seconds=20))
        trace_c = make_trace(db, project.id, f"session-c-{run_id}", started_at=t0 + timedelta(seconds=40))
        trace_d = make_trace(db, project.id, f"session-d-{run_id}", started_at=t0 + timedelta(seconds=50))

        evidence_seed = make_evidence(db, trace_a.id, t0)
        evidence_same_trace = make_evidence(db, trace_a.id, t0 + timedelta(seconds=5))
        evidence_b = make_evidence(db, trace_b.id, t0 + timedelta(seconds=20))
        evidence_c = make_evidence(db, trace_c.id, t0 + timedelta(seconds=40))
        evidence_d = make_evidence(db, trace_d.id, t0 + timedelta(seconds=50))

        db.commit()

        incident = incident_repository.create_incident(
            db, project.id, "Sprint 15 regression test incident", "created by test_correlation_regression.py"
        )
        db.commit()

        # Seed with only evidence_seed — mirrors the real workflow
        # (manual link, then correlate).
        incident_repository.link_evidence(db, incident.id, [evidence_seed.id], linked_by="manual")
        db.commit()

        # --- Run correlation under test (uses the new 30s default) ---
        result = correlate_incident_evidence(db, incident.id)
        assert result is not None, "correlate_incident_evidence returned None for a valid incident"

        db.refresh(incident)
        linked_ids = {e.id for e in incident.evidence}

        # --- Case A: same-trace evidence remains included -------------
        assert evidence_same_trace.id in linked_ids, (
            "FAIL (case A): evidence on the seed trace itself "
            f"({evidence_same_trace.id}) was not pulled in by same-trace expansion."
        )
        print("PASS (case A): same-trace evidence included.")

        # --- Case B: +20s candidate trace included ---------------------
        assert evidence_b.id in linked_ids, (
            f"FAIL (case B): evidence at +20s ({evidence_b.id}) should be inside "
            "the +/-30s window but was excluded."
        )
        print("PASS (case B): +20s candidate trace evidence included.")

        # --- Case C: ~40s candidate trace excluded (the real Sprint 14 case) --
        assert evidence_c.id not in linked_ids, (
            f"FAIL (case C): evidence at +40s ({evidence_c.id}) should be outside "
            "the +/-30s window (this is the exact Sprint 14 false-positive offset) "
            "but was included."
        )
        print("PASS (case C): ~40s candidate trace evidence excluded.")

        # --- Case D: +50s candidate trace excluded ----------------------
        assert evidence_d.id not in linked_ids, (
            f"FAIL (case D): evidence at +50s ({evidence_d.id}) should be clearly "
            "outside the +/-30s window but was included."
        )
        print("PASS (case D): +50s candidate trace evidence excluded.")

        print("\nAll 4 regression cases passed.")

    finally:
        # Explicit cleanup, FK-safe order, runs even if an assertion
        # above failed. Nothing here should ever touch real demo data —
        # every row created above lives under the unique project_name.
        try:
            if incident is not None:
                db.query(IncidentEvidence).filter(IncidentEvidence.incident_id == incident.id).delete()
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


if __name__ == "__main__":
    run()
