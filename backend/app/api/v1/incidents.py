from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.repositories import incident_repository, investigation_repository
from app.schemas.incident import IncidentCreate, IncidentResponse, EvidenceLinkRequest, IncidentWithEvidenceResponse
from app.schemas.investigation import InvestigationResponse
from app.services import incident_service, correlation_service, investigation_service

router = APIRouter(prefix="/incidents", tags=["incidents"])


@router.post("", response_model=IncidentResponse, status_code=201)
def create_incident(data: IncidentCreate, db: Session = Depends(get_db)):
    return incident_service.create_incident(db, data)


@router.get("/{incident_id}", response_model=IncidentWithEvidenceResponse)
def get_incident(incident_id: UUID, db: Session = Depends(get_db)):
    incident = incident_repository.get_incident(db, incident_id)
    if incident is None:
        raise HTTPException(status_code=404, detail="Incident not found")
    return incident


@router.post("/{incident_id}/evidence", response_model=IncidentWithEvidenceResponse)
def link_evidence(incident_id: UUID, data: EvidenceLinkRequest, db: Session = Depends(get_db)):
    incident = incident_service.link_evidence_to_incident(db, incident_id, data.evidence_ids)
    if incident is None:
        raise HTTPException(status_code=404, detail="Incident not found")
    return incident


@router.post("/{incident_id}/correlate", response_model=IncidentWithEvidenceResponse)
def correlate_incident(
    incident_id: UUID,
    window_seconds: int = Query(60, description="Time window (seconds) for cross-trace correlation"),
    db: Session = Depends(get_db),
):
    incident = correlation_service.correlate_incident_evidence(db, incident_id, window_seconds)
    if incident is None:
        raise HTTPException(status_code=404, detail="Incident not found")
    return incident


@router.post("/{incident_id}/investigate", response_model=InvestigationResponse, status_code=201)
def investigate_incident(incident_id: UUID, db: Session = Depends(get_db)):
    """
    Runs a fresh root-cause analysis against this incident's current
    evidence and stores it as a new, immutable Investigation. Safe to
    call more than once (e.g. after correlation adds more evidence) —
    each call creates a new row, never overwrites a previous result.
    """
    try:
        investigation = investigation_service.run_investigation(db, incident_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    if investigation is None:
        raise HTTPException(status_code=404, detail="Incident not found")
    return investigation


@router.get("/{incident_id}/investigations", response_model=list[InvestigationResponse])
def list_investigations(incident_id: UUID, db: Session = Depends(get_db)):
    """Full investigation history for this incident, newest first."""
    incident = incident_repository.get_incident(db, incident_id)
    if incident is None:
        raise HTTPException(status_code=404, detail="Incident not found")
    return investigation_repository.get_investigations_for_incident(db, incident_id)
