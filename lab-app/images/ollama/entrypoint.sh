#!/bin/sh
# Start Ollama and pull the model on first boot if it isn't already cached.
set -e

MODEL="${OLLAMA_MODEL:-qwen2.5:3b}"

ollama serve &
SERVER_PID=$!

# Wait for the server to accept connections
echo "Waiting for ollama..."
until ollama list > /dev/null 2>&1; do
    sleep 2
done

# Pull only if the model isn't already in the cache
if ! ollama list | grep -q "$MODEL"; then
    echo "Pulling $MODEL — this takes a few minutes on first run..."
    ollama pull "$MODEL"
    echo "Pull complete."
fi

echo "Model ready: $MODEL"
wait "$SERVER_PID"
