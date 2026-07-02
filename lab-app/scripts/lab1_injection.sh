#!/usr/bin/env bash
# Lab 1 — Prompt injection against the system instruction
#
# Step 1: direct ask is refused.
# Step 2: the injection bypasses that protection.
#
# Save the output — you'll replay this on Day 2 through FortiAIGate.
#
# Usage:
#   ./lab1_injection.sh
#   OPENAI_BASE_URL=https://your-fortiaigate-host/v1 ./lab1_injection.sh

OPENAI_BASE_URL="${OPENAI_BASE_URL:-http://localhost:11434/v1}"
MODEL="${MODEL:-qwen2.5:3b}"

python3 "$(dirname "$0")/_lab1_common.py" injection \
  --url "$OPENAI_BASE_URL" --model "$MODEL"
