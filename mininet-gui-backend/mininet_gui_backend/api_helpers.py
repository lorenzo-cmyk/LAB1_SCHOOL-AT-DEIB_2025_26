"""
Helper functions, Pydantic models, and constants extracted from api.py.

This module contains non-endpoint utility functions, data models, and
configuration constants that support the Mininet-GUI API layer.
"""

import os
import select
import asyncio
import subprocess
import logging
import pkgutil
from typing import Optional, Set

from pydantic import BaseModel, Field

from mininet.log import debug as _debug
from mininet.node import (
    RemoteController,
    Controller as ReferenceController,
    NOX,
    UserSwitch,
    OVSSwitch,
    OVSKernelSwitch,
    OVSBridge,
    Node,
)
from mininet_gui_backend.nodes import Ryu
from fastapi import HTTPException, WebSocket

from mininet_gui_backend.schema import Switch, Host, Controller, Nat, Router
from mininet_gui_backend import app_state as state


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

LOG_FILE = os.path.join(os.path.dirname(__file__), "mininet.log")
RYU_APP_DIRS = []

FLOW_FIELDS = [
    "cookie",
    "duration",
    "table",
    "n_packets",
    "n_bytes",
    "idle_timeout",
    "priority",
    "actions",
]

MONITOR_INTERVAL_SECONDS = 0.5


# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------


class LinkCreate(BaseModel):
    src: str
    dst: str


class ControllerUpdate(BaseModel):
    controller_type: Optional[str] = None
    remote: Optional[bool] = None
    ip: Optional[str] = None
    port: Optional[int] = None
    ryu_app: Optional[str | list] = None
    color: Optional[str] = None
    of_version: Optional[str] = None


class SwitchUpdate(BaseModel):
    of_version: Optional[str] = None


class HostUpdate(BaseModel):
    ip: Optional[str] = None
    intf: Optional[str] = None
    default_route: Optional[str] = None
    default_route_type: Optional[str] = None
    default_route_dev: Optional[str] = None
    default_route_ip: Optional[str] = None


class IperfRequest(BaseModel):
    client: str
    server: str
    l4_type: Optional[str] = "TCP"
    udp_bw: Optional[str] = None
    fmt: Optional[str] = None
    seconds: Optional[int] = 5
    port: Optional[int] = None


class LinuxRouter(Node):
    def config(self, **params):
        super().config(**params)
        self.cmd("sysctl -w net.ipv4.ip_forward=1")

    def terminate(self):
        self.cmd("sysctl -w net.ipv4.ip_forward=0")
        super().terminate()


# ---------------------------------------------------------------------------
# Helper / utility functions
# ---------------------------------------------------------------------------


def debug(msg, *args):
    _debug(str(msg) + " " + " ".join(map(str, args)) + "\n")


def list_ryu_apps():
    apps = set()
    app_dirs = []
    env_dirs = os.environ.get("RYU_APP_DIRS", "")
    if env_dirs:
        for entry in env_dirs.split(os.pathsep):
            entry = entry.strip()
            if entry:
                app_dirs.append(entry)
    for app_dir in RYU_APP_DIRS:
        if os.path.isdir(app_dir):
            app_dirs.append(app_dir)
    try:
        import importlib

        app_pkg = importlib.import_module("ryu.app")
        if app_pkg and hasattr(app_pkg, "__path__"):
            for _finder, name, _ispkg in pkgutil.iter_modules(app_pkg.__path__):
                if name and not name.startswith("__"):
                    apps.add(name)
            pkg_dir = os.path.dirname(app_pkg.__file__)
            if os.path.isdir(pkg_dir):
                app_dirs.append(pkg_dir)
    except Exception:
        pass

    try:
        result = subprocess.run(
            ["ryu-manager", "--app-list"],
            check=False,
            capture_output=True,
            text=True,
            timeout=3,
        )
        if result.stdout:
            for line in result.stdout.splitlines():
                line = line.strip()
                if not line:
                    continue
                token = line.split()[0]
                if token.startswith("ryu.app."):
                    apps.add(token[len("ryu.app.") :])
    except Exception:
        pass

    for app_dir in app_dirs:
        try:
            entries = os.listdir(app_dir)
        except OSError:
            continue
        for entry in entries:
            if entry.endswith(".py") and entry != "__init__.py":
                apps.add(entry[:-3])

    return sorted(apps)


def setup_log_file():
    os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
    handler = logging.FileHandler(LOG_FILE)
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)
    if not any(
        isinstance(h, logging.FileHandler)
        and getattr(h, "baseFilename", None) == handler.baseFilename
        for h in root_logger.handlers
    ):
        root_logger.addHandler(handler)
    try:
        from mininet.log import lg

        lg.setLevel(logging.DEBUG)
        if not any(
            isinstance(h, logging.FileHandler)
            and getattr(h, "baseFilename", None) == handler.baseFilename
            for h in lg.handlers
        ):
            lg.addHandler(handler)
    except Exception:
        pass


def clear_log_file():
    os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
    with open(LOG_FILE, "w", encoding="utf-8"):
        pass


