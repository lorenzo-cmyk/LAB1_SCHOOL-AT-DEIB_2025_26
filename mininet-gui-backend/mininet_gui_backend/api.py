"""
Mininet-GUI API to deploy and manage a mininet network instance.

## Deploy

Endpoints to start and stop the network at any point.

## Topology

Endpoints that add, remove and edit nodes and edges in real time.
"""

import json
import subprocess
from datetime import datetime, timezone
from mininet_gui_backend.sniffer import SnifferManager
from typing import Tuple, Union
from contextlib import asynccontextmanager


from mininet.net import Mininet
from mininet.log import setLogLevel
from mininet.topo import Topo
from mininet.clean import cleanup as mn_cleanup
from mininet.node import UserSwitch, OVSSwitch, OVSKernelSwitch, OVSBridge
from mininet.link import TCLink
from fastapi import FastAPI, HTTPException, File, UploadFile, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse

from mininet_gui_backend.export import (
    build_addressing_plan,
    export_net_to_script,
    export_net_to_json,
)
from mininet_gui_backend.schema import Switch, Host, Controller, Nat, Router
from mininet_gui_backend import app_state as state
from mininet_gui_backend.flow_rules import (
    FlowRuleCreate,
    FlowRuleDelete,
    build_flow,
    build_flow_match,
)
from mininet_gui_backend.utils import (
    get_interface_stats_path,
    parse_flow_match_from_dump,
    read_interface_counter,
)
from mininet_gui_backend.api_helpers import (
    LinkCreate,
    LinkUpdate,
    ControllerUpdate,
    SwitchUpdate,
    HostUpdate,
    IperfRequest,
    FLOW_FIELDS,
    debug,
    list_ryu_apps,
    setup_log_file,
    clear_log_file,
    add_host_to_net,
    add_router_to_net,
    add_nat_to_net,
    add_controller_to_net,
    add_switch_to_net,
    _apply_switch_openflow_version,
    _terminate_all_terminals,
    _stop_all_sniffers_quietly,
    _stop_mininet_with_timeout,
    list_mininet_interfaces,
    start_sniffer_process,
)

from mininet_gui_backend.routers.websockets import router as ws_router
from mininet_gui_backend.routers.sniffer_api import router as sniffer_router
from mininet_gui_backend import __version__ as BACKEND_VERSION

try:
    from mininet.net import VERSION as MININET_VERSION
except Exception:
    MININET_VERSION = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    # start
    mn_cleanup()
    setup_log_file()
    state.controllers = dict()
    state.switches = dict()
    state.hosts = dict()
    state.nats = dict()
    state.routers = dict()
    state.links = dict()
    state.link_attrs = dict()
    state.terminals = dict()
    state.sniffers = dict()
    state.sniffer_manager = SnifferManager(
        list_mininet_interfaces, start_sniffer_process
    )
    state.pingall_running = False
    state.iperf_running = False
    setLogLevel("debug")
    state.net = Mininet(autoSetMacs=True, topo=Topo())
    state.net.is_started = False
    yield
    # stop
    mn_cleanup()


