"""
Prompt construction for the investigation pipeline.

build_root_cause_prompt (Day 9): diagnosis — what happened and why.
build_remediation_prompt (Day 11): prescription — what to do about it.
Kept as separate functions/prompts deliberately — different reasoning
tasks, iterated on independently.
"""

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


def build_root_cause_prompt(evidence: list[dict]) -> tuple[str, str]:
    """Returns (system_prompt, user_prompt) for root-cause diagnosis."""
    taxonomy_text = "\n".join(f"- {t['name']}: {t['description']}" for t in TAXONOMY)

    system_prompt = (
        "You are an AI incident investigator. Given a bundle of evidence "
        "(LLM calls and tool calls) from an AI agent's execution, determine "
        "the most likely root cause of a failure.\n\n"
        f"Use exactly one of these categories:\n{taxonomy_text}\n\n"
        "Respond ONLY with a JSON object with this exact shape:\n"
        "{\n"
        '  "category": "<one of the category names above>",\n'
        '  "confidence": <float between 0 and 1>,\n'
        '  "explanation": "<plain-language explanation>",\n'
        '  "cited_evidence_ids": ["<evidence id>", ...]\n'
        "}\n\n"
        "cited_evidence_ids MUST reference actual ids from the evidence "
        "provided below. Never cite an id that wasn't given to you. If no "
        "single piece of evidence clearly supports a specific category, "
        "use category \"other\" and explain why in plain language."
    )

    user_prompt = f"Evidence:\n{_format_evidence(evidence)}"

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
