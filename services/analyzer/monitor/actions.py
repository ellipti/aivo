from __future__ import annotations

import time, json, os

STAMP = ".aivo.guard.stamp"


def _write_guard(kind: str, minutes: int):
    with open(STAMP, "w", encoding="utf-8") as f:
        f.write(json.dumps({"kind": kind, "until": time.time() + minutes * 60}))


def is_paused() -> tuple[bool, str]:
    if not os.path.exists(STAMP):
        return (False, "")
    try:
        d = json.load(open(STAMP, "r", encoding="utf-8"))
    except Exception:
        return (False, "")
    if time.time() < d.get("until", 0):
        return (True, d.get("kind", "PAUSE"))
    else:
        try:
            os.remove(STAMP)
        except Exception:
            pass
        return (False, "")


def apply_action(action: str):
    if action == "PAUSE_15M":
        _write_guard("PAUSE_15M", 15)
    elif action == "PAUSE_2H":
        _write_guard("PAUSE_2H", 120)
    elif action == "SAFE_MODE":
        with open(".aivo.safe_mode", "w", encoding="utf-8") as f:
            f.write("1")
    else:
        pass


