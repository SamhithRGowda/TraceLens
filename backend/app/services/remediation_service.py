from typing import Optional
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.remediation import Remediation
from app.repositories import investigation_repository, remediation_repository, evidence_repository
from app.integrations.llm.prompts import build_remediation_prompt
from app.integrations.llm.openai_client import call_llm_json


def run_remediation(db: Session, investigation_id: UUID) -> Optional[Remediation]:
    """
    Generates a fresh advisory remediation for an existing Investigation
    and persists it as a new, immutable Remediation row.

    Returns None if the investigation doesn't exist.

    Grounds the recommendation in exactly the evidence the investigation
    cited (not all evidence on the parent incident) — see Day 11 notes
    on why that matters after Day 10's correlation-noise lesson.
    """
    investigation = investigation_repository.get_investigation(db, investigation_id)
    if investigation is None:
        return None

    cited_evidence = evidence_repository.get_evidence_by_ids(db, investigation.cited_evidence_ids)
    evidence_dicts = [
        {
            "id": str(e.id),
            "evidence_type": e.evidence_type,
            "timestamp": e.timestamp.isoformat(),
            "payload": e.payload,
        }
        for e in cited_evidence
    ]

    system_prompt, user_prompt = build_remediation_prompt(
        category=investigation.category,
        explanation=investigation.explanation,
        evidence=evidence_dicts,
    )
    result = call_llm_json(system_prompt, user_prompt)

    remediation = remediation_repository.create_remediation(
        db,
        investigation_id=investigation_id,
        recommended_fix=result["recommended_fix"],
        rationale=result["rationale"],
        model=settings.openai_model,
    )
    db.commit()
    db.refresh(remediation)
    return remediation
