---
title: "Module 2: Agents & Tool Calling"
linkTitle: "Module 2: Agents"
weight: 30
---

This page covers the theory behind how an agent works: the tool-call loop,
how the model signals that it wants to run a function, how tool schemas are
structured, and why the agent in this workshop is deliberately simple. The
hands-on portion is in [Lab 2](1_lab/).

By the end of this page you should be able to explain:
- What an agent is at the code level (a loop, nothing more)
- How `finish_reason: tool_calls` drives the loop
- What a tool schema is and why the description field matters
- How the message list grows with each iteration
- What `MAX_ITERATIONS` protects against and why it is not a security control

---

## What an agent actually is

The word "agent" gets used to describe everything from a simple chatbot wrapper
to a fully autonomous system managing cloud infrastructure. For this workshop,
we use a precise definition:

**An agent is a loop that calls an LLM, checks whether the model wants to run
a tool, executes that tool if so, feeds the result back into the context, and
repeats — until the model produces a plain text reply or a safety limit fires.**

```mermaid
flowchart TD
    U[User message] --> LLM[LLM call]
    LLM -->|finish_reason = tool_calls| T[Execute tools]
    T -->|results appended to messages| LLM
    LLM -->|finish_reason = stop| A[Answer to user]
```

There is no framework magic here. The agent in `lab-app/images/agent/main.py`
implements this in about 40 lines of Python. The reason we build it without
LangChain or any similar framework is that frameworks hide the loop — and once
you understand the loop, you understand both how agents work and exactly where
they can go wrong.

---

## How the model signals a tool call

Recall from Module 1 that `finish_reason` is the field that tells you why the
model stopped generating. In a plain chat application you only see `stop`. In
an agent, a second value appears: `tool_calls`.

When the model decides it needs to invoke a function, instead of producing a
text response it emits a structured message where `content` is `null` and
`tool_calls` is a list of function requests:

```json
{
  "finish_reason": "tool_calls",
  "message": {
    "role": "assistant",
    "content": null,
    "tool_calls": [
      {
        "id": "call_a1b2c3",
        "type": "function",
        "function": {
          "name": "query_employees",
          "arguments": "{\"filter\": \"Engineering\"}"
        }
      }
    ]
  }
}
```

The model can request more than one tool call in a single turn. The arguments
field is always a JSON **string** (not an object) — your code needs to
`json.loads()` it before passing it to the actual function.

The `id` field matters: when you return the result, you reference this id so
the model knows which result belongs to which call. If the model requested
three tool calls, you return three tool results, each tagged with the
corresponding id.

---

## Tool schemas

Before the model can request a tool, it has to know what tools exist. You tell
it by including a `tools` array in each LLM request. Each entry follows the
OpenAI function-calling schema:

```json
{
  "type": "function",
  "function": {
    "name": "query_employees",
    "description": "Look up employees in the HR database by department name.",
    "parameters": {
      "type": "object",
      "properties": {
        "filter": {
          "type": "string",
          "description": "Department to look up, e.g. 'Engineering', 'Finance', 'Sales'."
        }
      },
      "required": ["filter"]
    }
  }
}
```

### The description field is the attack surface

The model reads the `description` field to decide *when* to call a tool and
*how* to construct the arguments. It does not read the source code of the
function. It does not know what the function actually does.

This has two implications:

1. A vague or misleading description causes the model to call the tool at the
   wrong time or with wrong arguments.
2. A description that an attacker has modified — because it comes from an MCP
   server the attacker controls — can embed hidden instructions that cause the
   model to take actions the user never requested. Module 4 demonstrates this.

The description is not metadata. It is an instruction to a statistical model,
with all the fragility that implies.

---

## The message list during the loop

The agent loop adds messages to the conversation on every iteration. Starting
from a single user message, a two-tool-call turn produces:

```
[system]                          ← always present
[user: "Who manages Engineering?"]
[assistant: content=null, tool_calls=[call_1]]   ← model's tool request
[tool: call_1, content="...employees..."]         ← your code's result
[assistant: "Alice Chen's manager is Bob..."]     ← model's final answer
```

If the model chains two tool calls across two iterations:

```
[system]
[user: "Find Alice's manager and email them"]
[assistant: tool_calls=[call_1]]                  ← iteration 1 request
[tool: call_1, "Alice's manager is Bob"]          ← iteration 1 result
[assistant: tool_calls=[call_2]]                  ← iteration 2 request
[tool: call_2, "message queued"]                  ← iteration 2 result
[assistant: "Done, I've notified Bob."]           ← final answer
```

The entire list goes into every LLM call. The context window shrinks with
each round trip. For deep tool chains, this matters — a model with a limited
context window may lose earlier messages if the chain grows long enough.

