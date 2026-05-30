from fastapi import APIRouter, HTTPException
from fastapi.responses import Response
from mininet_gui_backend import app_state as state

router = APIRouter(prefix="/api/mininet/sniffer")

@router.get("/state")
def sniffer_state():
    return {"active": state.sniffer_manager.active}

@router.get("/history")
async def sniffer_history():
    return {"events": await state.sniffer_manager.get_history()}

@router.post("/start")
async def sniffer_start():
    if not getattr(state.net, "is_started", False):
        raise HTTPException(status_code=400, detail="network must be started to begin sniffing")
    await state.sniffer_manager.start()
    return {"active": state.sniffer_manager.active}

@router.post("/stop")
async def sniffer_stop():
    await state.sniffer_manager.stop()
    return {"active": state.sniffer_manager.active}

@router.get("/export")
async def sniffer_export():
    pcap_data = await state.sniffer_manager.get_pcap()
    return Response(
        content=pcap_data,
        media_type="application/vnd.tcpdump.pcap",
        headers={"Content-Disposition": "attachment; filename=sniffer.pcap"},
    )
