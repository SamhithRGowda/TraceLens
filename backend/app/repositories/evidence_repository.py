from uuid import UUID

from sqlalchemy.orm import Session

from app.models.evidence import Evidence
from app.schemas.evidence import EvidenceCreate


def create_evidence(db: Session, trace_id: UUID, data: EvidenceCreate) -> Evidence:
    evidence = Evidence(
        trace_id=trace_id,
        evidence_type=data.evidence_type.value,
        payload=data.payload,
        evidence_metadata=data.metadata,
        latency_ms=data.latency_ms,
        timestamp=data.timestamp,
    )
    db.add(evidence)
    db.flush()
    return evidence
