from __future__ import annotations

import json
from typing import Any, Dict, List

from .guards.pnl_guard import PnLGuard
from .recovery.mt5_reconnect import MT5Reconnect
from ..utils.logger import info


class SwarmCoordinator:
    def __init__(self, cfg_path: str = "configs/swarm.json"):
        self.cfg = json.load(open(cfg_path, "r", encoding="utf-8"))
        self.guards: List[Any] = []
        self.recovery: List[Any] = []
        for g in self.cfg.get("guards", []):
            if g.get("type") == "PNL_GUARD":
                self.guards.append(PnLGuard(**g.get("params", {})))
        for r in self.cfg.get("recovery", []):
            if r.get("type") == "MT5_RECONNECT":
                self.recovery.append(MT5Reconnect())

    def run_cycle(self, context: Dict[str, Any]):
        triggered = False
        for g in self.guards:
            try:
                if g.check(context.get("stats", {})):
                    triggered = True
            except Exception:
                pass
        if triggered:
            info("swarm.triggered")
            for r in self.recovery:
                try:
                    r.attempt()
                except Exception:
                    pass


