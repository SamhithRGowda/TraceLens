from typing import Optional
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.incident import Incident
from app.repositories.project_repository import get_or_create_project
from app.repositories import incident_repository
from app.schemas.incident import IncidentCreate

VALID_STATUSES = {"open", "investigating", "resolved"}


def create_incident(db: Session, data: IncidentCreate) -> Incident:
    project = get_or_create_project(db, data.project_name)
    incident = incident_repository.create_incident(db, project.id, data.title, data.description)
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
