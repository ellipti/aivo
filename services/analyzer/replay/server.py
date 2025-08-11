from __future__ import annotations

from fastapi import FastAPI
from fastapi.responses import StreamingResponse
import asyncio, json

app = FastAPI()


@app.get("/replay")
async def replay_stream(path: str = "bt_events.jsonl", speed: float = 1.0):
    async def gen():
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                try:
                    ev = json.loads(line.strip())
                except Exception:
                    continue
                yield f"data: {json.dumps(ev)}\n\n"
                await asyncio.sleep(max(0.01, 0.2 / float(speed)))

    return StreamingResponse(gen(), media_type="text/event-stream")


