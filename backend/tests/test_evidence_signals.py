"""
Deterministic evidence-signal detector tests.

Pure unit tests: no database, no network, no OpenAI key, no LLM call. Every
bundle below is the actual payload structure the SDK writes, taken from the
real Trace Library scenarios (verified against the seeded rows in Postgres),
so a passing test here means the detector fires on the data the pipeline
will really see. Evidence ids are synthetic — the detector never looks at
them beyond echoing them back.

Dependency-free by design, matching the two existing test files (no pytest
installed; adding a test framework is still out of scope):

    docker compose exec -T backend python - < backend/tests/test_evidence_signals.py
"""

from app.services.evidence_signals import detect_signals


def ev(eid, kind, payload, ts):
    return {"id": eid, "evidence_type": kind, "timestamp": ts, "payload": payload}


def llm(eid, prompt, response, ts):
    return ev(eid, "llm_call", {"model": "gpt-4o-mini", "prompt": prompt, "response": response}, ts)


def tool(eid, name, arguments, output, ts):
    return ev(eid, "tool_call", {"tool_name": name, "arguments": arguments, "output": output}, ts)


def categories(report):
    return [s.category for s in report.signals]


# --- context_overflow ------------------------------------------------

# Real payloads from trace-library-context-overflow-truncation.
CONTEXT_OVERFLOW_BUNDLE = [
    llm("e1", "Customer reports intermittent integration failures. Begin troubleshooting.",
        "Let's start by checking your recent API request logs.", "2026-01-01T00:00:00+00:00"),
    tool("e2", "get_request_logs", {"range": "24h", "customer_id": "CUST-6630"},
         {"logs": "... 200 OK ... 200 OK ... 429 rate_limited ..."}, "2026-01-01T00:00:01+00:00"),
    llm("e3", "The logs show occasional 429 rate-limit responses. Explain this to the customer.",
        "It looks like you're occasionally hitting our rate limit — I'd recommend adding backoff logic.",
        "2026-01-01T00:00:02+00:00"),
    tool("e4", "get_conversation_context", {"session_id": "support-6630"},
         {"error": "context_length_exceeded", "truncated_tokens": 1200}, "2026-01-01T00:00:03+00:00"),
    llm("e5", "Continue troubleshooting using the full conversation so far.",
        "As I mentioned, this is unrelated to rate limits — it's actually a DNS misconfiguration on your end.",
        "2026-01-01T00:00:04+00:00"),
]


def test_context_overflow():
    report = detect_signals(CONTEXT_OVERFLOW_BUNDLE)
    assert report.authoritative_category == "context_overflow", (
        f"FAIL: real overflow bundle gave {report.authoritative_category!r}."
    )
    signal = report.signals[0]
    assert "e4" in signal.evidence_ids, f"FAIL: didn't cite the overflow row: {signal.evidence_ids}"
    print("PASS (context_overflow): explicit context_length_exceeded marker detected, authoritative.")

    # truncated_tokens alone — matched by KEY, not value; the value is an int.
    only_key = [tool("t1", "get_ctx", {}, {"truncated_tokens": 900}, "2026-01-01T00:00:00+00:00")]
    assert detect_signals(only_key).authoritative_category == "context_overflow", (
        "FAIL: a truncation marker present only as a dict key was missed."
    )
    print("PASS (context_overflow): marker found in a payload key, not just a string value.")

    # Nested inside a list — markers can be anywhere in the payload tree.
    nested = [tool("t2", "get_docs", {}, [{"note": "output was TRUNCATED here"}], "2026-01-01T00:00:00+00:00")]
    assert detect_signals(nested).authoritative_category == "context_overflow", (
        "FAIL: a truncation marker nested in a list was missed."
    )
    print("PASS (context_overflow): marker found nested in a list, case-insensitively.")

    # And must NOT fire on an ordinary trace.
    clean = [
        llm("c1", "Look up the order.", "Checking now.", "2026-01-01T00:00:00+00:00"),
        tool("c2", "get_order_status", {"order_id": "ORD-1"}, "SHIPPED", "2026-01-01T00:00:01+00:00"),
    ]
    assert detect_signals(clean).authoritative_category is None, (
        "FAIL: overflow fired on a bundle with no limit marker."
    )
    print("PASS (context_overflow): does not fire without an explicit marker.")


