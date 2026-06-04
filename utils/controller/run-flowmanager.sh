#!/bin/bash
set -e

# Re-launch in a visible terminal when double-clicked from a file manager
if [ ! -t 0 ]; then
    xfce4-terminal --hold -e "$0"
    exit $?
fi

cd "$(dirname "$0")"
source .venv/bin/activate

echo "Starting FlowManager..."
python3 flowmanager/controller.py flowmanager/flowmanager.py &
CONTROLLER_PID=$!

echo "Waiting for server to be ready..."
for i in $(seq 1 30); do
    if curl -s -o /dev/null http://localhost:8080; then
        echo "Server is up."
        break
    fi
    sleep 1
done

firefox http://localhost:8080/home/index.html 2>/dev/null &

echo "Controller running (PID: $CONTROLLER_PID). Press Ctrl+C to stop."
trap 'kill $CONTROLLER_PID 2>/dev/null; echo "Stopped."' EXIT
wait $CONTROLLER_PID
