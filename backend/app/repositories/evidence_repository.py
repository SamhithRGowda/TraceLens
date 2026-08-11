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


def get_evidence_by_trace_ids(db: Session, trace_ids) -> list[Evidence]:
    return db.query(Evidence).filter(Evidence.trace_id.in_(trace_ids)).all()


def get_evidence_by_ids(db: Session, evidence_ids) -> list[Evidence]:
    """
    Used by remediation (Day 11) to fetch exactly the evidence an
    Investigation cited — not all evidence linked to the incident.
    Grounding remediation in the same evidence the diagnosis actually
    pointed to avoids repeating Day 10's lesson (irrelevant correlated
    evidence diluting the result) one step further downstream.
    """
    return db.query(Evidence).filter(Evidence.id.in_(evidence_ids)).all()
