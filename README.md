# Mininet-GUI

A web-based interface to design and run Mininet experiments through an interactive topology graph.

Add and configure hosts, switches, controllers, and links, start/stop the emulation, and modify the topology during execution. Includes WebShell node terminals, OpenFlow flow-rule manager, packet sniffer, and real-time traffic charts.

Fork of [latarc/mininet-gui](https://github.com/latarc/mininet-gui).

## Installation

Tested on Ubuntu 20.04.

```bash
git clone https://github.com/lorenzo-cmyk/mininet-gui
cd mininet-gui
./scripts/setup.sh
```

Then start with:

```bash
mininet_gui
```

Open `http://<host-ip>:5173` in a browser.

## Quick test

1. Drag a "Controller" from the sidebar to the canvas, choose "Default".
2. Click "Generate Topology", select "Single", set "Hosts" to 2, submit.
3. Click "Run Pingall Test" on the sidebar and wait for results.

## License

BSD 3-Clause License
