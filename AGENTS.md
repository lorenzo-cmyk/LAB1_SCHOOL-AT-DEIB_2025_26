# Mininet-GUI

Lab tool: Vue 3 frontend + FastAPI backend for interactive Mininet network emulation.

## Project layout

- `mininet-gui-frontend/` — Vue 3 SPA (Vite, Tailwind CSS v4, vis-network for topology graph)
- `mininet-gui-backend/` — FastAPI app (Python, Mininet integration, WebSocket terminals)
- `scripts/` — `setup.sh` (install deps), `run.sh` (start both), `stop.sh` (kill processes), `mininet-gui` (symlink-safe wrapper: `mininet-gui run|stop|setup`)
- `utils/webserver-ttl/` — TTL-gated HTTP challenge server (Go, port 2000)
- `utils/controller/` — FlowManager SDN controller with custom OS-Ken app, run scripts, setup

## Key commands

```bash
# Frontend
cd mininet-gui-frontend
npm install          # first time only (needs Node 20+ via nvm)
npx vite dev         # dev server on :4020
npx vite build       # production build
npx prettier --write . # format

# Backend (uses venv created by setup.sh)
cd mininet-gui-backend
source .venv/bin/activate
pip install -r requirements.txt
uvicorn mininet_gui_backend.api:app --host=0.0.0.0 --port=4021

# Or just use the wrapper:
./scripts/mininet-gui run     # kills old processes, starts backend + frontend
./scripts/mininet-gui stop    # kills all mininet-gui processes
./scripts/mininet-gui setup   # install system deps, venv, Node, frontend

# webserver-ttl (CTF challenge utility)
cd utils/webserver-ttl
go build -o webserver-ttl .   # needs golang-go from apt
sudo ./test.sh                 # integration tests (requires root)

# SDN controller (FlowManager submodule)
cd utils/controller
git submodule update --init     # clone flowmanager on first use
./setup.sh                      # create venv + install deps
./run-flowmanager.sh            # flowmanager web UI on :8080
./run-sdn-controller.sh         # flowmanager + sdn-controller.py on :8080
```

## Linting

```bash
# Python (pylint installed in venv)
cd mininet-gui-backend
.venv/bin/pylint mininet_gui_backend/

# JavaScript
cd mininet-gui-frontend
npx eslint --rule 'no-unused-vars: warn' --no-config-lookup src/core/*.js src/i18n/*.js src/main.js
```

## Desktop shortcut

Copy `scripts/mininet-gui.desktop` to `~/.local/share/applications/` (edit the `Exec` path to match your install location):

```bash
cp scripts/mininet-gui.desktop ~/.local/share/applications/mininet-gui.desktop
sed -i "s|/opt/mininet-gui|$PWD|g" ~/.local/share/applications/mininet-gui.desktop
```

Opens a terminal, runs `mininet-gui run`, and waits for Enter before closing.


## Auto-start on boot (systemd)

Copy `scripts/mininet-gui.service` to `/etc/systemd/system/` (edit path if needed), then enable:

```bash
sudo cp scripts/mininet-gui.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now mininet-gui
```

Runs as root — no sudo prompts, surviving reboots. `ExecStop` calls the stop script.

## Architecture

- Frontend communicates with backend via HTTP REST (`src/core/api.js`) and WebSockets (terminal, sniffer, monitoring)
- All network state lives in backend `app_state.py` module-level dicts (no DB)
- Topology graph rendered by vis-network; `NetworkGraph.vue` orchestrates the graph, with `Side.vue` (sidebar), `NodeStats.vue` (node details), `PingallResults.vue`, and other components handling specific UI areas
- i18n: single `en.json` locale file, used via vue-i18n

## Node types supported

Hosts, Switches (ovskernel), Controllers (default/remote). NAT, Router, special switches (OVS, User, OVSBridge), Ryu, and NOX are not supported.

## Gotchas

- `run.sh` runs backend with `sudo nohup` using `.venv/bin/uvicorn` — changes to backend require restart
- Frontend proxies nothing — backend must be on `:4021`, frontend on `:4020`
- WebSocket endpoints (`/api/mininet/terminal/`, `/api/mininet/sniffer`, `/api/mininet/monitor`) require the Mininet network to be started first
- `pingFull()` has a 120s timeout; iperf has per-command `timeout` wrapping
- All processes run as root (required for Mininet/OVS)
- Port labels are always-on on edges (no toggle)
- Dark theme only (light theme was removed)
- Remote controllers: stopping the network will fail if the external controller process is still listening on its port. Stop the external controller manually before restarting.
- Webshell terminal PTY is fixed at 24×256 columns (not dynamically resized)
- `package-lock.json` is intentionally not tracked in git
- `vis.js` is a kept dependency despite being unused by source code
