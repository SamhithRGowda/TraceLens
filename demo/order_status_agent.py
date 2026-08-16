"""
TraceLens Demo: Order Status Agent (Sprint 14 — Live-Agent Ingestion)

Purpose
-------
Proves the ingestion path (SDK -> POST /api/v1/events -> Evidence rows)
with a real runnable script, instead of synthetic/pre-created trace JSON.

IMPORTANT — what this is and isn't:
  This is a DETERMINISTIC, SCRIPTED controlled failure scenario, not an
  organic model hallucination. Both LLM "calls" below are hardcoded
  strings, not real calls to an LLM API. The second one is deliberately
  written to contradict the tool's output (DELIVERED vs. the tool's
  SHIPPED), reproducing the same ground-truth test already validated
  manually (see project handoff, Section 6) — but this time the evidence
  reaches the backend through the actual SDK/ingestion path, not curl.

  Nothing here proves an LLM hallucinates on its own. It proves: given a
  contradiction in the evidence, ingested through the real SDK, the
  existing correlation/investigation pipeline can detect it. That's the
  scope of this sprint.

What this script does NOT do (by design, matching MVP philosophy):
  - Does not call the OpenAI API. No API key required, no cost, no
    nondeterminism — the contradiction reproduces identically every run.
  - Does not create an Incident, correlate, or trigger an investigation.
    Those are separate, explicit steps (see README.md) — this sprint is
    about proving ingestion, not automating incident creation.
  - Does not modify the SDK. Uses TraceLensClient exactly as it exists.

Run:
    python demo/order_status_agent.py
"""

import time
from uuid import uuid4

from tracelens import TraceLensClient


def get_order_status(order_id: str) -> str:
    """
    A small real function standing in for a tool the agent calls —
    not just an inline dict — so the traced "tool call" reflects an
    actual function invocation, matching how track_tool_call is meant
    to be used in a real agent.

    Hardcoded to SHIPPED on purpose: this is the ground-truth fact the
    final LLM step will contradict.
    """
    return "SHIPPED"


def run_agent() -> str:
    client = TraceLensClient(project="order-status-agent", api_url="http://localhost:8000")

    # One session_id for the whole run -> one Trace on the backend.
    # Printed at the end so it can be used for the manual next steps
    # (create incident, link evidence, correlate, investigate).
    session_id = str(uuid4())
    order_id = "ORD-1234"

    print(f"Starting Order Status Agent run — session_id: {session_id}\n")

    # --- Step 1: initial LLM call -------------------------------------
    # Scripted response. Represents the agent deciding to look up the
    # order rather than answering from nothing. Timed with
    # perf_counter() even though it's just string construction — the
    # measurement is real, even if the "work" being measured is trivial;
    # nothing here is a fabricated/hardcoded latency number.
    start = time.perf_counter()
    prompt_1 = f"The customer is asking for an update on order {order_id}. What should I do?"
    response_1 = "I'll check the current status of this order using the order lookup tool."
    latency_1_ms = int((time.perf_counter() - start) * 1000)

    client.track_llm_call(
        session_id=session_id,
        prompt=prompt_1,
        response=response_1,
        model="gpt-4o-mini",
        latency_ms=latency_1_ms,
    )
    print(f"[1/3] Sent llm_call (planning step) — measured {latency_1_ms}ms")

    # --- Step 2: tool call ----------------------------------------------
    # Real function call, real measured duration.
    start = time.perf_counter()
    tool_output = get_order_status(order_id)
    latency_2_ms = int((time.perf_counter() - start) * 1000)

    client.track_tool_call(
        session_id=session_id,
        tool_name="get_order_status",
        arguments={"order_id": order_id},
        output=tool_output,
        latency_ms=latency_2_ms,
    )
    print(f"[2/3] Sent tool_call (get_order_status -> {tool_output}) — measured {latency_2_ms}ms")

    # --- Step 3: final LLM call — the deliberate contradiction ----------
    # Scripted to say DELIVERED despite the tool output above being
    # SHIPPED. This is the ground-truth failure the pipeline is meant
    # to catch. Hardcoded and deterministic — see module docstring.
    start = time.perf_counter()
    prompt_2 = (
        f"The order lookup tool returned status='{tool_output}' for order {order_id}. "
        "Summarize this for the customer."
    )
    response_2 = f"Good news! Your order {order_id} has been delivered. Enjoy your purchase!"
    latency_3_ms = int((time.perf_counter() - start) * 1000)

    client.track_llm_call(
        session_id=session_id,
        prompt=prompt_2,
        response=response_2,
        model="gpt-4o-mini",
        latency_ms=latency_3_ms,
    )
    print(f"[3/3] Sent llm_call (final response, claims DELIVERED) — measured {latency_3_ms}ms")

    print(f"\nDone. session_id: {session_id}")
    print("Use this session_id to create an incident and investigate — see demo/README.md.")

    return session_id


if __name__ == "__main__":
    run_agent()
