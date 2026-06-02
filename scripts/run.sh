#!/bin/bash
set -euo pipefail

MININET_GUI_DIR="$(cd "$(dirname "$0")/.." && pwd)"
BACKEND_DIR="$MININET_GUI_DIR/mininet-gui-backend"
FRONTEND_DIR="$MININET_GUI_DIR/mininet-gui-frontend"

restore_terminal() {
  stty sane 2>/dev/null || true
}
trap restore_terminal EXIT

# ---- cleanup previous runs ----
echo "Stopping previous processes..."
sudo pkill -9 -f "uvicorn mininet_gui_backend" 2>/dev/null || true
sudo pkill -9 -f "vite.*mininet-gui" 2>/dev/null || true
sudo pkill -9 -f "tshark" 2>/dev/null || true
sudo pkill -9 -f "ryu" 2>/dev/null || true
sudo pkill -9 -f "mnexec" 2>/dev/null || true
sudo mn -c >/dev/null 2>&1 || true

# ---- trim logs ----
BACKEND_LOG_FILE="$BACKEND_DIR/mininet_gui_backend/mininet.log"

trim_log() {
  local file="$1"
  if [ -f "$file" ]; then
    sudo tail -n 10000 "$file" > "${file}.tmp"
    mv -f "${file}.tmp" "$file"
  fi
}

trim_log "$BACKEND_DIR/nohup.out"
trim_log "$FRONTEND_DIR/nohup.out"

if [ -f "$BACKEND_LOG_FILE" ]; then
  sudo truncate -s 0 "$BACKEND_LOG_FILE"
  echo "✔ Cleared backend log file"
fi

# ---- start backend ----
echo "Starting backend..."
(cd "$BACKEND_DIR" && sudo nohup uvicorn mininet_gui_backend.api:app --host=0.0.0.0 --port=4021 --log-level debug > /dev/null 2>&1 &)
sleep 3

if ! pgrep -f "uvicorn mininet_gui_backend" >/dev/null 2>&1; then
  echo "✘ Backend process not found. Check:"
  tail -30 "$BACKEND_DIR/nohup.out" 2>/dev/null || true
  exit 1
fi

# wait for backend to be ready
echo "Waiting for backend..."
for i in $(seq 1 30); do
  if curl -s http://127.0.0.1:4021/api/health 2>/dev/null | grep -q '"status"'; then
    echo "✔ Backend ready"
    break
  fi
  if [ "$i" -eq 30 ]; then
    echo "✘ Backend failed to start within 30 seconds"
    echo "  Check: $BACKEND_DIR/nohup.out"
    tail -30 "$BACKEND_DIR/nohup.out" 2>/dev/null || true
    exit 1
  fi
  sleep 1
done

# ---- start frontend ----
echo "Starting frontend..."
(
  cd "$FRONTEND_DIR"
  if [ -s "$HOME/.nvm/nvm.sh" ]; then
    export NVM_DIR="$HOME/.nvm"
    . "$NVM_DIR/nvm.sh"
  elif [ -s "$HOME/.config/nvm/nvm.sh" ]; then
    export NVM_DIR="$HOME/.config/nvm"
    . "$NVM_DIR/nvm.sh"
  elif [ -s "/usr/share/nvm/nvm.sh" ]; then
    export NVM_DIR="/usr/share/nvm"
    . "$NVM_DIR/nvm.sh"
  fi
  nvm use 20 2>/dev/null || true
  nohup npm run dev -- --host 0.0.0.0 --port 4020 &
)

# ---- done ----
stty sane 2>/dev/null || true
ALL_IPS="$(hostname -I)"
echo ""
echo "Mininet-GUI is available at:"
for ip in $ALL_IPS; do
  echo "  http://$ip:4020"
done
