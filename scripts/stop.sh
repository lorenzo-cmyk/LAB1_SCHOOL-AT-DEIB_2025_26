#!/bin/bash
set -euo pipefail

restore_terminal() {
  stty sane 2>/dev/null || true
}
trap restore_terminal EXIT

echo "Stopping Mininet-GUI processes..."
sudo pkill -9 -f "uvicorn mininet_gui_backend" 2>/dev/null || true
sudo pkill -9 -f "vite.*mininet-gui" 2>/dev/null || true
sudo pkill -9 -f "tshark" 2>/dev/null || true
sudo pkill -9 -f "ryu" 2>/dev/null || true
sudo pkill -9 -f "mnexec" 2>/dev/null || true
sudo mn -c >/dev/null 2>&1 || true

stty sane 2>/dev/null || true
echo "Stopped."