app = FastAPI(
    debug=True,
    lifespan=lifespan,
    title="Mininet-GUI-API",
    description=__doc__,
    version=BACKEND_VERSION,
    terms_of_service="http://example.com/terms/",
    # contact= {
    #     "name": "Lucas Schneider",
    #     "url": "https://github.com/schneider8357",
    #     "email": "schneider8357@hotmail.com",
    # },
    contact={
        "name": "",
        "url": "",
        "email": "",
    },
    # license_info={
    #     "name": "Apache 2.0",
    #     "url": "https://www.apache.org/licenses/LICENSE-2.0.html",
    # },
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(ws_router)
app.include_router(sniffer_router)


@app.get("/api/version")
def get_version():
    return {"version": app.version, "mininet_version": MININET_VERSION}


@app.get("/api/health")
def get_health():
    connected = state.net is not None
    network_started = bool(getattr(state.net, "is_started", False))
    status = "ok" if connected else "unavailable"
    return {
        "status": status,
        "connected": connected,
        "network_started": network_started,
        "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
    }


@app.get("/api/ryu/apps")
def get_ryu_apps():
    return {"apps": list_ryu_apps()}


@app.get("/api/mininet/addressing_plan")
def addressing_plan():
    if not state.net.is_started:
        raise HTTPException(status_code=400, detail="network must be started")
    return build_addressing_plan(state.net)


@app.get("/api/mininet/hosts")
def list_hosts():
    return state.hosts


@app.get("/api/mininet/interfaces")
def list_interfaces():
    return {"nodes": list_mininet_interfaces()}


@app.get("/api/mininet/switches")
def list_switches():
    for sw_id, sw in state.switches.items():
        if not getattr(sw, "switch_type", None):
            node = state.net.nameToNode.get(sw_id)
            if node:
                if isinstance(node, UserSwitch):
                    sw.switch_type = "user"
                elif isinstance(node, OVSBridge):
                    sw.switch_type = "ovsbridge"
                elif isinstance(node, OVSSwitch):
                    sw.switch_type = "ovs"
                elif isinstance(node, OVSKernelSwitch):
                    sw.switch_type = "ovskernel"
    return state.switches


@app.get("/api/mininet/controllers")
def list_controllers():
    return state.controllers


@app.get("/api/mininet/nats")
def list_nats():
    return state.nats


@app.get("/api/mininet/routers")
def list_routers():
    return state.routers


@app.get("/api/mininet/links")
def list_edges():
    edges = []
    for key in state.links:
        nodes = list(key)
        attrs = state.link_attrs.get(key) or {}
        link = state.links.get(key)
        from_node = nodes[0] if len(nodes) > 0 else None
        to_node = nodes[1] if len(nodes) > 1 else None
        intfs = None
        intf1 = getattr(link, "intf1", None)
        intf2 = getattr(link, "intf2", None)
        if (
            intf1
            and intf2
            and getattr(intf1, "node", None)
            and getattr(intf2, "node", None)
        ):
            from_node = intf1.node.name
            to_node = intf2.node.name
            intfs = {"from": intf1.name, "to": intf2.name}
        if from_node and to_node:
            edges.append(
                {"from": from_node, "to": to_node, "options": attrs, "intfs": intfs}
            )
    return edges


@app.get("/api/mininet/start")
def get_network_started():
    return state.net.is_started


@app.post("/api/mininet/start")
def start_network():
    """Build network and start nodes"""
    if state.net.is_started:
        raise HTTPException(status_code=400, detail="network already started")
    state.net.build()
    for controller in state.controllers:
        state.net.nameToNode[controller].start()
    for switch_id in state.switches:
        switch = state.net.nameToNode[switch_id]
        controller_id = getattr(state.switches[switch_id], "controller", None)
        controller_node = None
        if controller_id:
            controller_node = state.net.nameToNode.get(controller_id)
        if controller_node:
            switch.controller = controller_node
            switch.start([controller_node])
        else:
            switch.controller = None
            switch.start([])
    state.net.is_started = True
    return {"status": "ok"}


@app.post("/api/mininet/stop")
async def stop_network():
    """Stop network and nodes"""
    await _stop_all_sniffers_quietly()
    _terminate_all_terminals()
    state.iperf_running = False

    await _stop_mininet_with_timeout()

    # Cleanup (mn -c)
    mn_cleanup()

    # Create the Mininet network
    setLogLevel("debug")
    state.net = Mininet(autoSetMacs=True, topo=Topo())
    state.net.is_started = False
    state.sniffer_manager = SnifferManager(list_mininet_interfaces, start_sniffer_process)
    state.links = dict()
    # Recreate topology without start
    entries = [
        (add_host_to_net, state.hosts.values(), {}),
        (add_router_to_net, state.routers.values(), {}),
        (add_nat_to_net, state.nats.values(), {}),
        (add_controller_to_net, state.controllers.values(), {"start": False}),
        (add_switch_to_net, state.switches.values(), {"start": False}),
    ]
    for builder, collection, kwargs in entries:
        for item in collection:
            builder(item, **kwargs)
    state.links = dict()
    for key, attrs in list(state.link_attrs.items()):
        nodes = list(key)
        if len(nodes) != 2:
            continue
        src, dst = nodes
        kwargs = {}
        if attrs:
            kwargs.update(attrs)
            kwargs["cls"] = TCLink
        new_link = state.net.addLink(src, dst, **kwargs)
        if state.net.is_started:
            for node_id in (src, dst):
                node = state.net.nameToNode[node_id]
                if node.type in ("host", "nat", "router"):
                    node.configDefault()
                elif node.type == "sw" and node.controller:
                    node.start([node.controller])
        state.links[key] = new_link
    return {"status": "ok"}


@app.post("/api/mininet/reset")
async def reset_network():
    """Restart network and nodes"""
    try:
        await state.sniffer_manager.stop()
    except Exception:
        pass
    clear_log_file()
    await stop_network()
    return start_network()


@app.post("/api/mininet/full_reset")
async def full_reset_network():
    """Full reset: stop everything, cleanup, and clear saved topology."""
    await _stop_all_sniffers_quietly()
    _terminate_all_terminals()
    clear_log_file()

    await _stop_mininet_with_timeout()
    mn_cleanup()

    state.controllers = dict()
    state.switches = dict()
    state.hosts = dict()
    state.nats = dict()
    state.routers = dict()
    state.links = dict()
    state.link_attrs = dict()
    state.terminals = dict()
    state.sniffers = dict()
    state.pingall_running = False
    state.iperf_running = False

    setLogLevel("debug")
    state.net = Mininet(autoSetMacs=True, topo=Topo())
    state.net.is_started = False
    state.sniffer_manager = SnifferManager(list_mininet_interfaces, start_sniffer_process)
    return {"status": "ok"}


@app.post("/api/mininet/pingall")
def run_pingall():
    """Build network and start nodes"""
    if not state.net.is_started:
        raise HTTPException(
            status_code=400, detail="network must be started to run pingall"
        )
    if state.pingall_running:
        raise HTTPException(status_code=409, detail="pingall already running")
    state.pingall_running = True
    try:
        pingall_results = state.net.pingFull()
        debug(pingall_results)
        return "\n".join(
            [
                f"{p[0]}->{p[1]}: {p[2][0]}/{p[2][1]}, rtt min/avg/max/mdev {p[2][2]:.3f}/{p[2][3]:.3f}/{p[2][4]:.3f}/{p[2][5]:.3f} ms"
                for p in pingall_results
            ]
        )
    except AssertionError:
        raise HTTPException(
            status_code=500,
            detail="Host shell busy — wait for previous command to finish and try again",
        )
    finally:
        state.pingall_running = False


@app.post("/api/mininet/hosts")
def create_host(host: Host):
    if host.id in state.hosts:
        state.hosts[host.id] = host
        return {"status": "updated"}
    # Create host in the Mininet network using the request data
    debug(host)
    new_host = add_host_to_net(host)
    state.hosts[host.name] = host
    debug(new_host)
    # Return an OK status code
    return {"status": "ok"}


@app.post("/api/mininet/routers")
def create_router(router: Router):
    if router.id in state.routers:
        state.routers[router.id] = router
        return {"status": "updated"}
    debug(router)
    new_router = add_router_to_net(router)
    state.routers[router.name] = router
    debug(new_router)
    return {"status": "ok"}


@app.patch("/api/mininet/hosts/{host_id}")
def update_host(host_id: str, payload: HostUpdate):
    if host_id not in state.net.nameToNode:
        raise HTTPException(status_code=404, detail=f"Node {host_id} not found")
    node = state.net.nameToNode[host_id]
    if getattr(node, "type", None) != "host":
        raise HTTPException(status_code=400, detail="node is not a host")
    host = state.hosts.get(host_id)
    if not host:
        raise HTTPException(status_code=404, detail=f"Host {host_id} not found")
    if payload.ip:
        ip_value = payload.ip.strip()
        if "/" in ip_value:
            addr, prefix_raw = ip_value.split("/", 1)
            try:
                prefix_len = int(prefix_raw)
            except ValueError:
                raise HTTPException(status_code=400, detail="invalid prefix length")
        else:
            addr = ip_value
            prefix_len = None
        if prefix_len is None:
            fallback = host.ip
            if fallback and "/" in fallback:
                prefix_len = int(fallback.split("/", 1)[1])
            else:
                prefix_len = 8
        intf = payload.intf or None
        node.setIP(addr, prefixLen=prefix_len, intf=intf)
        host.ip = f"{addr}/{prefix_len}"
    if payload.default_route_type:
        route_type = payload.default_route_type.strip().lower()
        if route_type == "dev":
            dev = (payload.default_route_dev or "").strip()
            if dev:
                node.setDefaultRoute(dev)
            else:
                node.cmd("ip route del default")
        elif route_type == "ip":
            ip_value = (payload.default_route_ip or "").strip()
            if ip_value:
                node.setDefaultRoute(f"via {ip_value}")
            else:
                node.cmd("ip route del default")
    elif payload.default_route is not None:
        route_value = payload.default_route.strip()
        if route_value:
            node.setDefaultRoute(route_value)
        else:
            node.cmd("ip route del default")
    state.hosts[host_id] = host
    return {"status": "ok", "host": host.model_dump()}


@app.post("/api/mininet/nats")
def create_nat(nat: Nat):
    if nat.id in state.nats:
        state.nats[nat.id] = nat
        return {"status": "updated"}
    debug(nat)
    new_nat = add_nat_to_net(nat)
    state.nats[nat.name] = nat
    debug(new_nat)
    return {"status": "ok"}


@app.post("/api/mininet/switches")
def create_switch(switch: Switch):
    # Create switch in the Mininet network using the request data
    debug("CREATING SWITCH", switch)
    if switch.controller and switch.controller not in state.controllers:
        raise HTTPException(
            status_code=400, detail=f'controller "{switch.controller}" does not exist'
        )
    add_switch_to_net(switch)
    state.switches[switch.name] = switch
    return switch


@app.post("/api/mininet/controllers")
def create_controller(controller: Controller):
    # Create controller in the Mininet network using the request data
    debug(controller)
    new_controller = add_controller_to_net(controller, start=True)
    state.controllers[controller.name] = controller
    debug(new_controller)
    return {"status": "ok"}


@app.put("/api/mininet/controllers/{controller_id}")
def update_controller(controller_id: str, payload: ControllerUpdate):
    if controller_id not in state.controllers:
        raise HTTPException(status_code=404, detail="controller not found")
    controller = state.controllers[controller_id]
    updates = payload.model_dump(exclude_none=True)
    for key, value in updates.items():
        setattr(controller, key, value)
    state.controllers[controller_id] = controller
    return {"controller": controller.model_dump()}


@app.put("/api/mininet/switches/{switch_id}/openflow")
def update_switch_openflow_version(switch_id: str, payload: SwitchUpdate):
    if switch_id not in state.switches:
        raise HTTPException(status_code=404, detail="switch not found")
    of_version = payload.of_version
    if of_version in ("", "auto"):
        of_version = None
    allowed = {
        None,
        "OpenFlow10",
        "OpenFlow11",
        "OpenFlow12",
        "OpenFlow13",
        "OpenFlow14",
        "OpenFlow15",
    }
    if of_version not in allowed:
        raise HTTPException(status_code=400, detail="invalid OpenFlow version")
    _apply_switch_openflow_version(switch_id, of_version)
    state.switches[switch_id].of_version = of_version
    return {"switch": state.switches[switch_id].model_dump()}


@app.post("/api/mininet/associate_switch")
def associate_switch(data: dict):
    # Associate switch to controller.
    if "switch" not in data or "controller" not in data:
        raise HTTPException(status_code=400, detail="missing key in data")
    sw_id = data["switch"]
    ctl_id = data["controller"]
    if sw_id not in state.net.nameToNode or ctl_id not in state.net.nameToNode:
        raise HTTPException(status_code=400, detail="node not in net")
    sw = state.net.nameToNode[sw_id]
    ctl = state.net.nameToNode[ctl_id]
    if state.switches[sw_id].controller:
        raise HTTPException(status_code=400, detail="switch is already associated")
    sw.controller = ctl
    state.switches[sw_id].controller = ctl_id
    if state.net.is_started:
        sw.start([sw.controller])
    return "OK"


@app.post("/api/mininet/links")
def create_link(payload: Union[Tuple[str, str], LinkCreate]):
    if isinstance(payload, (list, tuple)):
        src, dst = payload
        options = None
    else:
        src, dst = payload.src, payload.dst
        options = payload.options

    if src not in state.net.nameToNode or dst not in state.net.nameToNode:
        raise HTTPException(status_code=400, detail="node not in net")
    if (
        state.net.nameToNode[src].type == "host"
        and state.net.nameToNode[src].intfList()
        and len(
            [
                i
                for i in state.net.nameToNode[src].intfList()
                if i.name and i.name not in ("lo", "lo0")
            ]
        )
        >= 1
    ):
        raise HTTPException(status_code=400, detail="host already has a link")
    if (
        state.net.nameToNode[dst].type == "host"
        and state.net.nameToNode[dst].intfList()
        and len(
            [
                i
                for i in state.net.nameToNode[dst].intfList()
                if i.name and i.name not in ("lo", "lo0")
            ]
        )
        >= 1
    ):
        raise HTTPException(status_code=400, detail="host already has a link")
    key = frozenset((src, dst))
    if key in state.links:
        raise HTTPException(status_code=400, detail="link already exists")
    link_kwargs = {}
    if options:
        opt = options.model_dump(exclude_none=True)
        if "delay" in opt and isinstance(opt["delay"], (int, float)):
            opt["delay"] = f"{opt['delay']}ms"
        if "jitter" in opt and isinstance(opt["jitter"], (int, float)):
            opt["jitter"] = f"{opt['jitter']}ms"
        link_kwargs.update(opt)
        link_kwargs["cls"] = TCLink
    new_link = state.net.addLink(src, dst, **link_kwargs)
    if state.net.is_started:
        for node in (src, dst):
            node = state.net.nameToNode[node]
            if node.type in ("host", "nat", "router"):
                node.configDefault()
            elif node.type == "sw" and node.controller:
                # Important, otherwise switch doesnt init the port
                controller_node = (
                    node.controller
                    if not isinstance(node.controller, str)
                    else state.net.nameToNode.get(node.controller)
                )
                if controller_node:
                    node.controller = controller_node
                    node.start([controller_node])
                else:
                    node.start([])
    # It is important to store this Link object because
    # mininet (apparently) doesn't have an easy way to access this
    state.links[key] = new_link
    if options:
        state.link_attrs[key] = options.model_dump(exclude_none=True)
    else:
        state.link_attrs[key] = {}
    intfs = None
    if getattr(new_link, "intf1", None) and getattr(new_link, "intf2", None):
        intfs = {"from": new_link.intf1.name, "to": new_link.intf2.name}
    return {"from": src, "to": dst, "options": state.link_attrs[key], "intfs": intfs}


@app.put("/api/mininet/links")
def update_link(payload: LinkUpdate):
    src, dst = payload.src, payload.dst
    options = payload.options
    if src not in state.net.nameToNode or dst not in state.net.nameToNode:
        raise HTTPException(status_code=400, detail="node not in net")
    key = frozenset((src, dst))
    if key not in state.links:
        raise HTTPException(status_code=404, detail="link not found")
    stored_opts = options.model_dump(exclude_none=True) if options else {}
    config_opts = dict(stored_opts)
    if "delay" in config_opts and isinstance(config_opts["delay"], (int, float)):
        config_opts["delay"] = f"{config_opts['delay']}ms"
    if "jitter" in config_opts and isinstance(config_opts["jitter"], (int, float)):
        config_opts["jitter"] = f"{config_opts['jitter']}ms"
    state.link_attrs[key] = stored_opts

    link = state.links.get(key)
    if link and config_opts:
        try:
            link.intf1.config(**config_opts)
            link.intf2.config(**config_opts)
        except Exception as exc:
            debug("failed to update link config", exc)

    return {"from": src, "to": dst, "options": state.link_attrs[key]}


@app.get("/api/mininet/links/stats/{src_id}/{dst_id}")
def get_link_stats(src_id: str, dst_id: str):
    key = frozenset((src_id, dst_id))
    link = state.links.get(key)
    if not link:
        raise HTTPException(status_code=404, detail="link not found")
    intfs = []
    for intf in (getattr(link, "intf1", None), getattr(link, "intf2", None)):
        if not intf or not getattr(intf, "name", None):
            continue
        stats_paths = get_interface_stats_path(intf.name)
        intfs.append(
            {
                "name": intf.name,
                "tx_bytes": read_interface_counter(stats_paths["tx"]),
                "rx_bytes": read_interface_counter(stats_paths["rx"]),
            }
        )
    return {
        "from": src_id,
        "to": dst_id,
        "intfs": intfs,
        "options": state.link_attrs.get(key, {}),
        "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
    }


@app.post("/api/mininet/node_position")
def node_position(data: dict):
    if "node_id" not in data or "position" not in data:
        raise HTTPException(status_code=400, detail="missing key in data")
    debug("data:", data)
    node_id = data["node_id"]
    x, y = data["position"]
    if node_id not in state.net.nameToNode:
        raise HTTPException(status_code=404, detail=f"Node {node_id} not found")
    node = state.net.nameToNode[node_id]
    debug("before update xy", (node.x, node.y))
    node.x = x
    node.y = y
    debug(
        "updated xy", (state.net.nameToNode[node_id].x, state.net.nameToNode[node_id].y)
    )
    if node.type == "sw":
        state.switches[node_id].x = x
        state.switches[node_id].y = y
    elif node.type == "host":
        state.hosts[node_id].x = x
        state.hosts[node_id].y = y
    elif node.type == "controller":
        state.controllers[node_id].x = x
        state.controllers[node_id].y = y
    elif node.type == "nat":
        state.nats[node_id].x = x
        state.nats[node_id].y = y
    elif node.type == "router":
        state.routers[node_id].x = x
        state.routers[node_id].y = y
    return {"message": f"Node {node_id} updated successfully"}


@app.delete("/api/mininet/delete_node/{node_id}")
def delete_node(node_id: str):
    if node_id not in state.net.nameToNode:
        raise HTTPException(status_code=404, detail=f"Node {node_id} not found")
    node = state.net.nameToNode[node_id]
    state.net.delNode(node)
    if node.type == "sw":
        del state.switches[node_id]
    elif node.type == "host":
        del state.hosts[node_id]
    elif node.type == "controller":
        del state.controllers[node_id]
        for switch_id in state.switches:
            switch = state.switches[switch_id]
            if switch.controller == node_id:
                debug("CONTROLLER", switch.controller, node_id)
                state.switches[switch_id].controller = None
                state.net.nameToNode[switch_id].start([])
    elif node.type == "nat":
        del state.nats[node_id]
    elif node.type == "router":
        del state.routers[node_id]
    return {"message": f"Node {node_id} deleted successfully"}


@app.delete("/api/mininet/delete_link/{src_id}/{dst_id}")
def delete_link(src_id: str, dst_id: str):
    key = frozenset((src_id, dst_id))
    if key not in state.links:
        raise HTTPException(status_code=404, detail="Node not found")
    state.net.delLink(state.links[key])
    del state.links[key]
    state.link_attrs.pop(key, None)
    return {"message": f"Link {key} deleted successfully"}


@app.delete("/api/mininet/remove_association/{src_id}/{dst_id}")
def remove_association(src_id: str, dst_id: str):
    if src_id not in state.net.nameToNode or dst_id not in state.net.nameToNode:
        raise HTTPException(status_code=400, detail="node not in net")
    sw, ctl = None, None
    for node_id in (src_id, dst_id):
        node = state.net.nameToNode[node_id]
        if node.type == "sw":
            sw = node
        elif node.type == "controller":
            ctl = node
    if not sw or not ctl:
        raise HTTPException(
            status_code=400, detail=f"node {node_id} isnt switch or controller"
        )
    sw.controller = None
    state.switches[sw.name].controller = None
    if state.net.is_started:
        sw.start([])
    return "OK"


@app.get("/api/mininet/stats/{node_id}")
def get_node_stats(node_id: str):
    if node_id not in state.net.nameToNode:
        raise HTTPException(status_code=404, detail=f"Node {node_id} not found")

    node = state.net.nameToNode[node_id]
    base_data = (
        state.switches.get(node_id)
        or state.hosts.get(node_id)
        or state.controllers.get(node_id)
        or state.nats.get(node_id)
        or state.routers.get(node_id)
    )
    if not base_data:
        raise HTTPException(status_code=404, detail=f"Node {node_id} not found")
    result = dict(**base_data.model_dump())

    if node.type == "sw":
        ports_raw = node.dpctl("dump-ports")
        ports_raw = ports_raw[ports_raw.find("\n") + 1 :].replace("\n", " ")
        result["ports"] = [
            p.strip() for p in ports_raw.split("port") if "LOCAL" not in p and p.strip()
        ]

        flow_table_raw = node.dpctl("dump-flows").strip()
        parsed_flows = []

        for line in flow_table_raw.split("\n"):
            line = line.strip()
            if not line:
                continue
            flow = {}
            match_fields = {}
            actions = None

            if " actions=" in line:
                line, actions = line.split(" actions=", 1)
            elif "actions=" in line:
                line, actions = line.split("actions=", 1)

            if actions is not None:
                flow["actions"] = actions.strip()

            fields = [f.strip() for f in line.split(",") if f.strip()]
            for field in fields:
                if "=" in field:
                    key, value = field.split("=", 1)
                    if key in FLOW_FIELDS:
                        flow[key] = value
                    else:
                        match_fields[key] = value
                else:
                    match_fields[field] = True

            flow["match_fields"] = match_fields
            parsed_flows.append(flow)
        result["flow_table"] = parsed_flows
    elif node.type in ("host", "router"):
        arp_table = node.cmd("arp -a -n")
        print("ARP TABLE", arp_table)
        parsed_arp_table = []
        for line in arp_table.splitlines():
            parts = line.split()
            if len(parts) < 6:
                continue
            ip = parts[1].strip("()")
            mac = parts[3]
            interface = parts[-1]
            parsed_arp_table.append({"ip": ip, "mac": mac, "interface": interface})
        result["arp_table"] = parsed_arp_table
        default_route = node.cmd("ip route show default").strip()
        result["default_route"] = default_route
        interfaces = []
        try:
            interfaces = [intf.name for intf in node.intfList() if intf.name != "lo"]
        except Exception:
            interfaces = []
        result["interfaces"] = interfaces

    result.pop("x", None)
    result.pop("y", None)

    return result


@app.post("/api/mininet/flows")
def add_flow(rule: FlowRuleCreate):
    if not state.net.is_started:
        raise HTTPException(
            status_code=400, detail="network must be started to add flows"
        )
    if rule.switch not in state.net.nameToNode:
        raise HTTPException(status_code=404, detail=f"Switch {rule.switch} not found")
    node = state.net.nameToNode[rule.switch]
    if getattr(node, "type", None) not in ("sw", "switch"):
        raise HTTPException(status_code=400, detail="node is not a switch")

    flow = build_flow(rule)
    cmd = ["ovs-ofctl"]
    if rule.of_version:
        cmd.extend(["-O", rule.of_version])
    cmd.extend(["add-flow", rule.switch, flow])
    result = subprocess.run(cmd, text=True, capture_output=True)
    if result.returncode != 0:
        detail = (result.stderr or result.stdout or "ovs-ofctl add-flow failed").strip()
        raise HTTPException(status_code=400, detail=detail)

    return {"status": "ok", "flow": flow}


@app.get("/api/mininet/flows/{switch_id}")
def list_flows(switch_id: str):
    if not state.net.is_started:
        raise HTTPException(
            status_code=400, detail="network must be started to list flows"
        )
    if switch_id not in state.net.nameToNode:
        raise HTTPException(status_code=404, detail=f"Switch {switch_id} not found")
    node = state.net.nameToNode[switch_id]
    if getattr(node, "type", None) not in ("sw", "switch"):
        raise HTTPException(status_code=400, detail="node is not a switch")

    cmd = ["ovs-ofctl", "dump-flows", switch_id]
    result = subprocess.run(cmd, text=True, capture_output=True)
    if result.returncode != 0:
        detail = (
            result.stderr or result.stdout or "ovs-ofctl dump-flows failed"
        ).strip()
        raise HTTPException(status_code=400, detail=detail)
    return {"switch": switch_id, "flows": result.stdout.strip()}


@app.delete("/api/mininet/flows")
def delete_flows(rule: FlowRuleDelete):
    if not state.net.is_started:
        raise HTTPException(
            status_code=400, detail="network must be started to delete flows"
        )
    if rule.switch not in state.net.nameToNode:
        raise HTTPException(status_code=404, detail=f"Switch {rule.switch} not found")
    node = state.net.nameToNode[rule.switch]
    if getattr(node, "type", None) not in ("sw", "switch"):
        raise HTTPException(status_code=400, detail="node is not a switch")

    match = build_flow_match(rule)
    cmd = ["ovs-ofctl"]
    if rule.of_version:
        cmd.extend(["-O", rule.of_version])
    if rule.strict:
        cmd.append("--strict")
    cmd.extend(["del-flows", rule.switch])
    if match:
        cmd.append(match)
    result = subprocess.run(cmd, text=True, capture_output=True)
    if result.returncode != 0:
        detail = (
            result.stderr or result.stdout or "ovs-ofctl del-flows failed"
        ).strip()
        raise HTTPException(status_code=400, detail=detail)

    return {"status": "ok", "match": match or "all"}


@app.delete("/api/mininet/flows/{switch_id}/{flow_id}")
def delete_flow_by_id(switch_id: str, flow_id: int):
    if not state.net.is_started:
        raise HTTPException(
            status_code=400, detail="network must be started to delete flows"
        )
    if switch_id not in state.net.nameToNode:
        raise HTTPException(status_code=404, detail=f"Switch {switch_id} not found")
    node = state.net.nameToNode[switch_id]
    if getattr(node, "type", None) not in ("sw", "switch"):
        raise HTTPException(status_code=400, detail="node is not a switch")
    if flow_id <= 0:
        raise HTTPException(status_code=400, detail="flow_id must be >= 1")

    dump = subprocess.run(
        ["ovs-ofctl", "dump-flows", switch_id], text=True, capture_output=True
    )
    if dump.returncode != 0:
        detail = (dump.stderr or dump.stdout or "ovs-ofctl dump-flows failed").strip()
        raise HTTPException(status_code=400, detail=detail)
    lines = [line for line in dump.stdout.splitlines() if "actions=" in line]
    if flow_id > len(lines):
        raise HTTPException(status_code=404, detail="flow_id not found")
    line = lines[flow_id - 1]
    try:
        match = parse_flow_match_from_dump(line)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    result = subprocess.run(
        ["ovs-ofctl", "--strict", "del-flows", switch_id, match],
        text=True,
        capture_output=True,
    )
    if result.returncode != 0:
        detail = (
            result.stderr or result.stdout or "ovs-ofctl del-flows failed"
        ).strip()
        raise HTTPException(status_code=400, detail=detail)
    return {"status": "ok", "match": match}


@app.post("/api/mininet/iperf")
async def run_iperf(request: IperfRequest, background_tasks: BackgroundTasks):
    if not state.net.is_started:
        raise HTTPException(
            status_code=400, detail="network must be started to run iperf"
        )
    if state.iperf_running:
        raise HTTPException(status_code=409, detail="iperf already running")
    if request.client == request.server:
        raise HTTPException(
            status_code=400, detail="client and server must be different hosts"
        )
    if (
        request.client not in state.net.nameToNode
        or request.server not in state.net.nameToNode
    ):
        raise HTTPException(status_code=404, detail="client or server host not found")
    client_node = state.net.nameToNode[request.client]
    server_node = state.net.nameToNode[request.server]
    if (
        getattr(client_node, "type", None) != "host"
        or getattr(server_node, "type", None) != "host"
    ):
        raise HTTPException(status_code=400, detail="client and server must be hosts")

    kwargs = {}
    if request.udp_bw:
        kwargs["udpBw"] = request.udp_bw
    if request.fmt:
        kwargs["fmt"] = request.fmt
    if request.seconds:
        kwargs["seconds"] = request.seconds
    if request.port:
        kwargs["port"] = request.port

    state.iperf_running = True
    state.iperf_result = None

    def _run():
        try:
            result = state.net.iperf(
                hosts=[client_node, server_node],
                l4Type=request.l4_type or "TCP",
                **kwargs,
            )
            if isinstance(result, (list, tuple)) and len(result) >= 2:
                state.iperf_result = {"client": result[0], "server": result[1]}
            else:
                state.iperf_result = {"result": str(result)}
        except Exception as exc:
            state.iperf_result = {"error": str(exc)}
        finally:
            state.iperf_running = False

    background_tasks.add_task(_run)
    return {"started": True}


@app.get("/api/mininet/iperf")
def get_iperf_result():
    if state.iperf_running:
        return {"running": True}
    if state.iperf_result is not None:
        result = state.iperf_result
        state.iperf_result = None
        return result
    return {"running": True}


@app.get("/api/mininet/export_script", response_class=PlainTextResponse)
def export_network():
    debug(state.net)
    return export_net_to_script(
        state.switches,
        state.hosts,
        state.controllers,
        state.nats,
        state.routers,
        state.links,
    ).encode("utf-8")


@app.get("/api/mininet/export_json", response_class=PlainTextResponse)
def export_network_json():
    debug(state.net)
    return export_net_to_json(
        state.switches,
        state.hosts,
        state.controllers,
        state.nats,
        state.routers,
        state.links,
    ).encode("utf-8")


@app.post("/api/mininet/import_json")
async def import_json(file: UploadFile = File(...)):
    contents = await file.read()

    try:
        data = json.loads(contents.decode("utf-8"))
        print("Received Topology JSON:", data)

        if "nodes" in data and "edges" in data:
            nodes = data.get("nodes") or []
            edges = data.get("edges") or []
            controllers = []
            switches = []
            hosts = []
            routers = []
            nats = []

            for node in nodes:
                node_type = (node.get("type") or "").lower()
                if node_type in ("controller", "ctl", "c"):
                    controllers.append(node)
                elif node_type in ("sw", "switch"):
                    switches.append(node)
                elif node_type in ("host", "h"):
                    hosts.append(node)
                elif node_type == "router":
                    routers.append(node)
                elif node_type == "nat":
                    nats.append(node)

            controller_ids = {c.get("id") for c in controllers if c.get("id")}
            switch_ids = {s.get("id") for s in switches if s.get("id")}
            switch_index = {s.get("id"): s for s in switches if s.get("id")}

            for edge in edges:
                src = edge.get("from")
                dst = edge.get("to")
                if not src or not dst:
                    continue
                if src in switch_ids and dst in controller_ids:
                    if not switch_index[src].get("controller"):
                        switch_index[src]["controller"] = dst
                elif dst in switch_ids and src in controller_ids:
                    if not switch_index[dst].get("controller"):
                        switch_index[dst]["controller"] = src

            links = []
            for edge in edges:
                src = edge.get("from")
                dst = edge.get("to")
                if not src or not dst:
                    continue
                if src in controller_ids or dst in controller_ids:
                    continue
                options = edge.get("options")
                if options is None:
                    links.append([src, dst])
                else:
                    links.append({"src": src, "dst": dst, "options": options})

            data = {
                "controllers": controllers,
                "switches": switches,
                "hosts": hosts,
                "routers": routers,
                "nats": nats,
                "links": links,
            }

        for controller_data in data.get("controllers", []):
            controller = Controller(**controller_data)
            create_controller(controller)

        for switch_data in data.get("switches", []):
            switch = Switch(**switch_data)
            controller = switch.controller
            switch.controller = None
            create_switch(switch)
            if controller:
                associate_switch({"switch": switch.id, "controller": controller})

        for host_data in data.get("hosts", []):
            host = Host(**host_data)
            create_host(host)

        for router_data in data.get("routers", []):
            router = Router(**router_data)
            create_router(router)

        for nat_data in data.get("nats", []):
            nat = Nat(**nat_data)
            create_nat(nat)

        for link in data.get("links", []):
            debug("LINKS: ", data["links"])
            debug("LINK: ", link)
            if isinstance(link, dict):
                create_link(LinkCreate(**link))
            else:
                create_link(tuple(link))

        return {"message": "Topology successfully imported"}

    except json.JSONDecodeError:
        return {"error": "Invalid JSON file"}, 400
