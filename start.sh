#!/bin/bash
# TDX KA Tuna — start backend and frontend in separate terminal tabs

REPO="$(cd "$(dirname "$0")" && pwd)"

# Backend
osascript -e "
  tell application \"Terminal\"
    do script \"source '$REPO/backend/.venv/bin/activate' && uvicorn main:app --reload --app-dir '$REPO/backend'\"
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
