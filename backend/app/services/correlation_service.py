from datetime import timedelta
from typing import Optional
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.incident import Incident
from app.repositories import incident_repository, trace_repository, evidence_repository

DEFAULT_TIME_WINDOW_SECONDS = 60


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
