from typing import Optional
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.remediation import Remediation


def create_remediation(
    db: Session,
    investigation_id: UUID,
    recommended_fix: str,
    rationale: str,
    model: str,
) -> Remediation:
    remediation = Remediation(
        investigation_id=investigation_id,
        recommended_fix=recommended_fix,
        rationale=rationale,
        model=model,
    )
    db.add(remediation)
    db.flush()
    return remediation


def get_remediations_for_investigation(db: Session, investigation_id: UUID) -> list[Remediation]:
    """All remediations for an investigation, newest first."""
    return (
        db.query(Remediation)
        .filter(Remediation.investigation_id == investigation_id)
        .order_by(Remediation.created_at.desc())
        .all()
    )
