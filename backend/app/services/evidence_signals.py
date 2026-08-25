"""
Deterministic evidence signals for the investigation pipeline.

Why this module exists: the Trace Library classification eval ran at 1/9,
then 2/9 after the precedence rules were rewritten in the prompt. The
diagnosis was not that the model is weak. It is that the loudest fact in
every failing trace is "the agent's final response is wrong", and
`hallucination` as the taxonomy defines it ("asserts a claim with no
support in the retrieved context or tool output") is satisfied by that
fact in *every* one of those traces. It is a superset of the observable
symptom of the other failure modes, so a single-label 7-way choice
collapses onto it regardless of how the prompt orders its rules. Stating
precedence as prose lost to evidence salience twice, in two different
wordings.

Some of those categories never needed a model. Three identical
`charge_card` calls is a countable fact. `context_length_exceeded` in a
payload is a string that is either present or absent. This module computes
those facts in code, which turns precedence into control flow instead of a
suggestion the model may decline to follow.

Everything here is pure. It takes the same evidence bundle
run_investigation already builds for the prompt — dicts of
id / evidence_type / timestamp / payload — and returns dataclasses. No
Session, no ORM, no network, no I/O, no scenario ids: detection reads the
actual payload structure the SDK writes, so it works on any ingested
trace, not just the curated library. That is also why it can be tested
exhaustively with no database and no API key.

Deliberately NOT implemented: any rule of the form "the response isn't
supported by the evidence, therefore hallucination". That inference is the
exact thing this module exists to stop competing with, and it is a
judgement about meaning rather than structure. It stays with the model.
"""

import dataclasses
import json
from typing import Any, Iterator, Optional

# Explicit context/token-limit signals. Matched against every key and
# string value in a payload, so `{"truncated_tokens": 1200}` is caught by
# its key even though the value is a number.
_OVERFLOW_MARKERS = (
    "context_length_exceeded",
    "context length exceeded",
    "context_window",
    "context window",
    "maximum context",
    "max_context",
    "token_limit",
    "token limit",
    "max_tokens",
    "too many tokens",
    "truncat",  # truncated / truncation / truncated_tokens
)

# Explicit "the thing you asked for isn't here" signals. Matched ONLY
# against a tool call's `output`, never its arguments — a query argument
# like {"query": "missing claim"} is a request, not a failure.
_NOT_FOUND_MARKERS = (
    "not_found",
    "not found",
    "notfound",
    "no_results",
    "no results",
    "no_record",
    "no record",
    "no_data",
    "no data",
    "does_not_exist",
    "does not exist",
    "unavailable",
    "unknown_id",
    "missing",
)

# Phrases a response uses when it *does* acknowledge that a lookup failed.
# If a response after a not-found signal contains none of these, the agent
# answered as though the lookup had succeeded.
_ACKNOWLEDGEMENT_MARKERS = (
    "not found",
    "couldn't find",
    "could not find",
    "unable",
    "no record",
    "no results",
    "don't have",
    "do not have",
    "wasn't able",
    "was not able",
    "cannot",
    "can't",
    "error",
    "failed",
    "apolog",
    "sorry",
    "missing",
    "unavailable",
    "invalid",
)

# Three or more identical calls is a loop by the taxonomy's own wording
# ("the same call is repeated without state change") and is decided here.
# Exactly two is ambiguous — one retry is ordinary — so it is reported as
# a premise only, and only when the outputs were identical too.
_LOOP_AUTHORITATIVE_REPEATS = 3
_LOOP_MIN_REPEATS = 2


@dataclasses.dataclass(frozen=True)
class Signal:
    """
    One deterministic finding about an evidence bundle.

    Carries the evidence it was computed from, not just a verdict, so the
    model receives the finding *and* its basis and can cite the same rows
    back — a category string alone would be an unfalsifiable assertion.
    """

    name: str
    # The taxonomy category this finding implies.
    category: str
    # True when the finding decides the category outright, without a model.
    authoritative: bool
    detail: str
    evidence_ids: tuple[str, ...]

    def to_prompt_dict(self) -> dict[str, Any]:
        return {
            "category": self.category,
            "detail": self.detail,
            "evidence_ids": list(self.evidence_ids),
            "authoritative": self.authoritative,
        }


