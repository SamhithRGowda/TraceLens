import logging
import math
from typing import Any, Optional
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.investigation import Investigation
from app.repositories import incident_repository, investigation_repository
from app.services import evidence_signals
from app.integrations.llm.prompts import build_root_cause_prompt, TAXONOMY, TAXONOMY_VERSION
from app.integrations.llm.openai_client import call_llm_json

logger = logging.getLogger(__name__)

# Read from prompts.py, never redefined here — the taxonomy stays
# single-sourced, so adding a category there is enough to make it valid.
_TAXONOMY_NAMES = {t["name"] for t in TAXONOMY}

# Already a taxonomy member ("doesn't fit the other categories"), which is
# exactly what an unrecognised category means.
_FALLBACK_CATEGORY = "other"


def _validated_category(raw: Any) -> str:
    """
    The prompt asks for one of the taxonomy names; nothing enforced it, so
    an unrecognised value used to be persisted verbatim and then rendered
    as a real classification. Anything off-taxonomy becomes "other".
    """
    if isinstance(raw, str) and raw in _TAXONOMY_NAMES:
        return raw
    logger.warning(
        "Investigation LLM returned off-taxonomy category %r; falling back to %r",
        raw,
        _FALLBACK_CATEGORY,
    )
    return _FALLBACK_CATEGORY


def _validated_confidence(raw: Any) -> float:
    """
    Clamped into [0, 1] — the range the UI's percentage and bar assume.

    A non-numeric or non-finite value can't be clamped into anything
    meaningful, so it becomes 0.0: "no stated confidence" is the honest
    reading, and it keeps the column's float contract intact.
    """
    # bool is an int subclass, so True would otherwise clamp to 1.0 and
    # read as a genuine high-confidence result.
    if isinstance(raw, bool) or not isinstance(raw, (int, float)):
        logger.warning("Investigation LLM returned non-numeric confidence %r; using 0.0", raw)
        return 0.0

    value = float(raw)
    if math.isnan(value) or math.isinf(value):
        logger.warning("Investigation LLM returned non-finite confidence %r; using 0.0", raw)
        return 0.0

    return min(1.0, max(0.0, value))


def _validated_cited_ids(raw: Any, linked_ids: set[UUID]) -> list[str]:
    """
    Keeps only ids that parse as UUIDs *and* belong to evidence already
    linked to this incident, in the order cited, deduped.

    This is what makes "evidence-backed" enforceable rather than merely
    requested by the prompt: an invented id is dropped here instead of
    being stored and shown as a citation. It also protects the read path —
    InvestigationResponse types this field as list[UUID], so a non-UUID
    string committed fine and then broke every subsequent
    GET /incidents/{id}/investigations.
    """
    if not isinstance(raw, list):
        logger.warning("Investigation LLM returned non-list cited_evidence_ids %r; using []", raw)
        return []

    kept: list[str] = []
    seen: set[UUID] = set()

    for entry in raw:
        try:
            parsed = UUID(str(entry))
        except (AttributeError, TypeError, ValueError):
            logger.warning("Dropping unparseable cited evidence id %r", entry)
            continue

        if parsed not in linked_ids:
            logger.warning(
                "Dropping cited evidence id %s — not linked to this incident", parsed
            )
            continue

        if parsed in seen:
            continue

        seen.add(parsed)
        kept.append(str(parsed))

    return kept


def run_investigation(db: Session, incident_id: UUID) -> Optional[Investigation]:
    """
    Runs a fresh root-cause analysis against an incident's current
    evidence and persists the result as a new, immutable Investigation.

    Returns None if the incident doesn't exist.
    Raises ValueError if the incident has no linked evidence — there's
    nothing to analyze, and calling the LLM with an empty bundle would
    just waste a request and produce a meaningless result.

    The model's response is validated before it's persisted (see the
    _validated_* helpers above): the category must be a taxonomy name,
    confidence must land in [0, 1], and every cited evidence id must
    belong to evidence actually linked to this incident.

    Before the model is called, evidence_signals computes the structural
    facts about the bundle. Where one of those facts decides the category
    outright (context_overflow, infinite_loop), it is authoritative and the
    model's job narrows to explaining that failure; otherwise the facts are
    passed as premises and the model distinguishes the semantic categories.
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

    # A trace is a sequence, and several taxonomy categories are
    # sequence-dependent (a response contradicting an earlier tool result,
    # the same call repeating). The relationship behind incident.evidence
    # carries no ORDER BY, so the bundle previously reached the model in
    # whatever order Postgres returned the join rows.
    ordered_evidence = sorted(evidence, key=lambda e: e.timestamp)

    evidence_dicts = [
        {
            "id": str(e.id),
            "evidence_type": e.evidence_type,
            "timestamp": e.timestamp.isoformat(),
            "payload": e.payload,
        }
        for e in ordered_evidence
    ]

    # Deterministic pre-classification. A few categories are structural
    # facts about the bundle rather than judgements about it — three
    # byte-identical calls, an explicit token-limit marker — so they are
    # counted in code, and the model no longer gets the chance to be talked
    # out of them by the loudest thing in the trace. See evidence_signals
    # for why stating this precedence in the prompt didn't hold.
    signals = evidence_signals.detect_signals(evidence_dicts)
    decided_category = signals.authoritative_category

    system_prompt, user_prompt = build_root_cause_prompt(
        evidence_dicts,
        signals=signals.to_prompt_dicts(),
        decided_category=decided_category,
    )
    result = call_llm_json(system_prompt, user_prompt)

    # Validation gate. Everything below is checked before it's persisted;
    # previously result["category"], result["confidence"] and
    # result["cited_evidence_ids"] went straight into the row unexamined.
    # `explanation` is left as-is: it's free text with no valid/invalid
    # form to check, and a missing key raising here matches the existing
    # behaviour.
    linked_ids = {e.id for e in evidence}

    # An authoritative signal IS the category, whatever the model replied.
    # The prompt already asked for that category, so a mismatch here means
    # the model talked itself out of a counted fact: keep the fact, and say
    # so in the log rather than silently.
    category = _validated_category(result.get("category"))
    if decided_category and category != decided_category:
        logger.warning(
            "Incident %s: overriding LLM category %r with deterministic signal category %r",
            incident_id,
            category,
            decided_category,
        )
        category = decided_category

    investigation = investigation_repository.create_investigation(
        db,
        incident_id=incident_id,
        category=category,
        confidence=_validated_confidence(result.get("confidence")),
        explanation=result["explanation"],
        cited_evidence_ids=_validated_cited_ids(result.get("cited_evidence_ids"), linked_ids),
        taxonomy_version=TAXONOMY_VERSION,
        model=settings.openai_model,
    )
    db.commit()
    db.refresh(investigation)
    return investigation
