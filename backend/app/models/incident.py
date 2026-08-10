import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, String, DateTime, ForeignKey, Text, Integer
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.core.database import Base


class Incident(Base):
    """
    The investigation unit. Created manually (Day 6); Day 7's
    correlation engine expands its linked evidence automatically.

    NOTE (Day 10): `category` and `taxonomy_version` below were added
    on Day 6 with the intent that the investigation pipeline would
    fill them in. Now that Investigation exists as its own table and
    is the real source of truth for category (see investigation.py),
    these two columns are effectively unused — kept in the schema
    rather than migrated away for no functional gain, but flagged
    here so nobody mistakes them for live data. "Current category"
    for an incident means: the category on its most recent
    Investigation, not these fields.

    `status` defaults to "open" — the full open/investigating/resolved
    workflow (Day 12) isn't built yet.
    """
    __tablename__ = "incidents"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id"), nullable=False, index=True)

    title = Column(String, nullable=False)
    description = Column(Text, nullable=True)

    status = Column(String, nullable=False, default="open")

    # Effectively deprecated as of Day 10 — see docstring above.
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
    investigations = relationship("Investigation", back_populates="incident")

    @property
    def evidence(self):
        """Convenience accessor: the actual Evidence rows linked to this incident."""
        return [link.evidence for link in self.evidence_links]