@dataclasses.dataclass(frozen=True)
class SignalReport:
    """Signals in precedence order: context_overflow, infinite_loop, missing_context."""

    signals: tuple[Signal, ...] = ()

    @property
    def authoritative_category(self) -> Optional[str]:
        """
        The category decided in code, if any. Precedence is the tuple's
        order, so context_overflow beats infinite_loop when both fire.
        """
        for signal in self.signals:
            if signal.authoritative:
                return signal.category
        return None

    def to_prompt_dicts(self) -> list[dict[str, Any]]:
        return [signal.to_prompt_dict() for signal in self.signals]


def _walk_strings(value: Any) -> Iterator[str]:
    """Every dict key and string value anywhere in a payload, lowercased."""
    if isinstance(value, dict):
        for key, nested in value.items():
            yield str(key).lower()
            yield from _walk_strings(nested)
    elif isinstance(value, (list, tuple)):
        for item in value:
            yield from _walk_strings(item)
    elif isinstance(value, str):
        yield value.lower()


def _matches(value: Any, markers: tuple[str, ...]) -> Optional[str]:
    """The first marker found in `value`, or None."""
    for text in _walk_strings(value):
        for marker in markers:
            if marker in text:
                return marker
    return None


def _canonical(value: Any) -> str:
    """Order-independent form of a payload fragment, for identity comparison."""
    try:
        return json.dumps(value, sort_keys=True, default=str)
    except (TypeError, ValueError):
        return repr(value)


def _payload(item: dict[str, Any]) -> dict[str, Any]:
    payload = item.get("payload")
    return payload if isinstance(payload, dict) else {}


def _evidence_id(item: dict[str, Any]) -> str:
    return str(item.get("id", ""))


def _call_identity(item: dict[str, Any]) -> Optional[tuple[str, ...]]:
    """
    What makes two evidence rows "the same call". Reads the structure the
    SDK actually writes: tool calls are identified by name + arguments,
    LLM calls by prompt. Rows that don't carry those fields are skipped
    rather than guessed at.
    """
    payload = _payload(item)
    evidence_type = item.get("evidence_type")

    if evidence_type == "tool_call":
        tool_name = payload.get("tool_name")
        if not tool_name:
            return None
        return ("tool_call", str(tool_name), _canonical(payload.get("arguments")))

    if evidence_type == "llm_call":
        prompt = payload.get("prompt")
        if not prompt:
            return None
        return ("llm_call", _canonical(prompt))

    return None


