from sqlalchemy.orm import Session

from app.models.evidence import Evidence
from app.repositories.project_repository import get_or_create_project
from app.repositories.trace_repository import get_or_create_trace
from app.repositories.evidence_repository import create_evidence
from app.schemas.evidence import EvidenceCreate


def ingest_evidence(db: Session, data: EvidenceCreate) -> Evidence:
    """
    The full ingestion sequence, as one transaction:
      1. resolve (or create) the Project this evidence belongs to
      2. resolve (or create) the Trace this evidence belongs to
      3. create the Evidence row itself
      4. commit — all three succeed together, or none do

    That last point matters: if evidence creation failed after we'd
    already committed a new Project, we'd have a Project with no
    evidence and no way to know why. Wrapping all three in one
    transaction avoids that half-finished state.
    """
    project = get_or_create_project(db, data.project_name)
    trace = get_or_create_trace(db, project.id, data.session_id, data.timestamp)
    evidence = create_evidence(db, trace.id, data)

    db.commit()
    db.refresh(evidence)
    return evidence
