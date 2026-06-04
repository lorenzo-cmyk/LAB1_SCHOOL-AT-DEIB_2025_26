# webserver-ttl

TTL-gated HTTP server — a CTF / lab challenge service.

## How it works

Listens on port 2000 and sniffs all network interfaces for incoming TCP SYN
packets. When a SYN is observed, the server records the **IP TTL** of the
packet. On the subsequent TCP connection, it checks the recorded TTL:

| TTL          | Response |
|--------------|----------|
| < 100        | `403 ACCESS_DENIED` |
| >= 100       | `200 OK` with a 16‑char body: 13 printable ASCII chars ending in `TTL` |

The 13‑char prefix is **not truly random**: the sum of all 13 ASCII values is
always divisible by 7, making the response verifiable without a shared secret.

Linux hosts default to TTL 64, so direct requests are always denied.
Participants must raise their outbound TTL (e.g. via `iptables` mangle)
to >= 100 to pass the gate.

## Build

```bash
sudo apt-get install -y golang-go
go build -o webserver-ttl .
```

## Run

Requires root (raw sockets + listening on privileged port).

```bash
sudo ./webserver-ttl
```

## Test

```bash
sudo ./test.sh
```

Runs a suite of integration tests: TTL rejection, mangle‑based bypass,
random response verification, and cleanup.
