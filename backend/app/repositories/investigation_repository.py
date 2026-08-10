from typing import Optional
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.investigation import Investigation


def create_investigation(
    db: Session,
    incident_id: UUID,
    category: str,
    confidence: float,
    explanation: str,
    cited_evidence_ids: list,
    taxonomy_version: int,
    model: str,
) -> Investigation:
    investigation = Investigation(
        incident_id=incident_id,
        category=category,
        confidence=confidence,
        explanation=explanation,
        cited_evidence_ids=cited_evidence_ids,
        taxonomy_version=taxonomy_version,
        model=model,
    )
    db.add(investigation)
    db.flush()
    return investigation


def get_investigations_for_incident(db: Session, incident_id: UUID) -> list[Investigation]:
    """All investigations for an incident, newest first."""
    return (
        db.query(Investigation)
        .filter(Investigation.incident_id == incident_id)
        .order_by(Investigation.created_at.desc())
        .all()
    )


def get_latest_investigation(db: Session, incident_id: UUID) -> Optional[Investigation]:
    return (
        db.query(Investigation)
        .filter(Investigation.incident_id == incident_id)
        .order_by(Investigation.created_at.desc())
        .first()
    )
