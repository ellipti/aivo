from __future__ import annotations

import json
import sys
import os
import datetime
import threading

_LOG_PATH = os.environ.get("AIVO_LOG_PATH", "aivo.log")
_LOCK = threading.Lock()


def _ts() -> str:
    return datetime.datetime.utcnow().isoformat()


def log(level: str, msg: str, **kv) -> None:
    rec = {"ts": _ts(), "level": level.upper(), "msg": msg}
    if kv:
        rec.update(kv)
    line = json.dumps(rec, ensure_ascii=False)
    with _LOCK:
        sys.stdout.write(line + "\n")
        sys.stdout.flush()
        try:
            with open(_LOG_PATH, "a", encoding="utf-8") as f:
                f.write(line + "\n")
        except Exception:
            # ignore file write issues
            pass


def info(msg, **kv):
    log("INFO", msg, **kv)


def warn(msg, **kv):
    log("WARN", msg, **kv)


def error(msg, **kv):
    log("ERROR", msg, **kv)


