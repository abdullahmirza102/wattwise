import asyncio
import json
from datetime import datetime, timezone

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from sqlalchemy import func, and_, select

from app.core.database import AsyncSessionLocal
from app.models import EnergyReading, Device

router = APIRouter()


class ConnectionManager:
    def __init__(self):
        self.active_connections: dict[int, list[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, home_id: int):
        await websocket.accept()
        if home_id not in self.active_connections:
            self.active_connections[home_id] = []
        self.active_connections[home_id].append(websocket)

    def disconnect(self, websocket: WebSocket, home_id: int):
        if home_id in self.active_connections:
            self.active_connections[home_id] = [
                ws for ws in self.active_connections[home_id] if ws != websocket
            ]

    async def broadcast(self, home_id: int, data: dict):
        if home_id in self.active_connections:
            dead = []
            for ws in self.active_connections[home_id]:
                try:
                    await ws.send_json(data)
                except Exception:
                    dead.append(ws)
            for ws in dead:
                self.disconnect(ws, home_id)


manager = ConnectionManager()


@router.websocket("/ws/homes/{home_id}/live")
async def live_readings(websocket: WebSocket, home_id: int):
    await manager.connect(websocket, home_id)
    try:
        while True:
            # Poll latest readings every 5 seconds
            async with AsyncSessionLocal() as db:
                five_sec_ago = datetime.now(timezone.utc)

                # Get latest reading per device for this home
                result = await db.execute(
                    select(
                        Device.id.label("device_id"),
                        Device.name.label("device_name"),
                        Device.type.label("device_type"),
                        EnergyReading.kwh_consumed,
                        EnergyReading.voltage,
                        EnergyReading.current,
                        EnergyReading.power_factor,
                        EnergyReading.timestamp,
                    )
                    .join(Device, EnergyReading.device_id == Device.id)
                    .where(EnergyReading.home_id == home_id)
                    .order_by(EnergyReading.timestamp.desc())
                    .limit(10)
                )
                rows = result.all()

                # Compute total wattage
                total_watts = 0
                device_readings = []
                seen_devices = set()
                for r in rows:
                    if r.device_id in seen_devices:
                        continue
                    seen_devices.add(r.device_id)
                    watts = r.kwh_consumed * 12000  # 5-sec interval approx
                    total_watts += watts
                    device_readings.append({
                        "device_id": r.device_id,
                        "device_name": r.device_name,
                        "device_type": r.device_type,
                        "watts": round(watts, 1),
                        "voltage": r.voltage,
                        "current": r.current,
                        "power_factor": r.power_factor,
                        "timestamp": r.timestamp.isoformat() if r.timestamp else None,
                    })

                payload = {
                    "type": "live_update",
                    "home_id": home_id,
                    "total_watts": round(total_watts, 1),
                    "devices": device_readings,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }

            await websocket.send_json(payload)
            # Also check for client messages (like ping)
            try:
                await asyncio.wait_for(websocket.receive_text(), timeout=5.0)
            except asyncio.TimeoutError:
                pass
    except WebSocketDisconnect:
        manager.disconnect(websocket, home_id)
    except Exception:
        manager.disconnect(websocket, home_id)
