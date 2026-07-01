#!/usr/bin/env bash
# Lab 1 — Raw inference via the OpenAI-compatible API
#
# Usage:
#   ./lab1_inference.sh
#   OPENAI_BASE_URL=https://your-fortiaigate-host/v1 ./lab1_inference.sh

OPENAI_BASE_URL="${OPENAI_BASE_URL:-http://localhost:11434/v1}"
MODEL="${MODEL:-qwen2.5:3b}"

python3 "$(dirname "$0")/_lab1_common.py" inference \
  --url "$OPENAI_BASE_URL" --model "$MODEL"
