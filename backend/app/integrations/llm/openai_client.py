"""
Thin wrapper around the OpenAI SDK.

Isolated on purpose (Day 9): if we tune model choice, temperature, or
retry behavior, this is the only file that should need to change —
prompt content (prompts.py) and orchestration (Day 10's investigation
pipeline) shouldn't be affected by changes here.
"""

import json
import logging
from typing import Any, Optional

from openai import OpenAI

from app.core.config import settings

logger = logging.getLogger("tracelens.llm")

_client: Optional[OpenAI] = None


def get_client() -> OpenAI:
    global _client
    if _client is None:
        if not settings.openai_api_key:
            raise RuntimeError(
                "OPENAI_API_KEY is not set. Add it to your .env file before calling the LLM."
            )
        _client = OpenAI(api_key=settings.openai_api_key)
    return _client


def call_llm_json(system_prompt: str, user_prompt: str, model: Optional[str] = None) -> dict[str, Any]:
    """
    Calls the LLM and parses its response as JSON.

    Raises ValueError if the response isn't valid JSON — deliberately
    left to the caller (Day 10) to decide how to handle that (retry,
    fall back to category="other", etc). This file's only job is
    "talk to OpenAI and hand back parsed JSON or fail clearly."
    """
    client = get_client()
    response = client.chat.completions.create(
        model=model or settings.openai_model,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0,
    )
    raw = response.choices[0].message.content

    try:
        return json.loads(raw)
    except json.JSONDecodeError as exc:
        logger.error("LLM returned invalid JSON: %s", raw)
        raise ValueError(f"LLM response was not valid JSON: {exc}") from exc
