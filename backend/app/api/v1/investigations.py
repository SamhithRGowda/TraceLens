from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.repositories import remediation_repository
from app.schemas.remediation import RemediationResponse
from app.services import remediation_service

router = APIRouter(prefix="/investigations", tags=["investigations"])


@router.post("/{investigation_id}/remediate", response_model=RemediationResponse, status_code=201)
def remediate_investigation(investigation_id: UUID, db: Session = Depends(get_db)):
    """
    Generates a fresh advisory remediation recommendation for this
    investigation. Advisory only — no code is written or applied.
    Safe to call more than once; each call creates a new, immutable
    Remediation, never overwrites a previous one.
    """
    remediation = remediation_service.run_remediation(db, investigation_id)
    if remediation is None:
        raise HTTPException(status_code=404, detail="Investigation not found")
    return remediation


@router.get("/{investigation_id}/remediations", response_model=list[RemediationResponse])
def list_remediations(investigation_id: UUID, db: Session = Depends(get_db)):
    """Full remediation history for this investigation, newest first."""
    return remediation_repository.get_remediations_for_investigation(db, investigation_id)
