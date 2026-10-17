#!/usr/bin/env bash
set -euo pipefail
echo "Start backend in terminal 1: cd backend && python -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt && uvicorn app.main:app --reload --port 8000"
echo "Start frontend in terminal 2: cd frontend && npm install && npm run dev"