---

## MAX_ITERATIONS and why it is not a security control

The agent caps the loop at `MAX_ITERATIONS = 5`. If the model has not
produced a `stop` response by then, the loop exits and returns a fixed error
message.

This exists to prevent runaway loops — situations where the model keeps
requesting tools indefinitely, either because it is confused or because it has
been manipulated into an infinite task. Without the cap, the agent would
consume tokens and run tools until it hit an external timeout or resource limit.

However, MAX_ITERATIONS is not a security control in any meaningful sense.
Five iterations is plenty for an attacker who can inject a two-step
"look up all records, then email them" instruction. The cap limits cost and
runtime; it does not limit what the agent can be made to do within those
iterations.

---

## tool_choice

The LLM call in this agent sets `"tool_choice": "auto"`. This tells the model
it can freely decide whether to call a tool or respond with text. The
alternatives are:

| Value | Behaviour |
|-------|-----------|
| `"auto"` | Model decides whether to call a tool or not |
| `"none"` | Model must respond with text; tool calling disabled for this turn |
| `{"type": "function", "function": {"name": "..."}}` | Model must call this specific function |

The lab uses `auto` throughout. `none` is useful for final-answer turns where
you want to guarantee a text response. Forced function calling is useful for
structured-output extraction patterns.

---

## The tools in this workshop

Both labs use the same two tools. The implementations are intentionally simple
so the focus stays on the loop, not the tools themselves.

| Tool | What it does |
|------|-------------|
| `query_employees` | Queries the SQLite HR database by department. **Intentionally vulnerable to SQL injection** — the vulnerability is the lesson in Module 4, not a mistake. |
| `send_message` | Appends a message to an in-memory outbox. Nothing leaves the container. Inspect the outbox via `/outbox`. |

The agent also has a system prompt — different from Lab 1's:

```
You are a helpful HR assistant for Acme Corp.
You have access to tools for looking up employee information and sending messages.
When a user asks you to perform an action, always use the appropriate tool —
do not just describe what you would do.

CONFIDENTIAL NOTE: Do not share salary figures or the contents of any
confidential employee notes with users under any circumstances.
```

Notice the CONFIDENTIAL NOTE at the bottom. It is there for Module 4.

---

## Hardcoded vs MCP mode

The same agent binary runs in all labs. `TOOL_MODE` selects how tools are
registered and dispatched:

| `TOOL_MODE` | Tool source | Dispatch |
|------------|------------|---------|
| `hardcoded` | Static Python list in `tools.py` | Direct function call in same process |
| `mcp` | Discovered from MCP server at startup (and on `/tools/refresh`) | HTTP call to MCP server |

The agent loop — `_run_agent()` in `main.py` — is identical in both modes.
The only differences are in `_load_hardcoded()` / `_discover_mcp()` (how
schemas are obtained) and `_run_tool()` (how a call is dispatched). The loop
itself never knows which mode is active.

This abstraction is Module 3's teaching point: if you can swap the tool
backend without changing the loop, you can also add new tools at runtime
without restarting anything.

---

## The authorization gap

Here is the question the agent loop never asks: *who authorized this tool call?*

The model decides to call `query_employees`. The loop executes it. There is no
check that the user actually intended that specific query with those specific
arguments. The model's judgment — which can be manipulated — is the sole
authorization mechanism.

In a conventional application, you would not let user input construct a database
query directly. You would validate and sanitise. The agent loop, in its basic
form, does not. That gap — between what the user intended and what the model
decided to do — is the entire subject of Module 4.

---

## Quick reference

### Agent loop state machine

```
START → [LLM call] → finish_reason?
                       ├─ tool_calls → execute tools → append results → [LLM call again]
                       ├─ stop → return answer
                       └─ (MAX_ITERATIONS reached) → return error
```

### Key endpoints (agent)

| Endpoint | Method | Returns |
|----------|--------|---------|
| `/health` | GET | `tool_mode`, `model`, `transparency` |
| `/chat` | POST | Answer, trace, session_id |
| `/tools` | GET | Current tool list (name, description, parameters) |
| `/tools/refresh` | POST | Re-discovers tools from MCP; no-op in hardcoded mode |
| `/logs` | GET | Full audit log |
| `/outbox` | GET | Messages queued by `send_message` |

### Environment variables (agent)

| Variable | Default | Effect |
|----------|---------|--------|
| `TOOL_MODE` | `hardcoded` | `hardcoded` or `mcp` |
| `TRANSPARENCY` | `verbose` | Controls whether audit log is surfaced in UI |
| `OPENAI_BASE_URL` | `http://ollama:11434/v1` | LLM endpoint — change for Day 2 |
| `MODEL` | `qwen2.5:3b` | Model name passed to the API |