# --- infinite_loop ---------------------------------------------------

# Real payloads from trace-library-payment-retry-loop: three byte-identical
# charge_card calls, each returning gateway_timeout, then a false success.
RETRY_LOOP_BUNDLE = [
    llm("l1", "Charge the customer's card for this month's subscription.", "I'll process the charge now.",
        "2026-01-01T00:00:00+00:00"),
    tool("l2", "charge_card", {"amount": 29.99, "customer_id": "CUST-2290"},
         {"error": "gateway_timeout"}, "2026-01-01T00:00:01+00:00"),
    tool("l3", "charge_card", {"amount": 29.99, "customer_id": "CUST-2290"},
         {"error": "gateway_timeout"}, "2026-01-01T00:00:02+00:00"),
    tool("l4", "charge_card", {"amount": 29.99, "customer_id": "CUST-2290"},
         {"error": "gateway_timeout"}, "2026-01-01T00:00:03+00:00"),
    llm("l5", "Report the outcome of the charge to the customer.",
        "Your payment was processed successfully. Thank you!", "2026-01-01T00:00:04+00:00"),
]


def test_infinite_loop():
    report = detect_signals(RETRY_LOOP_BUNDLE)
    assert report.authoritative_category == "infinite_loop", (
        f"FAIL: real retry-loop bundle gave {report.authoritative_category!r}."
    )
    signal = next(s for s in report.signals if s.category == "infinite_loop")
    assert set(signal.evidence_ids) == {"l2", "l3", "l4"}, (
        f"FAIL: wrong rows cited for the loop: {signal.evidence_ids}"
    )
    assert "gateway_timeout" in signal.detail, f"FAIL: shared error not surfaced: {signal.detail}"
    print("PASS (infinite_loop): 3 identical calls detected and cited, authoritative.")

    # Argument order must not matter — payloads are JSONB, key order isn't stable.
    reordered = [
        tool("r1", "charge_card", {"amount": 29.99, "customer_id": "C"}, {"error": "t"}, "2026-01-01T00:00:01+00:00"),
        tool("r2", "charge_card", {"customer_id": "C", "amount": 29.99}, {"error": "t"}, "2026-01-01T00:00:02+00:00"),
        tool("r3", "charge_card", {"amount": 29.99, "customer_id": "C"}, {"error": "t"}, "2026-01-01T00:00:03+00:00"),
    ]
    assert detect_signals(reordered).authoritative_category == "infinite_loop", (
        "FAIL: identical calls with reordered argument keys weren't recognised as identical."
    )
    print("PASS (infinite_loop): argument key order ignored (JSONB-safe).")

    # DIFFERENT arguments are not a loop, however many calls.
    distinct = [
        tool("d1", "charge_card", {"amount": 1}, {"error": "t"}, "2026-01-01T00:00:01+00:00"),
        tool("d2", "charge_card", {"amount": 2}, {"error": "t"}, "2026-01-01T00:00:02+00:00"),
        tool("d3", "charge_card", {"amount": 3}, {"error": "t"}, "2026-01-01T00:00:03+00:00"),
    ]
    assert detect_signals(distinct).authoritative_category is None, (
        "FAIL: three calls with different arguments were reported as a loop."
    )
    print("PASS (infinite_loop): differing arguments are not a loop.")

    # Two identical calls with DIFFERENT results: a legitimate refetch.
    # Reported not at all — no state change can't be claimed.
    refetch = [
        tool("f1", "get_status", {"id": "X"}, {"state": "pending"}, "2026-01-01T00:00:01+00:00"),
        tool("f2", "get_status", {"id": "X"}, {"state": "done"}, "2026-01-01T00:00:02+00:00"),
    ]
    assert detect_signals(refetch).signals == (), (
        "FAIL: a refetch that returned a changed result was flagged."
    )
    print("PASS (infinite_loop): two identical calls with changed results not flagged.")

    # Two identical calls with identical results: a stalled retry. Worth
    # telling the model about, NOT worth deciding on its own.
    stalled = [
        tool("s1", "get_status", {"id": "X"}, {"state": "pending"}, "2026-01-01T00:00:01+00:00"),
        tool("s2", "get_status", {"id": "X"}, {"state": "pending"}, "2026-01-01T00:00:02+00:00"),
    ]
    report = detect_signals(stalled)
    assert categories(report) == ["infinite_loop"], f"FAIL: expected a premise, got {categories(report)}"
    assert report.authoritative_category is None, (
        "FAIL: two repeats decided the category outright; only 3+ should be authoritative."
    )
    print("PASS (infinite_loop): 2 repeats reported as a premise only, not authoritative.")


