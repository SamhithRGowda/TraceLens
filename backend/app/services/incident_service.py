from typing import Optional
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.incident import Incident
from app.repositories.project_repository import get_or_create_project
from app.repositories import incident_repository
from app.schemas.incident import IncidentCreate


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
