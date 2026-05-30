#!/bin/bash
set -euo pipefail

# ---- system packages ----
sudo apt-get update
sudo apt-get install -y \
    build-essential \
    curl \
    ethtool \
    git \
    iperf \
    iproute2 \
    iputils-ping \
    mininet \
    net-tools \
    openvswitch-switch \
    openvswitch-testcontroller \
    telnet \
    tshark

# ---- ovs-controller symlinks ----
sudo ln -sf /usr/bin/ovs-testcontroller /usr/local/bin/controller
sudo ln -sf /usr/bin/ovs-testcontroller /usr/local/bin/ovs-controller
sudo ln -sf /usr/bin/ovs-testcontroller /usr/local/bin/test-controller
sudo ln -sf /usr/bin/ovs-testcontroller /usr/local/bin/ovs-testcontroller

# ---- Python backend ----
MININET_GUI_DIR="$(cd "$(dirname "$0")/.." && pwd)"
BACKEND_DIR="$MININET_GUI_DIR/mininet-gui-backend"
FRONTEND_DIR="$MININET_GUI_DIR/mininet-gui-frontend"

echo "Installing backend Python deps"
sudo python3 -m pip install --break-system-packages --no-cache-dir -r "$BACKEND_DIR/requirements.txt"

# ---- Node / nvm ----
if [ ! -s "$HOME/.nvm/nvm.sh" ]; then
  echo "Installing nvm"
  curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.40.2/install.sh | bash
fi
export NVM_DIR="$HOME/.nvm"
[ -s "$NVM_DIR/nvm.sh" ] && . "$NVM_DIR/nvm.sh"

echo "Installing Node 18"
nvm install 18

# ---- Frontend ----
echo "Installing frontend deps"
(cd "$FRONTEND_DIR" && npm install)

# ---- Alias ----
if ! grep -q "alias mininet_gui=" "$HOME/.bashrc" 2>/dev/null; then
    echo "alias mininet_gui=$MININET_GUI_DIR/scripts/run.sh" >> "$HOME/.bashrc"
fi

echo ""
echo "Setup complete. Run with: mininet_gui (or scripts/run.sh)"
