import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, String, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.core.database import Base


class Trace(Base):
    """
    One agent execution / session — e.g. one full LangGraph run, one
    conversation. Evidence rows belong to a Trace, and a Trace belongs
    to a Project.

    `session_id` is the *external* identifier — whatever the SDK/agent
    framework calls this run (a LangChain run id, a custom session
    string, etc). It's how ingestion (Day 4) finds-or-creates the
    right Trace for incoming evidence: "have I seen this session_id
    for this project before?"

    `started_at` / `ended_at` are nullable because we don't know them
    up front — Day 4's ingestion logic sets started_at when the trace
    is first created, and updates ended_at as more evidence arrives.
    """
    __tablename__ = "traces"
    __table_args__ = (UniqueConstraint("project_id", "session_id", name="uq_trace_project_session"),)

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id"), nullable=False)
    session_id = Column(String, nullable=False, index=True)

    started_at = Column(DateTime(timezone=True), nullable=True)
    ended_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    project = relationship("Project", back_populates="traces")
    evidence = relationship("Evidence", back_populates="trace")
