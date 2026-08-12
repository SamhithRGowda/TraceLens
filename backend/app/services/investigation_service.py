from typing import Optional
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.investigation import Investigation
from app.repositories import incident_repository, investigation_repository
from app.integrations.llm.prompts import build_root_cause_prompt, TAXONOMY_VERSION
from app.integrations.llm.openai_client import call_llm_json


def run_investigation(db: Session, incident_id: UUID) -> Optional[Investigation]:
    """
    Runs a fresh root-cause analysis against an incident's current
    evidence and persists the result as a new, immutable Investigation.

    Returns None if the incident doesn't exist.
    Raises ValueError if the incident has no linked evidence — there's
    nothing to analyze, and calling the LLM with an empty bundle would
    just waste a request and produce a meaningless result.
    """
    incident = incident_repository.get_incident(db, incident_id)
    if incident is None:
        return None

    evidence = incident.evidence
    if not evidence:
        raise ValueError("Cannot investigate an incident with no linked evidence.")

    # Day 12: running an investigation is a real signal the incident is
    # actively being worked, so we keep status honest with that — but
    # only nudge it forward from "open", never override "resolved" or
    # an already-"investigating" incident being re-investigated.
    if incident.status == "open":
        incident_repository.set_status(db, incident, "investigating")

    evidence_dicts = [
        {
            "id": str(e.id),
            "evidence_type": e.evidence_type,
            "timestamp": e.timestamp.isoformat(),
            "payload": e.payload,
        }
        for e in evidence
    ]

    system_prompt, user_prompt = build_root_cause_prompt(evidence_dicts)
    result = call_llm_json(system_prompt, user_prompt)

    investigation = investigation_repository.create_investigation(
        db,
        incident_id=incident_id,
        category=result["category"],
        confidence=result["confidence"],
        explanation=result["explanation"],
        cited_evidence_ids=result["cited_evidence_ids"],
        taxonomy_version=TAXONOMY_VERSION,
        model=settings.openai_model,
    )
    db.commit()
    db.refresh(investigation)
    return investigation