def _ordered(evidence: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """
    Chronological. run_investigation already sorts, but the detectors below
    depend on "before/after" being real, so this doesn't take it on trust.
    Timestamps are ISO-8601 from one database, so string order is time
    order; the index keeps the sort stable when they tie or are absent.
    """
    return [
        item
        for _, item in sorted(
            enumerate(evidence),
            key=lambda pair: (str(pair[1].get("timestamp") or ""), pair[0]),
        )
    ]


def _detect_context_overflow(evidence: list[dict[str, Any]]) -> Optional[Signal]:
    """
    An explicit truncation or token-limit signal anywhere in a payload.
    Authoritative: the marker is present or it isn't, and no reading of the
    surrounding prose changes that.
    """
    hits: list[str] = []
    marker: Optional[str] = None

    for item in evidence:
        found = _matches(_payload(item), _OVERFLOW_MARKERS)
        if found:
            marker = marker or found
            hits.append(_evidence_id(item))

    if not hits:
        return None

    return Signal(
        name="explicit_context_limit_marker",
        category="context_overflow",
        authoritative=True,
        detail=(
            f"{len(hits)} evidence item(s) contain an explicit context/token-limit "
            f"marker (matched {marker!r}). Context was truncated or a limit was "
            "exceeded during this execution."
        ),
        evidence_ids=tuple(hits),
    )


def _detect_infinite_loop(evidence: list[dict[str, Any]]) -> Optional[Signal]:
    """
    The same call repeated with no change in arguments. Counted, not
    inferred: identity comes from tool_name + arguments (or the prompt for
    an LLM call), so this generalises to any ingested trace.
    """
    identities: dict[tuple[str, ...], list[dict[str, Any]]] = {}
    for item in evidence:
        identity = _call_identity(item)
        if identity is not None:
            identities.setdefault(identity, []).append(item)

    def outputs_identical(items: list[dict[str, Any]]) -> bool:
        return len({_canonical(_payload(item).get("output")) for item in items}) == 1

    # Two identical calls with differing results is ordinary (pagination, a
    # refetch after a change). Two with the *same* result is a retry that
    # made no progress — worth reporting, not worth deciding alone.
    qualifying = [
        items
        for items in identities.values()
        if len(items) >= _LOOP_AUTHORITATIVE_REPEATS
        or (len(items) >= _LOOP_MIN_REPEATS and outputs_identical(items))
    ]
    if not qualifying:
        return None

    group = max(qualifying, key=len)
    count = len(group)
    payload = _payload(group[0])
    label = payload.get("tool_name") or group[0].get("evidence_type") or "call"
    identical_outputs = outputs_identical(group)

    shared_error = None
    if identical_outputs:
        output = payload.get("output")
        if isinstance(output, dict):
            shared_error = output.get("error")

    detail = (
        f"'{label}' was called {count} times with byte-identical arguments and no "
        "intervening state change"
    )
    if identical_outputs:
        detail += ", each returning the same result"
        if shared_error:
            detail += f" ({shared_error!r})"
    detail += "."

    return Signal(
        name="repeated_identical_call",
        category="infinite_loop",
        authoritative=count >= _LOOP_AUTHORITATIVE_REPEATS,
        detail=detail,
        evidence_ids=tuple(_evidence_id(item) for item in group),
    )


def _detect_missing_context(evidence: list[dict[str, Any]]) -> Optional[Signal]:
    """
    A structural not-found/unavailable result from a tool, followed by a
    later response that answers as though the lookup had succeeded.

    Both halves are required. The not-found marker alone is not a failure
    (an agent that reports "no record found" behaved correctly), and a
    later response alone is just a response. Reported as a premise, never
    authoritative: whether the agent's answer actually depended on the
    absent data is a judgement about meaning, which is the model's job.
    """
    for index, item in enumerate(evidence):
        if item.get("evidence_type") != "tool_call":
            continue

        payload = _payload(item)
        marker = _matches(payload.get("output"), _NOT_FOUND_MARKERS)
        if not marker:
            continue

        for later in evidence[index + 1 :]:
            if later.get("evidence_type") != "llm_call":
                continue

            response = _payload(later).get("response")
            if not isinstance(response, str) or not response.strip():
                continue

            if _matches(response, _ACKNOWLEDGEMENT_MARKERS):
                # The agent said the lookup failed. Nothing structural to flag.
                continue

            tool_name = payload.get("tool_name") or "a tool"
            return Signal(
                name="unacknowledged_lookup_failure",
                category="missing_context",
                authoritative=False,
                detail=(
                    f"'{tool_name}' returned a not-found/unavailable result "
                    f"(matched {marker!r}), and a later response answered the user "
                    "without acknowledging that the lookup failed. The information "
                    "the answer needed was never retrieved."
                ),
                evidence_ids=(_evidence_id(item), _evidence_id(later)),
            )

    return None


def detect_signals(evidence: list[dict[str, Any]]) -> SignalReport:
    """
    Runs every detector over an evidence bundle and returns the findings in
    precedence order. Pure: same bundle in, same report out, always.
    """
    ordered = _ordered(evidence)

    found = [
        detector(ordered)
        for detector in (
            _detect_context_overflow,
            _detect_infinite_loop,
            _detect_missing_context,
        )
    ]

    return SignalReport(signals=tuple(signal for signal in found if signal is not None))
