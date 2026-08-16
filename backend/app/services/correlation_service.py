from datetime import timedelta
from typing import Optional
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.incident import Incident
from app.repositories import incident_repository, trace_repository, evidence_repository

# --- Sprint 15: window tightened from 60s to 30s -------------------------
# Original value (Day 7) was an unvalidated round-number placeholder — no
# multi-agent latency data existed to derive it from (see Sprint 15
# analysis). It was kept as a documented V1 limitation until Sprint 14's
# live-agent run produced a concrete, reproducible false positive: an
# unrelated trace ~40 seconds away from the target trace was pulled into
# the same incident by the 60s window, despite having nothing to do with
# it (verified incident d7324cad-f3d4-433a-b2f5-83167bdac2b6, contaminating
# trace 71c3729a-7bc4-4a5d-ac5a-80032d6f9111).
#
# 30 seconds is chosen specifically to exclude that ~40s case, NOT because
# it reflects any measured multi-agent handoff latency — no such data
# exists yet. It remains a bounded MVP heuristic, not a considered
# definition of "related traces."
#
# This is a probability reduction, not a structural fix: two unrelated
# traces in the same project landing within 30s of each other will still
# be merged. The only signal correlation uses is (project_id, time
# proximity) — there is no session/request/parent identity concept in the
# schema to distinguish "these two sessions are part of one logical flow"
# from "these two sessions just happened to run close together." A
# caller-asserted relationship field (e.g. a parent/request session id)
# would be the real fix, but requires SDK + schema changes and was
# explicitly deferred out of this sprint's scope — there's no real
# multi-agent usage yet to design that mechanism against. Revisit this
# constant, and that deferred mechanism, once real multi-agent trace data
# exists.
DEFAULT_TIME_WINDOW_SECONDS = 30


def correlate_incident_evidence(
    db: Session, incident_id: UUID, time_window_seconds: int = DEFAULT_TIME_WINDOW_SECONDS
) -> Optional[Incident]:
    """
    Expands an incident's evidence outward from whatever's already
    manually linked (Day 6), using the traces those evidence rows
    belong to as a starting point:

      - The seed traces themselves are included directly, which
        covers "pull in the rest of this trace's evidence" — no
        separate step needed, it falls out of the set naturally.
      - From each seed trace's time range, we search outward
        (+/- time_window_seconds) for OTHER traces in the same
        project that overlap it in time — this is what catches
        multi-agent scenarios where the relevant evidence sits in
        a different trace entirely.

    Idempotent: already-linked evidence is skipped (see
    incident_repository.link_evidence), so calling this more than
    once is safe and won't duplicate or relabel existing manual links.
    """
    incident = incident_repository.get_incident(db, incident_id)
    if incident is None:
        return None

    seed_evidence = incident.evidence
    seed_trace_ids = {e.trace_id for e in seed_evidence}

    if not seed_trace_ids:
        # Nothing manually linked yet — there's nothing to expand from.
        return incident

    seed_traces = trace_repository.get_traces_by_ids(db, seed_trace_ids)

    relevant_trace_ids = set(seed_trace_ids)
    for trace in seed_traces:
        window_start = trace.started_at - timedelta(seconds=time_window_seconds)
        window_end = (trace.ended_at or trace.started_at) + timedelta(seconds=time_window_seconds)
        nearby = trace_repository.get_traces_in_time_window(db, incident.project_id, window_start, window_end)
        relevant_trace_ids.update(t.id for t in nearby)

    candidate_evidence = evidence_repository.get_evidence_by_trace_ids(db, relevant_trace_ids)
    evidence_ids = [e.id for e in candidate_evidence]

    incident_repository.link_evidence(db, incident_id, evidence_ids, linked_by="correlation")
    db.commit()
    db.refresh(incident)
    return incident
