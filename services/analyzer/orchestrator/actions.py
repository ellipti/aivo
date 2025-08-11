from __future__ import annotations

from typing import Dict
from ..monitor.actions import apply_action
from ..utils.logger import info


def dispatch(action: dict, payload: dict):
    kind = action.get("action")
    if kind == "SAFE_MODE_ON":
        apply_action("SAFE_MODE")
        info("playbook.safe_mode", why=action.get("reason", ""))
    elif kind == "PAUSE":
        mins = int(action.get("minutes", 15))
        apply_action(f"PAUSE_{mins}M")
        info("playbook.pause", mins=mins)
    elif kind == "ROTATE_SYMBOL":
        sym = payload.get("symbol")
        info("playbook.rotate_symbol", symbol=sym, policy=action.get("policy"))
        # Integrate with symbol rotation module if needed
    elif kind == "NOTIFY":
        info("playbook.notify", msg=action.get("msg", "Playbook action executed."))
    else:
        info("playbook.unknown_action", action=str(kind))


