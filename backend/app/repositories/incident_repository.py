from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.incident import Incident
from app.models.incident_evidence import IncidentEvidence


def create_incident(db: Session, project_id: UUID, title: str, description: Optional[str]) -> Incident:
    incident = Incident(project_id=project_id, title=title, description=description)
    db.add(incident)
    db.flush()
    return incident


def get_incident(db: Session, incident_id: UUID) -> Optional[Incident]:
    return db.query(Incident).filter(Incident.id == incident_id).first()


def link_evidence(db: Session, incident_id: UUID, evidence_ids: list[UUID], linked_by: str = "manual") -> None:
    """
    Links each evidence_id to the incident. Skips any that are already
    linked (the UniqueConstraint would reject a duplicate insert
    outright) rather than erroring on a re-submitted request.
    """
    existing = {
        row.evidence_id
        for row in db.query(IncidentEvidence.evidence_id).filter(IncidentEvidence.incident_id == incident_id)
    }
    for evidence_id in evidence_ids:
        if evidence_id in existing:
            continue
        db.add(IncidentEvidence(incident_id=incident_id, evidence_id=evidence_id, linked_by=linked_by))
    db.flush()


def set_status(db: Session, incident: Incident, new_status: str) -> Incident:
    """
    Raw mutation, no validation — that's the service layer's job
    (incident_service.set_incident_status does the checking, and
    investigation_service's auto-transition calls this directly since
    it's an internal side effect, not a user-submitted transition
    that needs rejecting).

    resolved_at is set when moving to "resolved", and cleared
    otherwise — it always reflects the current/most-recent
    resolution, never a stale one from an earlier resolve-reopen cycle.
    """
    incident.status = new_status
    incident.resolved_at = datetime.now(timezone.utc) if new_status == "resolved" else None
    db.add(incident)
    db.flush()
    return incident
