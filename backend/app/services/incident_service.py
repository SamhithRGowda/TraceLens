from typing import Optional
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.incident import Incident
from app.repositories.project_repository import get_or_create_project
from app.repositories import incident_repository, evidence_repository
from app.schemas.incident import IncidentCreate
from app.services import correlation_service

VALID_STATUSES = {"open", "investigating", "resolved"}


def create_incident(db: Session, data: IncidentCreate) -> Incident:
    """
    Creates the incident and, when `evidence_ids` are supplied, assembles
    it in the same transaction: links that evidence as the manual seed,
    then correlates outward from it. This is what makes "select a trace ->
    create an incident" a single action — the evidence set for a selected
    trace is fully determined by the selection, so linking and correlating
    it are mechanical consequences, not decisions a user makes.

    Omitting `evidence_ids` preserves the original behavior exactly: a
    bare incident, with linking and correlation left to their own
    endpoints (still the path for incidents assembled by hand from
    arbitrary evidence).

    One commit for all of it. A failure at any step leaves no
    half-assembled incident behind — either the incident exists with its
    evidence linked and correlated, or it doesn't exist at all.

    Raises ValueError if any supplied evidence_id doesn't exist, rather
    than letting it surface as an opaque foreign-key IntegrityError. The
    likely cause is a Trace Library manifest that's stale for this
    database, so the message says so.
    """
    project = get_or_create_project(db, data.project_name)
    incident = incident_repository.create_incident(db, project.id, data.title, data.description)

    if data.evidence_ids:
        seed_evidence = evidence_repository.get_evidence_by_ids(db, data.evidence_ids)
        requested = set(data.evidence_ids)

        if len(seed_evidence) != len(requested):
            found = {e.id for e in seed_evidence}
            missing = sorted(str(eid) for eid in requested - found)
            db.rollback()
            raise ValueError(
                f"{len(missing)} of {len(requested)} evidence ids do not exist: "
                f"{', '.join(missing)}. If these came from the Trace Library, its "
                "manifest is stale for this database — re-run "
                "demo/seed_trace_library.py to regenerate it."
            )

        incident_repository.link_evidence(db, incident.id, data.evidence_ids, linked_by="manual")
        correlation_service.expand_from_seed(db, incident, seed_evidence)

    db.commit()
    db.refresh(incident)
    return incident


def link_evidence_to_incident(db: Session, incident_id: UUID, evidence_ids: list[UUID]) -> Optional[Incident]:
    incident = incident_repository.get_incident(db, incident_id)
    if incident is None:
        return None

    incident_repository.link_evidence(db, incident_id, evidence_ids, linked_by="manual")
    db.commit()
    db.refresh(incident)
    return incident


def set_incident_status(db: Session, incident_id: UUID, new_status: str) -> Optional[Incident]:
    """
    Validates and applies a status change. Deliberately simple
    validation, not a state machine: reject unknown status values,
    and reject a no-op (setting to the status it's already at) since
    that's almost always a mistake worth surfacing rather than
    silently accepting. All 3 real transitions between open/
    investigating/resolved are otherwise allowed in either direction
    (e.g. reopening a resolved incident is a legitimate real case).
    """
    incident = incident_repository.get_incident(db, incident_id)
    if incident is None:
        return None

    if new_status not in VALID_STATUSES:
        raise ValueError(f"'{new_status}' is not a valid status.")
    if new_status == incident.status:
        raise ValueError(f"Incident is already '{incident.status}'.")

    incident_repository.set_status(db, incident, new_status)
    db.commit()
    db.refresh(incident)
    return incident
