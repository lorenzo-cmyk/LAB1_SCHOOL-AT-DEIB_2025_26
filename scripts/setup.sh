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
    tshark \
    python3-pip \
    python3-venv

# ---- ovs-controller symlinks ----
sudo ln -sf /usr/bin/ovs-testcontroller /usr/local/bin/controller
sudo ln -sf /usr/bin/ovs-testcontroller /usr/local/bin/ovs-controller
sudo ln -sf /usr/bin/ovs-testcontroller /usr/local/bin/test-controller
sudo ln -sf /usr/bin/ovs-testcontroller /usr/local/bin/ovs-testcontroller

# ---- Python backend ----
MININET_GUI_DIR="$(cd "$(dirname "$0")/.." && pwd)"
BACKEND_DIR="$MININET_GUI_DIR/mininet-gui-backend"
FRONTEND_DIR="$MININET_GUI_DIR/mininet-gui-frontend"
VENV_DIR="$BACKEND_DIR/.venv"

if [ ! -d "$VENV_DIR" ]; then
  echo "Creating Python virtual environment for backend..."
  python3 -m venv "$VENV_DIR"
fi

echo "Installing backend Python deps"
"$VENV_DIR/bin/pip" install --no-cache-dir -r "$BACKEND_DIR/requirements.txt"

# ---- Node / nvm ----
if [ -s "$HOME/.nvm/nvm.sh" ]; then
  export NVM_DIR="$HOME/.nvm"
elif [ -s "$HOME/.config/nvm/nvm.sh" ]; then
  export NVM_DIR="$HOME/.config/nvm"
else
  echo "Installing nvm"
  curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.40.2/install.sh | bash
  if [ -s "$HOME/.nvm/nvm.sh" ]; then
    export NVM_DIR="$HOME/.nvm"
  elif [ -s "$HOME/.config/nvm/nvm.sh" ]; then
    export NVM_DIR="$HOME/.config/nvm"
  else
    echo "nvm install failed"
    exit 1
  fi
fi
. "$NVM_DIR/nvm.sh"

echo "Installing Node 20"
nvm install 20

# ---- Frontend ----
echo "Installing frontend deps"
(cd "$FRONTEND_DIR" && npm install)

# ---- Alias ----
if ! grep -q "alias mininet_gui=" "$HOME/.bashrc" 2>/dev/null; then
    echo "alias mininet_gui=$MININET_GUI_DIR/scripts/mininet-gui" >> "$HOME/.bashrc"
fi

echo ""
echo "Setup complete. Run with: mininet_gui (or scripts/mininet-gui)"
