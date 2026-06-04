# SDN Controller

FlowManager-based SDN controller with a custom OS-Ken application.

## Structure

```
controller/
├── flowmanager/          # git submodule (martimy/flowmanager)
├── examples/
│   └── sdn-controller.py # custom L2 learning switch with ARP proxy and TTL gate
├── run-flowmanager.sh    # starts flowmanager web UI on :8080
├── run-sdn-controller.sh # starts flowmanager + sdn-controller.py on :8080
└── setup.sh              # creates the Python venv and installs dependencies
```

## Setup

```bash
git submodule update --init   # clone flowmanager
./setup.sh                    # create venv + install deps
```

## Usage

```bash
# FlowManager web UI only
./run-flowmanager.sh

# FlowManager + custom SDN controller application
./run-sdn-controller.sh
```

Both scripts use `--observe-links` so the controller monitors link events. The web UI is available at `http://localhost:8080`.

### SDN Controller Application

`examples/sdn-controller.py` is an OS-Ken application implementing:
- **L2 learning switch** — learns MAC-to-port mappings and installs forwarding rules
- **ARP proxy** — responds to ARP requests for known hosts
- **TTL gate** — sets IP TTL to 100 on all forwarded packets, enabling interaction with the `webserver-ttl` challenge
