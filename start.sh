#!/usr/bin/env bash
# start.sh — Launch both the FastAPI backend and Next.js frontend in one go.
# Usage: ./start.sh
# Stop: Ctrl+C kills both processes cleanly.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
FRONTEND_DIR="$REPO_ROOT/frontend"

# Colour helpers
GREEN='\033[0;32m'
CYAN='\033[0;36m'
YELLOW='\033[1;33m'
RESET='\033[0m'

echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${RESET}"
echo -e "${CYAN}  VoiceChess — starting backend + frontend${RESET}"
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${RESET}"

# ── Preflight checks ─────────────────────────────────────────────────────────

if ! command -v python3 &>/dev/null; then
  echo "Error: python3 not found." >&2; exit 1
fi

if ! python3 -c "import fastapi" &>/dev/null; then
  echo -e "${YELLOW}Installing server dependencies…${RESET}"
  pip install -r "$REPO_ROOT/requirements-server.txt" -q
fi

if [ ! -d "$FRONTEND_DIR/node_modules" ]; then
  echo -e "${YELLOW}Installing frontend npm dependencies…${RESET}"
  npm install --prefix "$FRONTEND_DIR" --silent
fi

# ── Process management ───────────────────────────────────────────────────────

# Store child PIDs so the trap can kill both on Ctrl+C
BACKEND_PID=""
FRONTEND_PID=""

cleanup() {
  echo -e "\n${YELLOW}Shutting down…${RESET}"
  [[ -n "$BACKEND_PID"  ]] && kill "$BACKEND_PID"  2>/dev/null || true
  [[ -n "$FRONTEND_PID" ]] && kill "$FRONTEND_PID" 2>/dev/null || true
  wait 2>/dev/null || true
  echo -e "${GREEN}Done.${RESET}"
}
trap cleanup INT TERM EXIT

# ── Start backend ─────────────────────────────────────────────────────────────

echo -e "\n${GREEN}▶ Backend${RESET}  →  http://localhost:8000  (WS: ws://localhost:8000/ws/game)"
python3 "$REPO_ROOT/backend/server.py" &
BACKEND_PID=$!

# Give the server a moment to bind before the frontend tries to connect
sleep 1

# ── Start frontend ────────────────────────────────────────────────────────────

echo -e "${GREEN}▶ Frontend${RESET} →  http://localhost:3000"
npm run dev --prefix "$FRONTEND_DIR" &
FRONTEND_PID=$!

echo -e "\n${CYAN}Both services running. Press Ctrl+C to stop.${RESET}\n"

# Wait for either process to exit (e.g. crash), then trigger cleanup
wait "$BACKEND_PID" "$FRONTEND_PID"