# --- missing_context -------------------------------------------------

# Real payloads from trace-library-missing-claim-context.
MISSING_CONTEXT_BUNDLE = [
    llm("m1", "Customer is asking for their claim status. Look it up.",
        "I'll look up this claim using the policy number on file.", "2026-01-01T00:00:00+00:00"),
    tool("m2", "get_claim_status", {"policy_number": "POL-00812"},
         {"error": "policy_not_found"}, "2026-01-01T00:00:01+00:00"),
    llm("m3", "Report the claim status to the customer.",
        "Your claim is under review — expect a decision within 5-7 business days.",
        "2026-01-01T00:00:02+00:00"),
]


def test_missing_context():
    report = detect_signals(MISSING_CONTEXT_BUNDLE)
    assert categories(report) == ["missing_context"], f"FAIL: got {categories(report)}"
    signal = report.signals[0]
    # Never authoritative: whether the answer actually depended on the
    # absent data is a judgement about meaning, left to the model.
    assert not signal.authoritative, "FAIL: missing_context must be a premise, not authoritative."
    assert report.authoritative_category is None
    assert set(signal.evidence_ids) == {"m2", "m3"}, f"FAIL: wrong rows cited: {signal.evidence_ids}"
    print("PASS (missing_context): not-found + unacknowledged answer detected as a premise.")

    # The agent that DOES acknowledge the failure behaved correctly.
    acknowledged = [
        MISSING_CONTEXT_BUNDLE[0],
        MISSING_CONTEXT_BUNDLE[1],
        llm("a3", "Report the claim status to the customer.",
            "I couldn't find a claim under that policy number — could you confirm it?",
            "2026-01-01T00:00:02+00:00"),
    ]
    assert detect_signals(acknowledged).signals == (), (
        "FAIL: flagged an agent that correctly reported the lookup failure."
    )
    print("PASS (missing_context): does not fire when the response acknowledges the failure.")

    # A not-found-ish word in ARGUMENTS is a query, not a failure.
    query_only = [
        tool("q1", "search_kb", {"query": "missing claim policy"}, [{"title": "Claims FAQ"}],
             "2026-01-01T00:00:00+00:00"),
        llm("q2", "Answer the customer.", "Here's how claims work.", "2026-01-01T00:00:01+00:00"),
    ]
    assert detect_signals(query_only).signals == (), (
        "FAIL: a marker word in tool ARGUMENTS was treated as a lookup failure."
    )
    print("PASS (missing_context): marker in arguments ignored; only tool output counts.")

    # Ordering matters: a response BEFORE the failed lookup proves nothing.
    before_only = [
        llm("b1", "Answer the customer.", "Your claim is under review.", "2026-01-01T00:00:00+00:00"),
        tool("b2", "get_claim_status", {"policy_number": "P"}, {"error": "policy_not_found"},
             "2026-01-01T00:00:01+00:00"),
    ]
    assert detect_signals(before_only).signals == (), (
        "FAIL: fired on a response that preceded the failed lookup."
    )
    print("PASS (missing_context): requires the unsupported response to come AFTER the failure.")


