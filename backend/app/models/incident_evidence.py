import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, String, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.core.database import Base


class IncidentEvidence(Base):
    """
    Links one piece of Evidence to one Incident. A join table rather
    than a foreign key directly on Evidence, for two reasons:
      1. Flexibility — evidence could in principle be relevant to
         more than one incident.
      2. `linked_by` records *how* the link was made — "manual"
         (Day 6, a human attached it) vs "correlation" (Day 7, the
         system inferred it) — a fact about the relationship itself,
         which wouldn't have anywhere to live on a plain FK.
    """
    __tablename__ = "incident_evidence"
    __table_args__ = (UniqueConstraint("incident_id", "evidence_id", name="uq_incident_evidence"),)

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    incident_id = Column(UUID(as_uuid=True), ForeignKey("incidents.id"), nullable=False, index=True)
    evidence_id = Column(UUID(as_uuid=True), ForeignKey("evidence.id"), nullable=False, index=True)

    linked_by = Column(String, nullable=False, default="manual")
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    incident = relationship("Incident", back_populates="evidence_links")
    evidence = relationship("Evidence")
