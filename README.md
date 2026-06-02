# Mininet-GUI

A web-based interface to design and run Mininet experiments through an interactive topology graph.

Add and configure hosts, switches, controllers, and links, start/stop the emulation, and modify the topology during execution. Includes WebShell node terminals, OpenFlow flow-rule manager, packet sniffer, and real-time traffic charts.

Fork of [latarc/mininet-gui](https://github.com/latarc/mininet-gui).

## Installation

Tested on Ubuntu 22.04+. Requires Node 20+ (installed automatically by `setup.sh` via nvm).

```bash
git clone https://github.com/lorenzo-cmyk/mininet-gui
cd mininet-gui
./scripts/setup.sh
```

Then start with:

```bash
mininet_gui
```

Open `http://<host-ip>:4020` in a browser.

## Quick test

1. Drag a "Controller" from the sidebar to the canvas, choose "Default".
2. Click "Generate Topology", select "Single", set "Hosts" to 2, submit.
3. Click "Run Pingall Test" on the sidebar and wait for results.

## Changes from upstream

### UI overhaul

- **Simplified toolbar** — Removed the Help menu, Tools menu, and Settings menu from the toolbar. Run actions (start/stop/restart network) moved to the sidebar as an always-visible action group. The sidebar is now organized into three sections: Network, Testing, and Topology.
- **Dark theme only** — Removed the light theme entirely. All CSS variables, SVG icon sets, and theme-switching logic are gone. The app is dark-only.
- **Port labels always on** — Edge labels showing interface names (e.g. `s1-eth1 ↔ h1-0`) are rendered directly on links at all times. No toggle — they're always visible.
- **Reorganized sidebar** — The node palette now shows only Host, Switch, Controller, and Remote Controller. The action area is split into Network (start/stop/restart), Testing (pingall, iperf), and Topology (generate, connect, delete).
- **Export PCAP moved** — The PCAP export button moved from the File menu to the Sniffer tab toolbar, only enabled while sniffing is active.

### Removed features

- **Node types stripped** — Removed NAT, Router, OVS/User/OVSBridge switches, Ryu controllers, and NOX controllers. Only Host, Switch (ovskernel), Controller (default/remote) remain.
- **Link options removed** — The ability to set bandwidth, delay, jitter, loss, or HTB on links has been removed. Links are created with default settings only. The `PUT /api/mininet/links` endpoint and `LinkOptions`/`LinkUpdate` models were removed from the backend.
- **Export features removed** — Export Topology as PNG, Export Topology as Mininet Script, Export Addressing Plan (PDF), and Export Charts from the monitoring tab were all removed.
- **Help menu removed** — The Usage modal (welcome, shortcuts, devices tabs), About modal, and Open Documentation link are gone.
- **OpenFlow version selector removed** — Switches always use OpenFlow 1.3. The settings selector and per-switch editing were removed.
- **Color picker removed** — Controller color customization was removed. All controllers use the default white icon.
- **Default route editing removed** — Host node stats no longer allow editing the default route. The display is kept but editing was removed.
- **Port label toggle removed** — The "Show port labels" checkbox in the View menu was removed since labels are now always on.
- **Show Hosts/Controllers toggle removed** — The visibility toggles in the View menu were non-functional and removed.
- **Default route editing on hosts removed** — The route type selector, interface selector, and gateway IP input were removed from the host edit form. Only IP editing remains.
- **Switch node stats** — Displays switch type, port count, associated controller, and raw `dump-flows` output with a Refresh button. Flow table is only available when the network is started.

### Stability fixes

- **Iperf hanging** — Replaced Mininet's `iperf()` with a custom implementation using `sendCmd`/`monitor`. Added OS-level `timeout` wrapping and `asyncio.TimeoutError` catch with 504 responses.
- **Pingall hanging** — Added 120-second hard timeout via `asyncio.wait_for` + `asyncio.to_thread` on the blocking `pingFull()` call.
- **Webshell terminal corruption** — Added `stty sane` trap to shell scripts. Set PTY terminal size (80x24) via `TIOCSWINSZ` ioctl to fix line wrapping.
- **Sniffer stability** — Fixed pyshark broken mapping loader, added dynamic tshark version detection, improved error logging for tshark stderr.
- **Stale links on node deletion** — When a node is deleted, all associated links are now cleaned up from `state.links` and `state.link_attrs`, preventing "link already exists" errors when reusing node IDs.
- **Port label rendering** — Added dark background and stroke to edge labels for readability. Fixed stale font styling when toggling off by setting `font: null` and `title: null` on updates.
- **Frontend bug fixes** — Fixed modal hang on close, WebSocket stale references, `deleteEdge` freeze, throw-outside-catch errors, race conditions, and memory leaks. Fixed `sniffer_manager` stale state after network stop/reset.

### Infrastructure

- **Scripts rewritten** — `run.sh` and `stop.sh` rewritten with `echo` (replacing `printf`), `stty sane` terminal reset, process health checks, and proper error reporting. `setup.sh` installs from apt instead of building from source.
- **Backend decomposed** — Monolithic `api.py` split into `api_helpers.py` (models, utilities), `app_state.py` (state), `export.py` (script/JSON export), `schema.py` (Pydantic models), `routers/` (WebSocket handlers).
- **Frontend decomposed** — Monolithic `NetworkGraph.vue` refactored; components like `Side.vue`, `Webshell.vue`, `Modal.vue`, `Topbar.vue`, `MonitoringView.vue`, `TrafficView.vue` are well-scoped.
- **Docker removed** — Docker support was dropped in favor of native `setup.sh` + `run.sh`.
- **Fonts bundled locally** — Replaced Google Fonts CDN loading with local `.woff2` files for offline use.
- **Portuguese i18n removed** — Only English locale remains.
- **Dead code cleanup** — Removed LLM chat feature, unused examples, redundant docs, unused Python imports, `console.log` debug statements, and `print()` statements.
- **Naming standardized** — IPerf, WebShell, Default Route, OpenFlow, etc. capitalized correctly across all UI strings.

### Backend changes

- **Iperf endpoint** — `POST /api/mininet/iperf` with synchronous execution, per-command timeout, and proper busy-state cleanup.
- **Pingall endpoint** — `POST /api/mininet/pingall` with 120-second timeout, host shell state reset in `finally` block.
- **Node deletion** — Cleans up associated links from `state.links` and `state.link_attrs` before removing the node.
- **Link creation simplified** — `POST /api/mininet/links` no longer accepts options. `PUT /api/mininet/links` endpoint removed entirely.
- **Ryu/NOX endpoints removed** — `/api/ryu/apps` removed along with `list_ryu_apps()`, `LinuxRouter`, `Ryu` node class, and all special switch/controller creation logic.
- **`import_json` fixed** — Returns proper `HTTPException` instead of Flask-style tuple.
- **`debug=True` kept** — Intentionally left on for lab use.

## License

BSD 3-Clause License
