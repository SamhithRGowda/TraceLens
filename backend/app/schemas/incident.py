from datetime import datetime
from enum import Enum
from typing import Optional
from uuid import UUID

from pydantic import BaseModel

from app.schemas.evidence import EvidenceResponse


class IncidentStatus(str, Enum):
    OPEN = "open"
    INVESTIGATING = "investigating"
    RESOLVED = "resolved"


class IncidentCreate(BaseModel):
    project_name: str
    title: str
    description: Optional[str] = None
    # Optional seed evidence. When present, create_incident links it and
    # correlates outward from it in the same transaction — the "select a
    # trace, get an assembled incident" path. When absent, behavior is
    # unchanged: a bare incident, linked/correlated via their own
    # endpoints if at all.
    evidence_ids: list[UUID] = []


class StatusUpdateRequest(BaseModel):
    status: IncidentStatus


class IncidentResponse(BaseModel):
    id: UUID
    project_id: UUID
    title: str
    description: Optional[str]
    status: IncidentStatus
    category: Optional[str]
    created_at: datetime
    updated_at: datetime
    resolved_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class EvidenceLinkRequest(BaseModel):
    evidence_ids: list[UUID]


class IncidentWithEvidenceResponse(IncidentResponse):
    evidence: list[EvidenceResponse]
