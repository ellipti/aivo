from fastapi import APIRouter
from fastapi.responses import StreamingResponse
import asyncio, json, time
from .exposure_api import exposure_snapshot, heatmap

router = APIRouter(prefix="/dashboard", tags=["dashboard-sse"])

MIN_PUSH_MS = json.load(open("configs/dashboard.json", "r", encoding="utf-8"))["sse"]["min_push_ms"]


@router.get("/stream")
async def stream():
    async def gen():
        while True:
            snap = exposure_snapshot()
            hm = heatmap()
            payload = {"type": "tick", "exposure": snap, "heatmap": hm, "ts": int(time.time())}
            yield f"data: {json.dumps(payload)}\n\n"
            await asyncio.sleep(max(0.2, MIN_PUSH_MS / 1000.0))
    return StreamingResponse(gen(), media_type="text/event-stream")


