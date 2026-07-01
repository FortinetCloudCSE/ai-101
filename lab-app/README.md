# AI-101 Lab Application

Four-container stack for the AI-101 Day 1 workshop.

| Container    | Purpose                                     | Port  |
|-------------|---------------------------------------------|-------|
| `ollama`     | LLM inference (`qwen2.5:3b`)               | 11434 |
| `agent`      | FastAPI agent with explicit tool-call loop  | 8001  |
| `mcp-server` | FastMCP tool server (Lab 3+)               | 8000  |
| `ui`         | Chat UI (nginx, vanilla JS)                 | 8080  |

## Quick start

```bash
# Lab 1 — raw curl to Ollama
docker compose --profile m1 up -d

# Lab 2 — agent + hardcoded tools
docker compose --profile m2 up -d
# Open http://localhost:8080

# Lab 3 — MCP server (adds dynamic tool discovery)
docker compose --profile m3 up -d
# Add a third tool without rebuilding the agent:
ENABLE_EXTRA_TOOL=true docker compose --profile m3 up -d

# Lab 4 — security demo (enable poison tool desc for MCP poisoning demo)
POISON_DESC=true docker compose --profile m4 up -d
```

## Day 2 swap

Re-point the agent at FortiAIGate by overriding one variable:

```bash
OPENAI_BASE_URL=https://your-fortiaigate-host/v1 \
  docker compose --profile m4 up -d
```

No images are rebuilt. Everything else stays the same.

## Environment variables

| Variable          | Default                      | Description                         |
|-------------------|------------------------------|-------------------------------------|
| `OPENAI_BASE_URL` | `http://ollama:11434/v1`     | LLM endpoint — swap for Day 2       |
| `OLLAMA_MODEL`    | `qwen2.5:3b`                 | Model name                          |
| `TOOL_MODE`       | `hardcoded` / `mcp`          | Set by profile automatically        |
| `TRANSPARENCY`    | `verbose`                    | `quiet` hides audit log (Lab 4 demo)|
| `ENABLE_EXTRA_TOOL` | `false`                    | Exposes `search_web` via MCP        |
| `POISON_DESC`     | `false`                      | Enables poisoned tool description   |

## First boot

Ollama pulls `qwen2.5:3b` on first start (~2 GB). The first LLM response will
be slow while the model loads into memory. Subsequent calls are faster.
CPU-only hardware is supported; expect 30–90 seconds per response.
