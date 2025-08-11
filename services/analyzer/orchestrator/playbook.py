from __future__ import annotations

import json, operator, time
from typing import Dict, Any, List

OPS = {">": operator.gt, "<": operator.lt, ">=": operator.ge, "<=": operator.le, "==": operator.eq, "!=": operator.ne}


class PlaybookEngine:
    def __init__(self, cfg_path: str = "configs/playbooks.json"):
        self.cfg_path = cfg_path
        self.cfg = json.load(open(cfg_path, "r", encoding="utf-8"))
        self.cooldowns: Dict[str, float] = {}

    def _cooldown_ok(self, pbid: str) -> bool:
        cd = 60 * self.cfg.get("globals", {}).get("cooldown_minutes", 10)
        last = self.cooldowns.get(pbid, 0.0)
        return (time.time() - last) >= cd

    def _metrics_get(self, payload: dict, key: str, default=None):
        cur = payload
        for k in key.split("."):
            if isinstance(cur, dict):
                cur = cur.get(k, {})
            else:
                cur = {}
        return cur if cur != {} else default

    def eval(self, event: str, payload: dict) -> List[dict]:
        actions: List[dict] = []
        for pb in self.cfg.get("playbooks", []):
            w = pb.get("when", {})
            if w.get("event") != event:
                continue
            if not self._cooldown_ok(pb["id"]):
                continue
            if "symbols" in w and payload.get("symbol") not in w["symbols"]:
                continue
            ok = True
            for cond in pb.get("if", []):
                lhs = self._metrics_get(payload, cond["metric"], None)
                if lhs is None or not OPS[cond["op"]](lhs, cond["value"]):
                    ok = False
                    break
            if not ok:
                continue
            for a in pb.get("then", []):
                actions.append({"playbook": pb["id"], **a})
            self.cooldowns[pb["id"]] = time.time()
        return actions


