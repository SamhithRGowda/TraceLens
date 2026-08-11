from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class RemediationResponse(BaseModel):
    id: UUID
    investigation_id: UUID
    recommended_fix: str
    rationale: str
    model: str
    created_at: datetime

    class Config:
        from_attributes = True
