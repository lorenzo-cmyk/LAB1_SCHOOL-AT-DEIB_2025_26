#!/bin/bash
set -euo pipefail

# Re-launch in a visible terminal when double-clicked from a file manager
if [ ! -t 0 ]; then
    for term in xfce4-terminal gnome-terminal x-terminal-emulator; do
        if command -v "$term" &>/dev/null; then
            exec "$term" --hold -e "$0"
        fi
    done
    echo "No terminal emulator found. Run this script from a terminal." >&2
    exit 1
fi

cd "$(dirname "$0")"

if [ ! -f .venv/bin/activate ]; then
    echo "Virtual environment not found." >&2
    echo "Run: python3 -m venv .venv && .venv/bin/pip install -r flowmanager/requirements.txt" >&2
    exit 1
fi
source .venv/bin/activate

echo "Starting controller with --observe-links..."
python3 flowmanager/controller.py --observe-links flowmanager/flowmanager.py examples/sdn-controller.py &
CONTROLLER_PID=$!
trap 'kill $CONTROLLER_PID 2>/dev/null; echo "Stopped."' EXIT

echo "Waiting for server to be ready..."
for i in $(seq 1 30); do
    if curl -s -o /dev/null http://localhost:8080; then
        echo "Server is up."
        break
    fi
    sleep 1
done

if command -v firefox &>/dev/null; then
    firefox http://localhost:8080/home/index.html 2>/dev/null &
fi

echo "Controller running (PID: $CONTROLLER_PID). Press Ctrl+C to stop."
wait $CONTROLLER_PID
