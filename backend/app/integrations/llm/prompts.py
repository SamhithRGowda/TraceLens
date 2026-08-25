"""
Prompt construction for the investigation pipeline.

build_root_cause_prompt (Day 9): diagnosis — what happened and why.
build_remediation_prompt (Day 11): prescription — what to do about it.
Kept as separate functions/prompts deliberately — different reasoning
tasks, iterated on independently.
"""

from typing import Optional

TAXONOMY_VERSION = 1

TAXONOMY = [
    {
        "name": "hallucination",
        "description": "The response asserts a claim with no support in the retrieved context or tool output.",
    },
    {
        "name": "tool_misuse",
        "description": "Wrong tool selected, wrong arguments used, or tool output misinterpreted.",
    },
    {
        "name": "prompt_injection",
        "description": "Untrusted input contains instruction-like content that the model appears to have followed.",
    },
    {
        "name": "infinite_loop",
        "description": "The same call is repeated without state change (covers agent-driven loops and retry storms).",
    },
    {
        "name": "missing_context",
        "description": "The response depends on information that was never present in the evidence.",
    },
    {
        "name": "context_overflow",
        "description": "Evidence shows truncation, token-limit errors, or context exceeding model limits.",
    },
    {
        "name": "other",
        "description": "Doesn't fit any category above. Requires a free-text explanation.",
    },
]

_TAXONOMY_LOOKUP = {t["name"]: t["description"] for t in TAXONOMY}


def _format_evidence(evidence: list[dict]) -> str:
    """
    Each item is rendered with its real database id so the model can
    cite specific rows back to us — this is what makes "evidence-backed"
    a checkable claim instead of a vibe.
    """
    lines = []
    for item in evidence:
        lines.append(
            f"- id: {item['id']}\n"
            f"  type: {item['evidence_type']}\n"
            f"  timestamp: {item['timestamp']}\n"
            f"  payload: {item['payload']}"
        )
    return "\n".join(lines)


def _format_signals(signals: list[dict]) -> str:
    """
    Renders the deterministic findings from evidence_signals as premises.

    They go in the USER prompt, next to the evidence they were computed
    from, rather than in the system prompt: they are facts about this one
    bundle, not standing instructions. Each carries the evidence ids it
    came from so the model can cite the same rows rather than take the
    finding on faith.
    """
    lines = []
    for signal in signals:
        ids = ", ".join(signal.get("evidence_ids", []))
        lines.append(f"- [{signal['category']}] {signal['detail']} (evidence: {ids})")
    return "\n".join(lines)


