import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, String, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.core.database import Base


class Project(Base):
    """
    A logical grouping for evidence — e.g. one AI agent or application
    being monitored. Deliberately has no auth/ownership fields yet
    (Day 1 decision: no multi-tenancy in the MVP), but exists as its
    own table so adding auth later means adding a foreign key,
    not restructuring how evidence is scoped.
    """
    __tablename__ = "projects"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, nullable=False, unique=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    traces = relationship("Trace", back_populates="project")
