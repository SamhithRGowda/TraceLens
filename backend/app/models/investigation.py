import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, String, DateTime, ForeignKey, Text, Float, Integer
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship

from app.core.database import Base


class Investigation(Base):
    """
    An immutable snapshot of a root-cause analysis run against an
    Incident's evidence at a point in time. Never updated after
    creation — re-running analysis creates a NEW Investigation row,
    preserving earlier conclusions even as correlation (Day 7)
    discovers more evidence later.

    `cited_evidence_ids` is stored directly as JSONB, not as a join
    table — this is a frozen fact about the past ("at this moment,
    given this evidence, the conclusion was X"), not a live
    relationship, so it belongs baked into the snapshot itself.

    "Current result" for an incident = the Investigation with the
    most recent created_at. No separate latest/current flag — MVP
    scope decision, ordering by created_at is enough.
    """
    __tablename__ = "investigations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    incident_id = Column(UUID(as_uuid=True), ForeignKey("incidents.id"), nullable=False, index=True)

    category = Column(String, nullable=False)
    confidence = Column(Float, nullable=False)
    explanation = Column(Text, nullable=False)
    cited_evidence_ids = Column(JSONB, nullable=False)

    taxonomy_version = Column(Integer, nullable=False)
    model = Column(String, nullable=False)

    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    incident = relationship("Incident", back_populates="investigations")
