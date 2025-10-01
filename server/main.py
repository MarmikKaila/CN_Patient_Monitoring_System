import asyncio
import json
import os
from collections import deque
from typing import Any, Dict, Optional, Set, Tuple

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field

APP_HOST = os.getenv("APP_HOST", "0.0.0.0")
APP_PORT = int(os.getenv("APP_PORT", "8000"))
UDP_HOST = os.getenv("UDP_HOST", "0.0.0.0")
UDP_PORT = int(os.getenv("UDP_PORT", "9999"))
TCP_HOST = os.getenv("TCP_HOST", "0.0.0.0")
TCP_PORT = int(os.getenv("TCP_PORT", "9998"))

STATIC_DIR_DEFAULT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "web"))
STATIC_DIR = os.getenv("STATIC_DIR", STATIC_DIR_DEFAULT)

class VitalSigns(BaseModel):
    heart_rate: int = Field(ge=0, le=260)
    spo2: float = Field(ge=0.0, le=100.0)
    blood_pressure_sys: int = Field(ge=0, le=300)
    blood_pressure_dia: int = Field(ge=0, le=200)
    temperature: float = Field(ge=25.0, le=45.0)
    respiration_rate: int = Field(ge=0, le=80)

class TelemetryMessage(BaseModel):
    patient_id: str
    timestamp: float
    vitals: VitalSigns

class AlertMessage(BaseModel):
    patient_id: str
    timestamp: float
    type: str
    message: str
    severity: str

latest_vitals_by_patient: Dict[str, TelemetryMessage] = {}
recent_alerts: deque[AlertMessage] = deque(maxlen=20)

class WebSocketHub:
    def __init__(self) -> None:
        self._clients: Set[WebSocket] = set()
        self._lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        async with self._lock:
            self._clients.add(websocket)

    async def disconnect(self, websocket: WebSocket) -> None:
        async with self._lock:
            self._clients.discard(websocket)

    async def broadcast(self, message: Dict[str, Any]) -> None:
        data = json.dumps(message)
        async with self._lock:
            clients_snapshot = list(self._clients)
        if not clients_snapshot:
            return
        await asyncio.gather(
            *(self._send_safe(client, data) for client in clients_snapshot),
            return_exceptions=True,
        )

    async def _send_safe(self, websocket: WebSocket, data: str) -> None:
        try:
            await websocket.send_text(data)
        except Exception:
            await self.disconnect(websocket)

ws_hub = WebSocketHub()

class TelemetryDatagramProtocol(asyncio.DatagramProtocol):
    def __init__(self, loop: asyncio.AbstractEventLoop) -> None:
        self.loop = loop

    def datagram_received(self, data: bytes, addr: Tuple[str, int]) -> None:
        try:
            payload = json.loads(data.decode("utf-8"))
            telemetry = TelemetryMessage(**payload)
        except Exception:
            return
        latest_vitals_by_patient[telemetry.patient_id] = telemetry
        self.loop.create_task(
            ws_hub.broadcast({"type": "telemetry", "data": telemetry.model_dump()})
        )

udp_transport: Optional[asyncio.transports.DatagramTransport] = None

async def start_udp_server(loop: asyncio.AbstractEventLoop) -> None:
    global udp_transport
    transport, _ = await loop.create_datagram_endpoint(
        lambda: TelemetryDatagramProtocol(loop),
        local_addr=(UDP_HOST, UDP_PORT),
    )
    udp_transport = transport
    print(f"UDP server running on {UDP_HOST}:{UDP_PORT}")

async def stop_udp_server() -> None:
    global udp_transport
    if udp_transport is not None:
        udp_transport.close()
        udp_transport = None

tcp_server: Optional[asyncio.AbstractServer] = None
tcp_connections_count = 0

async def handle_alerts_client(reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
    global tcp_connections_count
    tcp_connections_count += 1
    print(f"TCP client connected! Active: {tcp_connections_count}")
    try:
        while True:
            line = await reader.readline()
            if not line:
                break
            try:
                payload = json.loads(line.decode("utf-8").strip())
                alert = AlertMessage(**payload)
            except Exception:
                continue
            recent_alerts.appendleft(alert)
            await ws_hub.broadcast({"type": "alert", "data": alert.model_dump()})
    except Exception as e:
        print(f"Error with TCP client: {e}")
    finally:
        try:
            writer.close()
            await writer.wait_closed()
        except Exception:
            pass
        tcp_connections_count -= 1
        print(f"TCP client disconnected! Active: {tcp_connections_count}")

async def start_tcp_server() -> None:
    global tcp_server
    tcp_server = await asyncio.start_server(handle_alerts_client, TCP_HOST, TCP_PORT)
    print(f"TCP server running on {TCP_HOST}:{TCP_PORT}")

async def stop_tcp_server() -> None:
    global tcp_server
    if tcp_server is not None:
        tcp_server.close()
        await tcp_server.wait_closed()
        tcp_server = None

app = FastAPI(title="CN Patient Monitor", version="1.0.0")

@app.get("/")
async def root():
    with open(STATIC_DIR + "/index.html", "r", encoding="utf-8") as f:
        return HTMLResponse(content=f.read(), status_code=200)

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    await ws_hub.connect(ws)
    try:
        snapshot = {
            "type": "snapshot",
            "data": {
                "patients": {k: v.model_dump() for k, v in latest_vitals_by_patient.items()},
                "alerts": [a.model_dump() for a in recent_alerts],
                "cn_info": {
                    "udp_port": UDP_PORT,
                    "tcp_port": TCP_PORT,
                    "ws_port": APP_PORT,
                },
            },
        }
        await ws.send_text(json.dumps(snapshot))
        while True:
            await ws.receive_text()
    except WebSocketDisconnect:
        await ws_hub.disconnect(ws)

@app.on_event("startup")
async def on_startup():
    loop = asyncio.get_running_loop()
    await start_udp_server(loop)
    await start_tcp_server()

    async def broadcast_cn_stats():
        while True:
            cn_stats = {
                "type": "cn_stats",
                "data": {
                    "udp_port": UDP_PORT,
                    "tcp_port": TCP_PORT,
                    "ws_port": APP_PORT,
                    "tcp_connections": tcp_connections_count
                },
            }
            await ws_hub.broadcast(cn_stats)
            await asyncio.sleep(5)

    asyncio.create_task(broadcast_cn_stats())

@app.on_event("shutdown")
async def on_shutdown():
    await stop_udp_server()
    await stop_tcp_server()
