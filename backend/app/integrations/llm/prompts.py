"""
Prompt construction for root-cause analysis.

The taxonomy embedded here matches Day 1's versioned failure taxonomy.
If the taxonomy definitions change, bump TAXONOMY_VERSION — this is
what lets a stored Investigation be traced back to which version of
the taxonomy produced it (same reasoning as Incident.taxonomy_version
from Day 6).
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


def _format_evidence(evidence: list[dict]) -> str:
    """
    Each item is rendered with its real database id so the model can
    cite specific rows back to us — this is what makes "evidence-backed
    root cause" a checkable claim instead of a vibe.
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
    """Returns (system_prompt, user_prompt) ready to hand to call_llm_json."""
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