# --- what must NOT be detected ---------------------------------------

def test_no_generic_hallucination_rule():
    """
    The contradiction scenario (tool returned SHIPPED, response said
    delivered) must produce NO signal. "Unsupported response =>
    hallucination" is exactly the over-firing rule that collapsed the
    classifier; that judgement stays with the model.
    """
    contradiction = [
        llm("h1", "The customer is asking for an update on order ORD-1234. What should I do?",
            "I'll check the current status of this order using the order lookup tool.",
            "2026-01-01T00:00:00+00:00"),
        tool("h2", "get_order_status", {"order_id": "ORD-1234"}, "SHIPPED", "2026-01-01T00:00:01+00:00"),
        llm("h3", "The order lookup tool returned status='SHIPPED' for order ORD-1234. Summarize this for the customer.",
            "Good news! Your order ORD-1234 has been delivered. Enjoy your purchase!",
            "2026-01-01T00:00:02+00:00"),
    ]
    report = detect_signals(contradiction)
    assert report.signals == (), f"FAIL: contradiction bundle produced signals: {categories(report)}"
    print("PASS (no over-firing): contradiction/hallucination bundle yields no deterministic signal.")

    # Same for the accurate-but-unauthorized scenario (expected "other").
    unauthorized = [
        llm("u1", "Customer is asking for retirement savings guidance given current market conditions.",
            "Let me check current market conditions and this customer's portfolio.", "2026-01-01T00:00:00+00:00"),
        tool("u2", "get_market_summary", {}, {"sp500_ytd": "+8%", "ten_year_yield": "4.3%"},
             "2026-01-01T00:00:01+00:00"),
        tool("u3", "get_portfolio_summary", {"user_id": "USR-4471"}, {"bonds_pct": 70, "equities_pct": 30},
             "2026-01-01T00:00:02+00:00"),
        llm("u4", "Advise the customer using the market and portfolio data.",
            "Given current conditions, you should move 40% of your bond holdings into equities right now.",
            "2026-01-01T00:00:03+00:00"),
    ]
    assert detect_signals(unauthorized).signals == (), (
        "FAIL: the accurate-but-unauthorized bundle produced a deterministic signal."
    )
    print("PASS (no over-firing): accurate-but-unauthorized bundle yields no signal.")

    # And the healthy control.
    healthy = [
        llm("p1", "Customer forgot their password.", "I'll send a reset link.", "2026-01-01T00:00:00+00:00"),
        tool("p2", "send_password_reset", {"email": "a@b.com"}, {"sent": True}, "2026-01-01T00:00:01+00:00"),
        llm("p3", "Confirm to the customer.", "A reset link is on its way to a@b.com.",
            "2026-01-01T00:00:02+00:00"),
    ]
    assert detect_signals(healthy).signals == (), "FAIL: healthy control produced a signal."
    print("PASS (no over-firing): healthy control yields no signal.")


# --- precedence, purity, robustness ----------------------------------

