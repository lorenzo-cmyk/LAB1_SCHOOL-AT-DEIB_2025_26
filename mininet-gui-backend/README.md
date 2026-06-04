# Backend runtime dependencies

The following executables must be available in `PATH` for the backend to
function correctly.

## Command → Ubuntu package mapping

| Command       | Ubuntu package            |
| ------------- | ------------------------- |
| `ip`          | `iproute2`                |
| `arp`         | `net-tools`               |
| `ping`        | `iputils-ping`            |
| `iperf`       | `iperf`                   |
| `netstat`     | `net-tools`               |
| `telnet`      | `telnet`                  |
| `sysctl`      | `procps` (pre-installed)  |
| `ovs-vsctl`   | `openvswitch-switch`      |
| `ovs-ofctl`   | `openvswitch-switch`      |
| `ovs-testcontroller` | `openvswitch-testcontroller` |
| `tshark`      | `tshark`                  |
| `mergecap`    | `tshark`                  |
| `mnexec`      | `mininet` (apt package)   |
| `tail`        | `coreutils` (pre-installed) |
| `which`       | `debianutils` (pre-installed) |

## Per-section detail

### Networking

| Command   | Used for                                           |
| --------- | -------------------------------------------------- |
| `ip`      | route and interface management on hosts            |
| `arp`     | ARP table queries on hosts                         |
| `ping`    | ping tests (called via Mininet's `pingFull`)       |
| `iperf`   | bandwidth tests (custom `_run_iperf` with per-command timeout) |
| `netstat` | port scanning (find free controller ports)         |
| `telnet`  | controller port probing                            |
| `sysctl`  | enable/disable IP forwarding                       |

### Open vSwitch

| Command           | Used for                                        |
| ----------------- | ----------------------------------------------- |
| `ovs-vsctl`       | OVS bridge configuration (OpenFlow version)     |
| `ovs-ofctl`       | OpenFlow flow rule management (add/dump/delete) |
| `ovs-testcontroller` | default controller for OVS switches          |

### Packet capture

| Command    | Used for                             |
| ---------- | ------------------------------------ |
| `tshark`   | live packet sniffing / PCAP export   |
| `mergecap` | merging multiple PCAP files into one |

### Mininet internal

| Command  | Used for                                        |
| -------- | ----------------------------------------------- |
| `mnexec` | execute commands inside node network namespaces |

### System (typically always present)

| Command     | Used for                                 |
| ----------- | ---------------------------------------- |
| `/bin/bash` | interactive terminal sessions (webshell) |
| `tail`      | log streaming over WebSocket             |
| `which`     | checks if telnet is installed            |
