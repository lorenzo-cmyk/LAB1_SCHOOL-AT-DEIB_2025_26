import os
import pty
import asyncio
import uuid
import struct
import fcntl
import termios
from datetime import datetime, timezone

from fastapi import APIRouter, WebSocketDisconnect, WebSocket

from mininet_gui_backend import app_state as state
from mininet_gui_backend.api_helpers import (
    LOG_FILE,
    MONITOR_INTERVAL_SECONDS,
    debug,
    clear_log_file,
    list_mininet_interfaces,
    read_pty,
)
from mininet_gui_backend.utils import (
    get_interface_stats_path,
    read_interface_counter,
)

router = APIRouter()


@router.websocket("/api/mininet/terminal/{node_id}")
async def websocket_terminal(websocket: WebSocket, node_id: str):
    """WebSocket endpoint for accessing a Mininet node terminal"""
    await websocket.accept()
    if not getattr(state.net, "is_started", False):
        await websocket.send_text("Error: network must be started to open a webshell.")
        await websocket.close()
        return

    node = state.net.get(node_id)

    if not node:
        await websocket.send_text(f"Error: node {node_id} not found.")
        await websocket.close()
        return

    master_fd, slave_fd = pty.openpty()
    winsize = struct.pack("HHHH", 24, 80, 0, 0)
    fcntl.ioctl(slave_fd, termios.TIOCSWINSZ, winsize)

    env = dict(os.environ)
    env["PS1"] = f"root@{node_id}:\\w$ "
    process = node.popen(
        ["/bin/bash", "--noprofile", "--norc", "-i"],
        stdin=slave_fd,
        stdout=slave_fd,
        stderr=slave_fd,
        text=True,
        close_fds=True,
        env=env,
    )

    session_id = f"{node_id}-{uuid.uuid4().hex}"
    sessions = state.terminals.get(node_id, {})
    sessions[session_id] = (master_fd, process)
    state.terminals[node_id] = sessions

    asyncio.create_task(read_pty(master_fd, websocket))

    try:
        while True:
            data = await websocket.receive_text()
            debug("RECEIVED", data.encode())
            os.write(master_fd, data.encode())
    except WebSocketDisconnect:
        process.terminate()
        os.close(master_fd)
        sessions = state.terminals.get(node_id, {})
        sessions.pop(session_id, None)
        if not sessions:
            state.terminals.pop(node_id, None)
        else:
            state.terminals[node_id] = sessions



@router.websocket("/api/mininet/logs")
async def websocket_logs(websocket: WebSocket):
    await websocket.accept()
    if not os.path.exists(LOG_FILE):
        clear_log_file()
    process = await asyncio.create_subprocess_exec(
        "tail",
        "-n",
        "1000",
        "-f",
        LOG_FILE,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    try:
        while True:
            line = await process.stdout.readline()
            if not line:
                await asyncio.sleep(0.05)
                continue
            await websocket.send_text(line.decode(errors="ignore").rstrip())
    except WebSocketDisconnect:
        pass
    finally:
        process.terminate()


@router.websocket("/api/mininet/sniffer")
async def websocket_sniffer(websocket: WebSocket):
    """WebSocket endpoint for streaming tcpdump output on all Mininet interfaces"""
    await websocket.accept()

    if not state.net.is_started:
        await websocket.send_text("Error: network must be started to sniff.")
        await websocket.close()
        return

    nodes = list_mininet_interfaces()
    if not nodes:
        await websocket.send_text("Error: no Mininet nodes available to sniff.")
        await websocket.close()
        return

    queue = await state.sniffer_manager.subscribe()
    try:
        while True:
            event = await queue.get()
            await websocket.send_json(event)
    except WebSocketDisconnect:
        pass
    finally:
        await state.sniffer_manager.unsubscribe(queue)


@router.websocket("/api/mininet/monitor")
async def websocket_interface_monitor(websocket: WebSocket):
    """WebSocket endpoint that streams tx/rx traffic rates for a single interface"""
    await websocket.accept()

    if not getattr(state.net, "is_started", False):
        await websocket.send_text("Error: network must be started to monitor.")
        await websocket.close()
        return

    node_id = websocket.query_params.get("node")
    intf_name = websocket.query_params.get("intf")
    interval_param = websocket.query_params.get("interval")
    try:
        interval = float(interval_param) if interval_param else MONITOR_INTERVAL_SECONDS
    except (ValueError, TypeError):
        interval = MONITOR_INTERVAL_SECONDS
    interval = max(0.1, min(interval, 5.0))

    if not node_id or not intf_name:
        await websocket.send_text("Error: node and intf query parameters are required.")
        await websocket.close()
        return

    nodes = list_mininet_interfaces()
    node_info = next((node for node in nodes if node["id"] == node_id), None)
    if not node_info or intf_name not in node_info.get("intfs", []):
        await websocket.send_text(
            f"Error: interface {intf_name} for node {node_id} was not found."
        )
        await websocket.close()
        return

    stats = get_interface_stats_path(intf_name)
    tx_path = stats.get("tx")
    rx_path = stats.get("rx")
    if not tx_path or not rx_path or not os.path.isdir(os.path.dirname(tx_path)):
        await websocket.send_text(
            f"Error: statistics for interface {intf_name} are unavailable."
        )
        await websocket.close()
        return

    last_tx = None
    last_rx = None
    last_time = None
    try:
        while True:
            current_time = datetime.now(timezone.utc)
            tx_bytes = read_interface_counter(tx_path)
            rx_bytes = read_interface_counter(rx_path)
            if tx_bytes is None or rx_bytes is None:
                await websocket.send_text(
                    f"Error: failed to read counters for {intf_name}."
                )
                break

            if last_tx is not None and last_rx is not None and last_time:
                elapsed = (current_time - last_time).total_seconds()
                if elapsed > 0:
                    tx_delta = max(0, tx_bytes - last_tx)
                    rx_delta = max(0, rx_bytes - last_rx)
                    tx_gbps = (tx_delta * 8) / elapsed / 1e9
                    rx_gbps = (rx_delta * 8) / elapsed / 1e9
                    payload = {
                        "node": node_id,
                        "intf": intf_name,
                        "ts": current_time.isoformat(),
                        "tx_gbps": tx_gbps,
                        "rx_gbps": rx_gbps,
                    }
                    await websocket.send_json(payload)

            last_tx = tx_bytes
            last_rx = rx_bytes
            last_time = current_time
            await asyncio.sleep(interval)
    except WebSocketDisconnect:
        pass
    except Exception as exc:
        debug(f"Monitor WebSocket error: {exc}")
    finally:
        try:
            await websocket.close()
        except Exception:
            pass
