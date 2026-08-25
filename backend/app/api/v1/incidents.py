from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.repositories import incident_repository, investigation_repository
from app.schemas.incident import (
    IncidentCreate,
    IncidentResponse,
    EvidenceLinkRequest,
    IncidentWithEvidenceResponse,
    StatusUpdateRequest,
)
from app.schemas.investigation import InvestigationResponse
from app.services import incident_service, correlation_service, investigation_service

router = APIRouter(prefix="/incidents", tags=["incidents"])


@router.post("", response_model=IncidentResponse, status_code=201)
def create_incident(data: IncidentCreate, db: Session = Depends(get_db)):
    """
    Creates an incident. If `evidence_ids` is supplied, that evidence is
    linked and correlated in the same transaction (see
    incident_service.create_incident); omitting it creates a bare
    incident exactly as before.
    """
    try:
        return incident_service.create_incident(db, data)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


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


@router.patch("/{incident_id}/status", response_model=IncidentResponse)
def update_incident_status(incident_id: UUID, data: StatusUpdateRequest, db: Session = Depends(get_db)):
    """
    Explicit, manual status change — open/investigating/resolved.
    Rejects unknown values (handled by the enum) and no-op transitions
    (setting to the status it's already at). No automatic resolution
    detection; a human decides when something is actually resolved.
    """
    try:
        incident = incident_service.set_incident_status(db, incident_id, data.status.value)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    if incident is None:
        raise HTTPException(status_code=404, detail="Incident not found")
    return incident


@router.post("/{incident_id}/correlate", response_model=IncidentWithEvidenceResponse)
def correlate_incident(
    incident_id: UUID,
    # Defaulted from the service's own constant, not a literal. A literal
    # here silently overrode it: the route always passes this value
    # explicitly, so a hardcoded 60 meant every HTTP correlate ran the 60s
    # window that Sprint 15 tightened to 30s — the service default was
    # only ever reached by direct callers (e.g. the regression test).
    window_seconds: int = Query(
        correlation_service.DEFAULT_TIME_WINDOW_SECONDS,
        description="Time window (seconds) for cross-trace correlation",
    ),
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