def test_precedence_and_purity():
    # Overflow AND loop in one bundle: overflow wins, both are reported.
    both = RETRY_LOOP_BUNDLE + [
        tool("x1", "get_conversation_context", {"s": "1"},
             {"error": "context_length_exceeded"}, "2026-01-01T00:00:05+00:00"),
    ]
    report = detect_signals(both)
    assert report.authoritative_category == "context_overflow", (
        f"FAIL: precedence broken, got {report.authoritative_category!r}."
    )
    assert categories(report)[:2] == ["context_overflow", "infinite_loop"], (
        f"FAIL: signals not in precedence order: {categories(report)}"
    )
    print("PASS (precedence): context_overflow outranks infinite_loop; both still reported.")

    # Order-independent: shuffled input, identical report. The detectors
    # sort internally rather than trusting the caller.
    shuffled = [RETRY_LOOP_BUNDLE[i] for i in (4, 1, 3, 0, 2)]
    assert detect_signals(shuffled) == detect_signals(RETRY_LOOP_BUNDLE), (
        "FAIL: report depended on input ordering."
    )
    print("PASS (purity): shuffled bundle produces an identical report.")

    # Pure: repeated calls agree, and the input is not mutated.
    snapshot = [dict(item) for item in MISSING_CONTEXT_BUNDLE]
    first = detect_signals(MISSING_CONTEXT_BUNDLE)
    second = detect_signals(MISSING_CONTEXT_BUNDLE)
    assert first == second, "FAIL: detect_signals is not deterministic across calls."
    assert MISSING_CONTEXT_BUNDLE == snapshot, "FAIL: detect_signals mutated its input."
    print("PASS (purity): repeatable, and the input bundle is untouched.")

    # Malformed / partial rows must not raise — real ingestion has gaps.
    malformed = [
        {"id": "z1"},
        {"id": "z2", "evidence_type": "tool_call", "payload": None, "timestamp": None},
        {"id": "z3", "evidence_type": "llm_call", "payload": {"response": None}},
        {"id": "z4", "evidence_type": "tool_call", "payload": {"tool_name": "t"}},
        {"id": "z5", "evidence_type": "weird_type", "payload": {"a": 1}, "timestamp": "x"},
    ]
    assert detect_signals(malformed).signals == (), "FAIL: malformed rows produced a signal."
    assert detect_signals([]).signals == (), "FAIL: empty bundle produced a signal."
    print("PASS (robustness): malformed and empty bundles handled without raising.")


def test_prompt_serialisation():
    """
    The report must serialise into the shape build_root_cause_prompt
    consumes — carrying the evidence behind each signal, not just a
    category string.
    """
    dicts = detect_signals(RETRY_LOOP_BUNDLE).to_prompt_dicts()
    assert len(dicts) == 1
    entry = dicts[0]
    assert set(entry) == {"category", "detail", "evidence_ids", "authoritative"}, (
        f"FAIL: unexpected prompt dict shape: {sorted(entry)}"
    )
    assert entry["category"] == "infinite_loop"
    assert entry["authoritative"] is True
    assert isinstance(entry["evidence_ids"], list) and len(entry["evidence_ids"]) == 3
    assert entry["detail"], "FAIL: signal detail was empty."
    print("PASS (serialisation): prompt dict carries category, detail, and evidence ids.")

    # The prompt builder must accept it, keep the previous output when given
    # nothing, and pin the category when one was decided.
    from app.integrations.llm.prompts import build_root_cause_prompt

    evidence_dicts = [
        {"id": i["id"], "evidence_type": i["evidence_type"], "timestamp": i["timestamp"], "payload": i["payload"]}
        for i in RETRY_LOOP_BUNDLE
    ]
    base_system, base_user = build_root_cause_prompt(evidence_dicts)
    sig_system, sig_user = build_root_cause_prompt(
        evidence_dicts, signals=dicts, decided_category="infinite_loop"
    )
    assert sig_system == base_system, "FAIL: signals changed the system prompt; they belong in the user prompt."
    assert base_user in sig_user, "FAIL: the evidence section was altered rather than appended to."
    assert "infinite_loop" in sig_user and "charge_card" in sig_user, (
        "FAIL: the decided category or its detail is missing from the user prompt."
    )
    print("PASS (serialisation): prompt builder appends premises; default call is unchanged.")


def run():
    test_context_overflow()
    test_infinite_loop()
    test_missing_context()
    test_no_generic_hallucination_rule()
    test_precedence_and_purity()
    test_prompt_serialisation()
    print("\nAll evidence-signal cases passed.")


if __name__ == "__main__":
    run()
