#!/usr/bin/env bash
# Démarre le faux LLM + le hub backend pour le smoke test.
set -e
cd "$(dirname "$0")/.."

export OMNIBOT_DATA_DIR="/tmp/opencode/omnibot-lite-test-data"
export OMNIBOT_LLM_BASE_URL="http://127.0.0.1:9999/v1"
export OMNIBOT_LLM_MODEL="fake-model"
rm -rf "$OMNIBOT_DATA_DIR"

backend/.venv/bin/python scripts/fake_llm_server.py 9999 &
FAKE_PID=$!
backend/.venv/bin/uvicorn --app-dir backend app:app --host 127.0.0.1 --port 8090 &
HUB_PID=$!
trap "kill $FAKE_PID $HUB_PID 2>/dev/null || true" EXIT

sleep 2
backend/.venv/bin/python scripts/smoke_test.py
