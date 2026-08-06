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


class IncidentResponse(BaseModel):
    id: UUID
    project_id: UUID
    title: str
    description: Optional[str]
    status: IncidentStatus
    category: Optional[str]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class EvidenceLinkRequest(BaseModel):
    evidence_ids: list[UUID]


class IncidentWithEvidenceResponse(IncidentResponse):
    evidence: list[EvidenceResponse]
