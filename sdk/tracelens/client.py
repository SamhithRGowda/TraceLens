"""
TraceLens SDK client.

Design principles (see Day 5 notes for full reasoning):
  1. Explicit, not magic — you call track_llm_call/track_tool_call
     yourself, right after the real call. No monkey-patching of
     other libraries, so nothing here breaks when OpenAI (or anyone
     else) changes their SDK internals.
  2. Never crash the host application. If TraceLens's backend is
     down or slow, that's our problem, not the AI agent's — we log
     a warning and move on, we never raise.
  3. Timestamp is captured here, at the moment the real event
     happened — not left to the backend to guess on arrival.
"""

import logging
from datetime import datetime, timezone
from typing import Any, Optional

import requests

logger = logging.getLogger("tracelens")


class TraceLensClient:
    def __init__(self, project: str, api_url: str = "http://localhost:8000", timeout: float = 2.0):
        self.project = project
        self.api_url = api_url.rstrip("/")
        self.timeout = timeout

    def _send(
        self,
        session_id: str,
        evidence_type: str,
        payload: dict[str, Any],
        latency_ms: Optional[int] = None,
        metadata: Optional[dict[str, Any]] = None,
    ) -> Optional[dict]:
        body = {
            "project_name": self.project,
            "session_id": session_id,
            "evidence_type": evidence_type,
            "payload": payload,
            "latency_ms": latency_ms,
            "metadata": metadata,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        try:
            response = requests.post(f"{self.api_url}/api/v1/events", json=body, timeout=self.timeout)
            response.raise_for_status()
            return response.json()
        except Exception as exc:
            # Principle #2: never let a broken/slow backend break the
            # agent we're observing. Warn, don't raise.
            logger.warning("TraceLens: failed to send evidence (%s)", exc)
            return None

    def track_llm_call(
        self,
        session_id: str,
        prompt: str,
        response: str,
        model: Optional[str] = None,
        latency_ms: Optional[int] = None,
        metadata: Optional[dict[str, Any]] = None,
    ) -> Optional[dict]:
        payload = {"prompt": prompt, "response": response}
        if model:
            payload["model"] = model
        return self._send(session_id, "llm_call", payload, latency_ms, metadata)

    def track_tool_call(
        self,
        session_id: str,
        tool_name: str,
        arguments: dict[str, Any],
        output: Any,
        latency_ms: Optional[int] = None,
        metadata: Optional[dict[str, Any]] = None,
    ) -> Optional[dict]:
        payload = {"tool_name": tool_name, "arguments": arguments, "output": output}
        return self._send(session_id, "tool_call", payload, latency_ms, metadata)
