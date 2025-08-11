from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Dict, Any

import os
import redis

REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
STREAM_KEY = os.getenv("AIVO_STREAM_KEY", "aivo_events")

r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)


def publish_event(event_type: str, payload: Dict[str, Any]) -> None:
    event = {
        "type": event_type,
        "time": datetime.now(timezone.utc).isoformat(),
        **payload,
    }
    try:
        r.xadd(STREAM_KEY, {"data": json.dumps(event)}, maxlen=5000)
    except Exception:
        # publishing must not crash core flow
        pass


