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
| `mnexec`      | built from Mininet source |
| `tail`        | `coreutils` (pre-installed) |
| `which`       | `debianutils` (pre-installed) |
| `ryu`         | `ryu` (pip, optional)     |
| `ryu-manager` | `ryu` (pip, optional)     |

## Per-section detail

### Networking

| Command   | Used for                                           |
| --------- | -------------------------------------------------- |
| `ip`      | route and interface management on hosts/routers    |
| `arp`     | ARP table queries on hosts                         |
| `ping`    | ping tests (called via Mininet's `pingFull`)       |
| `iperf`   | bandwidth tests (called via Mininet's `net.iperf`) |
| `netstat` | port scanning (find free controller ports)         |
| `telnet`  | controller port probing (Ryu)                      |
| `sysctl`  | enable/disable IP forwarding on routers            |

### Open vSwitch

| Command           | Used for                                        |
| ----------------- | ----------------------------------------------- |
| `ovs-vsctl`       | OVS bridge configuration (OpenFlow version)     |
| `ovs-ofctl`       | OpenFlow flow rule management (add/dump/delete) |
| `ovs-testcontroller` | default controller for OVS switches          |

### SDN Controllers (optional)

| Command       | Used for                            |
| ------------- | ----------------------------------- |
| `ryu`         | Ryu controller node support         |
| `ryu-manager` | discover available Ryu applications |

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
| `kill`      | stop Ryu controller processes            |
