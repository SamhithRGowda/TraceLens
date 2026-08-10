from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class InvestigationResponse(BaseModel):
    id: UUID
    incident_id: UUID
    category: str
    confidence: float
    explanation: str
    cited_evidence_ids: list[UUID]
    taxonomy_version: int
    model: str
    created_at: datetime

    class Config:
        from_attributes = True
