#!/bin/sh
set -eu
# Fargate CPU-only Ollama server. The /models directory MUST be an EFS volume.
ollama serve &
server_pid=$!
trap 'kill "$server_pid" 2>/dev/null || true' TERM INT
n=0
until ollama list >/dev/null 2>&1; do
  n=$((n + 1))
  if [ "$n" -gt 90 ]; then
    echo 'Ollama did not become ready' >&2
    exit 1
  fi
  sleep 2
done
# First start downloads the model to EFS. Later deployments reuse it.
if ! ollama show "$OLLAMA_MODEL" >/dev/null 2>&1; then
  echo "Ollama model not present; downloading $OLLAMA_MODEL to EFS"
  ollama pull "$OLLAMA_MODEL"
fi
wait "$server_pid"
