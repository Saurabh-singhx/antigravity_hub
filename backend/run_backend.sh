#!/bin/bash
# Starts the local Antigravity Hub Backend Relay
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$DIR"

if [ -d ".venv" ]; then
    source .venv/bin/activate
fi

export HUB_PORT=${HUB_PORT:-8765}
export HUB_HOST=${HUB_HOST:-0.0.0.0}

# Check if port is currently in use
PID_IN_USE=$(lsof -t -i :$HUB_PORT 2>/dev/null)
if [ ! -z "$PID_IN_USE" ]; then
    echo "⚠️  Port $HUB_PORT is currently occupied by PID $PID_IN_USE."
    echo "Killing stale process on port $HUB_PORT..."
    kill -9 $PID_IN_USE 2>/dev/null
    sleep 1
fi

echo "=========================================================="
echo "🚀 Starting Antigravity Hub Local Backend Relay"
echo "Listening on: http://0.0.0.0:$HUB_PORT"
echo "API Docs:     http://localhost:$HUB_PORT/docs"
echo "WebSocket:    ws://localhost:$HUB_PORT/ws/notifications"
echo "=========================================================="

python3 app.py
