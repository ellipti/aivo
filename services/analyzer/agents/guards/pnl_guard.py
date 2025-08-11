from __future__ import annotations

from ...utils.logger import warn
from ...orchestrator.runner import handle as run_playbooks


class PnLGuard:
    def __init__(self, limit_dd: float = -5.0):
        self.limit_dd = float(limit_dd)

    def check(self, stats: dict) -> bool:
        try:
            if float(stats.get("cum_r", 0.0)) <= self.limit_dd:
                warn("pnl_guard.trigger", reason="drawdown limit reached", limit=self.limit_dd, cum_r=stats.get("cum_r"))
                run_playbooks("PERF_CLIFF", {"symbol": stats.get("symbol"), "perf": stats})
                return True
        except Exception:
            pass
        return False


