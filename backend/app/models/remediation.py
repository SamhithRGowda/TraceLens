import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, String, DateTime, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.core.database import Base


class Remediation(Base):
    """
    An immutable, advisory recommendation generated from a specific
    Investigation's diagnosis and cited evidence. Same pattern as
    Investigation itself: never updated after creation, one
    Investigation can have multiple Remediations over time.

    Advisory only, by design and by prompt (see prompts.py) — this
    table stores a plain-language recommendation for a human to
    review, never a code change or an action taken automatically.
    """
    __tablename__ = "remediations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    investigation_id = Column(UUID(as_uuid=True), ForeignKey("investigations.id"), nullable=False, index=True)

    recommended_fix = Column(Text, nullable=False)
    rationale = Column(Text, nullable=False)
    model = Column(String, nullable=False)

    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    investigation = relationship("Investigation", back_populates="remediations")
