from __future__ import annotations

import json, time
from typing import Dict, Any

from .param_store import get_params, update_params
from .bo_opt import run_bo


class OptimizerEngine:
    def __init__(self, cfg_path: str = "configs/optimizer.json"):
        self.cfg = json.load(open(cfg_path, "r", encoding="utf-8"))
        self.last_run_ts = 0.0

    def _cooldown_ok(self) -> bool:
        return (time.time() - self.last_run_ts) >= 60 * float(self.cfg.get("cooldown_minutes", 180))

    def objective(self, strategy_id: str, params: Dict[str, Any]) -> float:
        # TODO: wire your backtest/forward metric here; must return negative of score (for minimization)
        # For placeholder, return -avg R over recent trades of this strategy
        return 0.0

    def try_optimize(self, strategy_id: str) -> Dict[str, Any]:
        st = next((s for s in self.cfg["strategies"] if s["id"] == strategy_id), None)
        if not st:
            return {"ok": False, "reason": "unknown_strategy"}
        if not self._cooldown_ok():
            return {"ok": False, "reason": "cooldown"}
        dims = st["dimensions"]
        n_calls = int(st.get("n_calls", 20))
        def obj(p):
            return self.objective(strategy_id, p)
        best, fun = run_bo(obj, dims, n_calls=n_calls)
        # Acceptance (placeholder)
        old = get_params(strategy_id)
        update_params(strategy_id, best)
        self.last_run_ts = time.time()
        return {"ok": True, "strategy": strategy_id, "best": best, "score": float(-fun), "prev": old}


