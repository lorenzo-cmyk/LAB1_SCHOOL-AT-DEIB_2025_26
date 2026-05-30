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
sudo pkill -9 -f "ryu" || true
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

# ---- start frontend ----
echo "VITE_BACKEND_URL=http://$MININET_GUI_ADDRESS:8000" > "$FRONTEND_DIR/.env"
echo "VITE_BACKEND_WS_URL=ws://$MININET_GUI_ADDRESS:8000" >> "$FRONTEND_DIR/.env"

echo "Starting frontend..."
(
  cd "$FRONTEND_DIR"
  if command -v nvm >/dev/null 2>&1; then
    nvm use 18
  elif [ -s "$HOME/.nvm/nvm.sh" ]; then
    . "$HOME/.nvm/nvm.sh"
    nvm use 18 || true
  elif [ -s "/usr/share/nvm/nvm.sh" ]; then
    . "/usr/share/nvm/nvm.sh"
    nvm use 18 || true
  fi
  nohup npm run dev -- --host 0.0.0.0 &
)

# ---- done ----
echo ""
echo "Mininet-GUI is available at: http://$MININET_GUI_ADDRESS:5173"
