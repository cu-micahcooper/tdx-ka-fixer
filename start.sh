#!/bin/bash
# TDX KA Tuna — start backend and frontend in separate terminal tabs

REPO="$(cd "$(dirname "$0")" && pwd)"

# Kill any stale servers
lsof -ti :8000 -ti :5173 | xargs kill -9 2>/dev/null

# Ensure DB schema is up to date (safe to run repeatedly)
source "$REPO/backend/.venv/bin/activate"
(cd "$REPO/backend" && python -c "from database import engine; from models import Base; Base.metadata.create_all(engine)")

# Backend
osascript -e "
  tell application \"Terminal\"
    do script \"cd '$REPO/backend' && source .venv/bin/activate && uvicorn main:app --reload\"
  end tell
"

# Frontend
osascript -e "
  tell application \"Terminal\"
    do script \"cd '$REPO/frontend' && npm run dev\"
  end tell
"

echo "Starting TDX KA Tuna..."
echo "  Backend → http://localhost:8000"
echo "  Frontend → http://localhost:5173"
