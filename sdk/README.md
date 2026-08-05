# tracelens (SDK)

Lightweight Python client for sending evidence (LLM calls, tool calls)
from your AI agent to a TraceLens backend.

## Install (local dev)

```bash
pip install -e sdk/
```

## Usage

```python
from tracelens import TraceLensClient

client = TraceLensClient(project="customer-support-bot", api_url="http://localhost:8000")

# After an LLM call:
client.track_llm_call(
    session_id="conv-8827",
    prompt="Where is my order?",
    response="Let me check that for you.",
    latency_ms=340,
)

# After a tool call:
client.track_tool_call(
    session_id="conv-8827",
    tool_name="order_lookup",
    arguments={"order_id": 12345},
    output="shipped, arriving Tuesday",
    latency_ms=120,
)
```

## Design notes

- Tracking calls never raise — if the TraceLens backend is unreachable,
  a warning is logged and your application keeps running.
- `timestamp` is captured automatically at call time; you don't provide it.
- Currently manual/explicit instrumentation, not auto-wrapping of any
  LLM provider's client — see project docs for why.
