#!/bin/bash
set -euo pipefail

MININET_GUI_DIR="$(cd "$(dirname "$0")/.." && pwd)"
BACKEND_DIR="$MININET_GUI_DIR/mininet-gui-backend"
FRONTEND_DIR="$MININET_GUI_DIR/mininet-gui-frontend"

export MININET_GUI_ADDRESS="$(hostname -I | awk '{print $1}')"

# ---- cleanup previous runs ----
echo "Stopping previous processes..."
sudo pkill -9 -f "uvicorn|mininet_gui_backend.api" || true
sudo pkill -9 -f "npm run dev|vite" || true
sudo pkill -9 -f "tshark|dumpcap" || true
sudo pkill -9 -f "ryu-manager|ryu run" || true
sudo pkill -9 -f "mnexec" || true
sudo pkill -9 -f "mininet:" || true
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
(cd "$BACKEND_DIR" && sudo nohup uvicorn mininet_gui_backend.api:app --host=0.0.0.0 --port=8000 --log-level debug &)

# wait for backend to be ready
echo "Waiting for backend..."
for i in $(seq 1 30); do
  if curl -sf http://127.0.0.1:8000/api/health >/dev/null 2>&1; then
    echo "✔ Backend ready"
    break
  fi
  if [ "$i" -eq 30 ]; then
    echo "✘ Backend failed to start within 30 seconds"
    exit 1
  fi
  sleep 1
done

# ---- start frontend ----
echo "VITE_BACKEND_URL=http://$MININET_GUI_ADDRESS:8000" > "$FRONTEND_DIR/.env"
echo "VITE_BACKEND_WS_URL=ws://$MININET_GUI_ADDRESS:8000" >> "$FRONTEND_DIR/.env"

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
  nvm use 18 2>/dev/null || true
  nohup npm run dev -- --host 0.0.0.0 &
)

# ---- done ----
echo ""
echo "Mininet-GUI is available at: http://$MININET_GUI_ADDRESS:5173"
