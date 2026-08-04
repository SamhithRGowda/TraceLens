from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.evidence import EvidenceCreate, EvidenceResponse
from app.services.ingestion_service import ingest_evidence

router = APIRouter(prefix="/events", tags=["events"])


@router.post("", response_model=EvidenceResponse, status_code=201)
def create_event(data: EvidenceCreate, db: Session = Depends(get_db)):
    """
    Accepts one piece of evidence (an LLM call or tool call) and
    stores it — creating the Project and Trace it belongs to if
    they don't exist yet.
    """
    evidence = ingest_evidence(db, data)
    return evidence