def build_root_cause_prompt(
    evidence: list[dict],
    signals: Optional[list[dict]] = None,
    decided_category: Optional[str] = None,
) -> tuple[str, str]:
    """
    Returns (system_prompt, user_prompt) for root-cause diagnosis.

    `signals` are deterministic findings computed in code by
    app.services.evidence_signals — counted repetitions, explicit
    token-limit markers, and so on. `decided_category` is set when one of
    those findings decides the category outright, in which case the model
    is asked to explain that failure rather than to re-choose a label it
    has repeatedly gotten wrong on near-ties.

    Both default to None, which reproduces the previous prompt exactly.
    """
    taxonomy_text = "\n".join(f"- {t['name']}: {t['description']}" for t in TAXONOMY)

    system_prompt = (
        "You are an AI incident investigator. Given a bundle of evidence "
        "(LLM calls and tool calls) from an AI agent's execution, determine "
        "whether the execution demonstrates a failure, and if so, its most "
        "likely root cause.\n\n"
        "Follow this reasoning order:\n"
        "1. First determine whether the evidence actually demonstrates a "
        "failure. Check whether each claim in the agent's response is "
        "directly supported by the tool outputs and context in the "
        "evidence.\n"
        "2. If the execution is fully supported by the evidence and no "
        "failure is demonstrated, still respond with the required JSON "
        "shape below, using category \"other\" and an explanation stating "
        "that no failure was found.\n"
        "3. If a failure is demonstrated, determine which single category "
        "below is the most appropriate root cause, based only on what the "
        "evidence actually shows.\n\n"
        f"Use exactly one of these categories:\n{taxonomy_text}\n\n"
        "To choose between them, work through the following checklist in "
        "order. THE FIRST RULE WHOSE CONDITION IS MET IS THE CATEGORY. "
        "Stop there. Do not keep going to look for a better fit, and do "
        "not switch to a later rule because it also describes the trace — "
        "most real traces match more than one, and the earlier rule always "
        "wins.\n\n"
        "1. context_overflow — any payload shows truncation, a token-limit "
        "or context-length error, dropped/omitted context, or context "
        "exceeding a model limit. If such a signal is present, this is the "
        "category even if the response also states something incorrect "
        "afterwards.\n"
        "2. infinite_loop — the same call is repeated with no meaningful "
        "change in arguments or state (an agent-driven loop or a retry "
        "cycle). Treat the repetition itself as the failure, even if a "
        "later response also describes the outcome incorrectly.\n"
        "3. prompt_injection — content returned by a tool or retrieved "
        "from an untrusted source contains instruction-like directives, "
        "and the response appears to have followed them.\n"
        "4. tool_misuse — the wrong tool was called for the question "
        "asked, the arguments were wrong, or the wrong/stale/superseded "
        "item was applied from what a tool returned. This rule is about "
        "SELECTION: which tool, which arguments, which document. If the "
        "correct tool and correct document were used and the response "
        "merely misstated what they returned, this rule does NOT fire — "
        "continue to rule 5.\n"
        "5. hallucination — the evidence does contain the relevant "
        "information, and the response contradicts it, restates it as a "
        "different value or status, or asserts something beyond it that "
        "nothing in the evidence supports.\n"
        "6. missing_context — the information the response depended on was "
        "never retrieved and is not in the evidence at all. Use this "
        "rather than rule 5 when the gap is that the data was never "
        "there, not that available data was misread.\n"
        "7. other — every factual statement in the response is supported "
        "by the evidence and the right tools and documents were used, but "
        "the response or action goes beyond the task, scope, permissions, "
        "or authority the agent had. Also use this when no failure is "
        "demonstrated at all.\n\n"
        "Write your explanation and cite the specific evidence it's based "
        "on BEFORE choosing a category — your category choice must follow "
        "from what you just wrote, not the reverse.\n\n"
        "Respond ONLY with a JSON object with this exact shape:\n"
        "{\n"
        '  "explanation": "<plain-language explanation>",\n'
        '  "cited_evidence_ids": ["<evidence id>", ...],\n'
        '  "category": "<one of the category names above>",\n'
        '  "confidence": <float between 0 and 1>\n'
        "}\n\n"
        "cited_evidence_ids MUST reference actual ids from the evidence "
        "provided below. Never cite an id that wasn't given to you. If no "
        "single piece of evidence clearly supports a specific category, "
        "use category \"other\" and explain why in plain language."
    )

    user_prompt = f"Evidence:\n{_format_evidence(evidence)}"

    if signals:
        user_prompt += (
            "\n\nDeterministic analysis of the evidence above, computed by static "
            "analysis of the payloads rather than by a model. Treat each of these "
            "as an established fact, not a suggestion:\n"
            f"{_format_signals(signals)}"
        )

    if decided_category:
        user_prompt += (
            f"\n\nThe category has already been determined to be "
            f'"{decided_category}" by that analysis. Set "category" to exactly '
            f'"{decided_category}" and write the explanation for that failure, '
            "citing the evidence the finding above was computed from. Do not "
            "choose a different category, even if another one also describes "
            "part of what went wrong."
        )
    elif signals:
        user_prompt += (
            "\n\nThese findings narrow the choice but do not decide it. Use them "
            "together with the evidence to pick the single most appropriate "
            "category."
        )

    return system_prompt, user_prompt


def build_remediation_prompt(category: str, explanation: str, evidence: list[dict]) -> tuple[str, str]:
    """
    Returns (system_prompt, user_prompt) for generating a remediation
    recommendation from an EXISTING diagnosis (category + explanation)
    plus the specific evidence that diagnosis cited.

    Deliberately advisory-only: the system prompt explicitly forbids
    code output or autonomous framing, per the MVP constraint that
    TraceLens recommends fixes, it does not apply them.
    """
    category_description = _TAXONOMY_LOOKUP.get(category, "No description available.")

    system_prompt = (
        "You are an AI incident remediation advisor. You have been given "
        "a root-cause diagnosis for an AI agent failure, along with the "
        "evidence that supports it. Recommend a concrete, actionable fix.\n\n"
        "IMPORTANT: You are an ADVISOR only. Do not write code, do not "
        "propose applying any change automatically, and do not describe "
        "yourself as taking action. Describe the fix in plain language, "
        "as a recommendation for a human engineer to review and implement "
        "themselves.\n\n"
        "Respond ONLY with a JSON object with this exact shape:\n"
        "{\n"
        '  "recommended_fix": "<a concrete, actionable recommendation, in plain language>",\n'
        '  "rationale": "<why this fix addresses the specific root cause identified below>"\n'
        "}"
    )

    user_prompt = (
        f"Diagnosed root cause category: {category} ({category_description})\n"
        f"Diagnosis explanation: {explanation}\n\n"
        f"Supporting evidence:\n{_format_evidence(evidence)}"
    )

    return system_prompt, user_prompt
