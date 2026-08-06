import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, String, DateTime, ForeignKey, Integer
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship

from app.core.database import Base


class Evidence(Base):
    """
    A single observed unit within a trace: one LLM call or one tool
    call. This is the raw material everything else in the system
    (correlation, investigation, root cause) is built from — and it's
    what a root-cause explanation ultimately has to cite.

    `evidence_type` tells us how to interpret `payload`:
      - "llm_call": payload holds {prompt, response, model, ...}
      - "tool_call": payload holds {tool_name, arguments, output, ...}
    """
    __tablename__ = "evidence"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    trace_id = Column(UUID(as_uuid=True), ForeignKey("traces.id"), nullable=False, index=True)

    evidence_type = Column(String, nullable=False)
    payload = Column(JSONB, nullable=False)
    evidence_metadata = Column(JSONB, nullable=True)

    latency_ms = Column(Integer, nullable=True)
    timestamp = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    trace = relationship("Trace", back_populates="evidence")
