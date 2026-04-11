#!/usr/bin/env bash
set -euo pipefail

DEV_ROOT="/opt/manim-dev"
BACKEND_DIR="$DEV_ROOT/backend"
LOG_DIR="$DEV_ROOT/logs"
PID_FILE="$LOG_DIR/backend.pid"
PYTHON_BIN="$BACKEND_DIR/venv/bin/python"
PORT="8001"

mkdir -p "$LOG_DIR"

if [[ -f "$PID_FILE" ]]; then
  OLD_PID="$(cat "$PID_FILE" || true)"
  if [[ -n "$OLD_PID" ]] && kill -0 "$OLD_PID" 2>/dev/null; then
    kill "$OLD_PID" || true
    sleep 2
  fi
fi

pkill -f "uvicorn app.main:app --host 0.0.0.0 --port $PORT" 2>/dev/null || true

cd "$BACKEND_DIR"
nohup "$PYTHON_BIN" -m uvicorn app.main:app --host 0.0.0.0 --port "$PORT" > "$LOG_DIR/backend.log" 2>&1 &
NEW_PID=$!
echo "$NEW_PID" > "$PID_FILE"

for _ in {1..20}; do
  if curl -fsS "http://127.0.0.1:$PORT/health" >/dev/null 2>&1; then
    echo "backend_ok pid=$NEW_PID port=$PORT"
    exit 0
  fi
  sleep 1
done

echo "backend_failed pid=$NEW_PID port=$PORT" >&2
tail -50 "$LOG_DIR/backend.log" >&2 || true
exit 1