def add_host_to_net(host: Host):
    host_node = state.net.addHost(host.name, ip=host.ip)
    host_node.x = host.x
    host_node.y = host.y
    host_node.ip = host.ip
    host_node.type = "host"
    return host_node


def add_router_to_net(router: Router):
    params = {"ip": router.ip, "mac": router.mac}
    router_node = state.net.addHost(router.name, cls=LinuxRouter, **params)
    router_node.x = router.x
    router_node.y = router.y
    router_node.ip = router.ip
    router_node.mac = router.mac
    router_node.type = "router"
    return router_node


def add_nat_to_net(nat: Nat):
    params = {}
    if nat.ip:
        params["ip"] = nat.ip
    if nat.mac:
        params["mac"] = nat.mac
    nat_node = state.net.addNAT(nat.name, connect=False, **params)
    nat_node.x = nat.x
    nat_node.y = nat.y
    nat_node.type = "nat"
    if nat.ip:
        nat_node.ip = nat.ip
    if nat.mac:
        nat_node.mac = nat.mac
    return nat_node


def add_controller_to_net(controller: Controller, start=True):
    controller_type = (controller.controller_type or "").lower()
    if controller.remote or controller_type == "remote":
        controller_node = state.net.addController(
            controller.name,
            controller=RemoteController,
            ip=controller.ip,
            port=controller.port,
        )
    elif controller_type == "ryu":
        if not controller.port:
            raise HTTPException(
                status_code=400, detail="Ryu controller requires a port"
            )
        if not controller.ryu_app:
            raise HTTPException(
                status_code=400, detail="Ryu controller requires an app"
            )
        ryu_apps = (
            controller.ryu_app
            if isinstance(controller.ryu_app, list)
            else [controller.ryu_app]
        )
        available_apps = list_ryu_apps()
        if available_apps and any(
            app_name not in available_apps for app_name in ryu_apps
        ):
            try:
                import importlib

                for app_name in ryu_apps:
                    importlib.import_module(f"ryu.app.{app_name}")
            except Exception:
                raise HTTPException(status_code=400, detail="Invalid ryu app")
        elif not available_apps:
            try:
                import importlib

                for app_name in ryu_apps:
                    importlib.import_module(f"ryu.app.{app_name}")
            except Exception:
                pass
        controller.ip = controller.ip or "127.0.0.1"
        controller_node = state.net.addController(
            controller.name,
            controller=Ryu,
            ip=controller.ip,
            port=controller.port,
            ryu_app=ryu_apps,
            of_version=controller.of_version or "OpenFlow13",
        )
    elif controller_type == "nox":
        controller_node = state.net.addController(controller.name, controller=NOX)
    else:
        if not controller.port or controller.port in _list_listening_ports():
            controller.port = _find_free_controller_port()
        controller_node = state.net.addController(
            controller.name, controller=ReferenceController, port=controller.port
        )

    if start:
        controller_node.start()
    controller_node.x = controller.x
    controller_node.y = controller.y
    controller_node.type = "controller"
    return controller_node


def _list_listening_ports() -> Set[int]:
    result = subprocess.run(
        ["netstat", "-tuln"],
        text=True,
        capture_output=True,
    )
    if result.returncode != 0:
        detail = (result.stderr or result.stdout or "netstat failed").strip()
        raise HTTPException(status_code=500, detail=detail)
    ports: Set[int] = set()
    for line in (result.stdout or "").splitlines():
        line = line.strip()
        if not line or line.lower().startswith("proto"):
            continue
        parts = line.split()
        if len(parts) < 4:
            continue
        local = parts[3]
        if ":" not in local:
            continue
        port_str = local.rsplit(":", 1)[-1]
        if port_str.isdigit():
            ports.add(int(port_str))
    return ports


def _find_free_controller_port() -> int:
    used = _list_listening_ports()
    ranges = [
        range(6633, 6638),
        range(6653, 6658),
    ]
    for rng in ranges:
        for port in rng:
            if port not in used:
                return port
    raise HTTPException(status_code=400, detail="no available controller ports")


def add_switch_to_net(switch: Switch, start=True):
    switch_type = (switch.switch_type or "").lower()
    switch.switch_type = switch_type or switch.switch_type
    if switch_type == "user":
        switch_node = state.net.addSwitch(
            switch.name, ports=switch.ports, cls=UserSwitch
        )
    elif switch_type == "ovs":
        switch_node = state.net.addSwitch(
            switch.name, ports=switch.ports, cls=OVSSwitch
        )
    elif switch_type == "ovskernel":
        switch_node = state.net.addSwitch(
            switch.name, ports=switch.ports, cls=OVSKernelSwitch
        )
    elif switch_type == "ovsbridge":
        switch_node = state.net.addSwitch(
            switch.name, ports=switch.ports, cls=OVSBridge
        )
    else:
        switch_node = state.net.addSwitch(switch.name, ports=switch.ports)

    if start and switch.controller:
        switch_node.start([state.net.nameToNode.get(switch.controller)])
    else:
        switch_node.start([])
    switch_node.x = switch.x
    switch_node.y = switch.y
    switch_node.type = "sw"
    switch_node.controller = switch.controller
    switch_node.switch_type = switch.switch_type
    if switch.of_version:
        _apply_switch_openflow_version(
            switch.name, switch.of_version, switch_type=switch.switch_type
        )
    return switch_node


