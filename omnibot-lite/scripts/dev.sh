#!/usr/bin/env bash
# Dev local : backend uvicorn:8080 + frontend vite:5173 (proxy API/WS).
# Env : OMNIBOT_LLM_BASE_URL / OMNIBOT_LLM_MODEL / OMNIBOT_LLM_API_KEY (voir .env.example)
set -e
cd "$(dirname "$0")/.."

[ -d backend/.venv ] || (cd backend && python3 -m venv .venv && .venv/bin/pip install -q -r requirements.txt)
[ -d frontend/node_modules ] || (cd frontend && npm install --no-audit --no-fund)

(cd backend && .venv/bin/uvicorn app:app --host 127.0.0.1 --port "${OMNIBOT_PORT:-8080}" --reload) &
BACK=$!
trap "kill $BACK 2>/dev/null || true" EXIT

(cd frontend && npm run dev)
