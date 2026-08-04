from datetime import datetime
from enum import Enum
from typing import Optional, Any
from uuid import UUID

from pydantic import BaseModel, Field


class EvidenceType(str, Enum):
    """
    Closed set on purpose — unlike the failure taxonomy (which needs
    an 'Other' escape hatch), evidence types are stable and few.
    A typo here should be rejected, not silently stored.
    """
    LLM_CALL = "llm_call"
    TOOL_CALL = "tool_call"


class EvidenceCreate(BaseModel):
    """
    What the SDK (or a curl request, for now) sends us. project_name
    and session_id are plain strings, not UUIDs — the caller shouldn't
    need to know our internal IDs, just their own project/session
    names. Ingestion resolves those into real Project/Trace rows.
    """
    project_name: str = Field(..., min_length=1)
    session_id: str = Field(..., min_length=1)
    evidence_type: EvidenceType
    payload: dict[str, Any]
    metadata: Optional[dict[str, Any]] = None
    latency_ms: Optional[int] = None
    timestamp: datetime


class EvidenceResponse(BaseModel):
    """What we hand back after successfully storing evidence."""
    id: UUID
    trace_id: UUID
    evidence_type: EvidenceType
    timestamp: datetime
    created_at: datetime

    class Config:
        from_attributes = True  # lets us build this directly from an Evidence ORM object