def _apply_switch_openflow_version(
    switch_id: str, of_version: Optional[str], switch_type: Optional[str] = None
):
    if switch_type is None:
        switch = state.switches.get(switch_id)
        if not switch:
            raise HTTPException(status_code=404, detail="switch not found")
        switch_type = switch.switch_type
    switch_type = (switch_type or "").lower()
    if switch_type not in ("ovs", "ovskernel", "ovsbridge"):
        raise HTTPException(
            status_code=400,
            detail="openflow version is only supported for OVS switches",
        )
    if not of_version or of_version == "auto":
        result = subprocess.run(
            ["ovs-vsctl", "--if-exists", "clear", "bridge", switch_id, "protocols"],
            text=True,
            capture_output=True,
        )
    else:
        result = subprocess.run(
            [
                "ovs-vsctl",
                "--if-exists",
                "set",
                "bridge",
                switch_id,
                f"protocols={of_version}",
            ],
            text=True,
            capture_output=True,
        )
    if result.returncode != 0:
        detail = (result.stderr or result.stdout or "ovs-vsctl failed").strip()
        raise HTTPException(status_code=400, detail=detail)


def _terminate_all_terminals():
    for node_id, sessions in list(state.terminals.items()):
        for session_id, (master_fd, process) in list(sessions.items()):
            try:
                process.terminate()
            except Exception:
                pass
            try:
                process.wait(timeout=0.1)
            except Exception:
                pass
            try:
                os.close(master_fd)
            except Exception:
                pass
        sessions.clear()
        state.terminals.pop(node_id, None)


async def _stop_all_sniffers_quietly():
    try:
        await state.sniffer_manager.stop()
    except Exception:
        pass


async def _stop_mininet_with_timeout(timeout: float = 5.0):
    controllers = list(getattr(state.net, "controllers", []) or [])
    if controllers:
        for controller in controllers:
            try:
                controller.terminate()
            except Exception:
                pass
    state.net.controllers = []
    loop = asyncio.get_running_loop()
    try:
        await asyncio.wait_for(
            loop.run_in_executor(None, state.net.stop), timeout=timeout
        )
    except asyncio.TimeoutError:
        debug(
            f"mininet.stop() did not complete within {timeout} seconds, continuing cleanup"
        )
    except Exception as exc:
        debug("error while stopping mininet", exc)


def list_mininet_interfaces():
    nodes = []
    if hasattr(state.net, "hosts"):
        for host in state.net.hosts:
            intfs = [
                i.name
                for i in host.intfList()
                if i.name and i.name not in ("lo", "lo0")
            ]
            node_type = getattr(host, "type", "host")
            nodes.append(
                {"id": host.name, "type": node_type, "intfs": intfs, "pid": host.pid}
            )
    if hasattr(state.net, "switches"):
        for sw in state.net.switches:
            intfs = [
                i.name for i in sw.intfList() if i.name and i.name not in ("lo", "lo0")
            ]
            node_type = getattr(sw, "type", "switch")
            nodes.append(
                {"id": sw.name, "type": node_type, "intfs": intfs, "pid": sw.pid}
            )
    return nodes


async def read_pty(master_fd, websocket: WebSocket):
    """Reads PTY output and sends it to WebSocket"""
    try:
        while True:
            await asyncio.sleep(0.01)
            try:
                r, _, _ = select.select([master_fd], [], [], 0)
            except OSError as e:
                if getattr(e, "errno", None) == 9:
                    break
                raise
            if master_fd in r:
                try:
                    output = os.read(master_fd, 1024).decode(errors="ignore")
                except OSError as e:
                    if getattr(e, "errno", None) == 9:
                        break
                    raise
                if output:
                    await websocket.send_text(output)
    except Exception as e:
        debug(f"PTY Read Error: {e}")


async def read_sniffer(process: asyncio.subprocess.Process, websocket: WebSocket):
    """Reads tcpdump output and sends it to WebSocket"""
    try:
        while True:
            line = await process.stdout.readline()
            if not line:
                break
            await websocket.send_text(line.decode(errors="ignore").rstrip())
    except Exception as e:
        debug(f"Sniffer Read Error: {e}")


async def start_sniffer_process(node_pid: int, intf: str, pcap_path: str):
    if node_pid and node_pid > 0:
        return await asyncio.create_subprocess_exec(
            "mnexec",
            "-a",
            str(node_pid),
            "tshark",
            "-l",
            "-n",
            "-i",
            intf,
            "-T",
            "ek",
            "-w",
            pcap_path,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
    return await asyncio.create_subprocess_exec(
        "tshark",
        "-l",
        "-n",
        "-i",
        intf,
        "-T",
        "ek",
        "-w",
        pcap_path,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
