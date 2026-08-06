import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, String, DateTime, ForeignKey, Text, Integer
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.core.database import Base


class Incident(Base):
    """
    The investigation unit. Created manually today (Day 6); Day 7's
    correlation engine will eventually help populate `evidence_links`
    automatically, and Day 9/10's investigation pipeline will fill in
    `category` and `taxonomy_version` from our failure taxonomy.

    `status` defaults to "open" — the full open/investigating/resolved
    workflow (Day 12) isn't built yet, but the field exists now so
    nothing needs restructuring when it arrives.
    """
    __tablename__ = "incidents"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id"), nullable=False, index=True)

    title = Column(String, nullable=False)
    description = Column(Text, nullable=True)

    status = Column(String, nullable=False, default="open")

    # Filled in later by the investigation pipeline (Day 9/10), not today.
    category = Column(String, nullable=True)
    taxonomy_version = Column(Integer, nullable=True)

    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    project = relationship("Project", back_populates="incidents")
    evidence_links = relationship("IncidentEvidence", back_populates="incident")

    @property
    def evidence(self):
        """Convenience accessor: the actual Evidence rows linked to this incident."""
        return [link.evidence for link in self.evidence_links]
