---
title: "Docker Compose Setup"
linkTitle: "Docker Compose"
weight: 1
---

## Prerequisites

| Requirement | Version | Check |
|-------------|---------|-------|
| Docker Engine | 24+ | `docker version` |
| Docker Compose | v2.20+ | `docker compose version` |
| Git | any | `git --version` |
| Free RAM | 8 GB | — |
| Free disk | 5 GB | for model cache |

{{% notice style="note" title="GPU optional" %}}
A discrete GPU (NVIDIA or Apple Silicon) cuts model load time from ~60 s to
~5 s and speeds inference significantly. The labs work without one — first
responses will just be slower.
{{% /notice %}}

## 1. Clone the repo

```bash
git clone https://github.com/FortinetCloudCSE/ai-101.git
cd ai-101
```

## 2. Pull the model

The first start downloads `qwen2.5:3b` (~2 GB). Do this now to avoid waiting
during the lab:

```bash
cd lab-app/compose
docker compose --profile lab1 up -d
docker compose logs -f ollama
```

Wait until you see a line containing `pull complete` or `success`. Then stop
following the logs with `Ctrl+C`. The model is cached in the `ollama-data`
Docker volume for all subsequent runs.

## 3. Verify

```bash
curl -s http://localhost:11434/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model":"qwen2.5:3b","messages":[{"role":"user","content":"ping"}]}' \
  | jq -r '.choices[0].message.content'
```

Expected: a short reply from the model (exact text varies).

## 4. Reference — start/stop per lab

```bash
cd lab-app/compose

# Lab 1 — Ollama only
docker compose --profile lab1 up -d
docker compose --profile lab1 down

# Lab 2 — Agent + UI (brings Ollama along)
docker compose --profile lab2 up -d

# Lab 3 — MCP server + Agent (MCP mode) + UI
docker compose --profile lab3 up -d

# Lab 4 — Same as lab3, different env vars applied by the lab steps
docker compose --profile lab4 up -d
```

To check running services:
```bash
docker compose ps
```

To tail all logs:
```bash
docker compose logs -f
```

{{% notice style="tip" title="Keep it running" %}}
Leave the stack running as you work through the labs. Each lab section tells you which profile to switch to. Only stop the stack when you are completely done.
{{% /notice %}}

## 5. Cleanup (after the workshop)

```bash
cd lab-app/compose
docker compose --profile lab4 down
docker volume rm compose_ollama-data
```
