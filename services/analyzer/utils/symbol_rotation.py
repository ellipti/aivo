from __future__ import annotations

import json, time
from typing import Dict, List
from statistics import pstdev


def load_symbols(path: str = "configs/symbols.json"):
    return json.load(open(path, "r", encoding="utf-8"))


def pct_returns(prices: List[float]) -> List[float]:
    out: List[float] = []
    for i in range(1, len(prices)):
        if prices[i - 1] == 0:
            out.append(0.0)
        else:
            out.append((prices[i] / prices[i - 1]) - 1.0)
    return out


def corr(x: List[float], y: List[float]) -> float:
    n = min(len(x), len(y))
    if n < 5:
        return 0.0
    x = x[-n:]
    y = y[-n:]
    mx = sum(x) / n
    my = sum(y) / n
    num = sum((xi - mx) * (yi - my) for xi, yi in zip(x, y))
    den = (sum((xi - mx) ** 2 for xi in x) * sum((yi - my) ** 2 for yi in y)) ** 0.5
    return 0.0 if den == 0 else max(-1.0, min(1.0, num / den))


def realized_vol(returns: List[float]) -> float:
    if len(returns) < 10:
        return 0.0
    return pstdev(returns)


def build_rotation(price_history: Dict[str, List[float]], sym_cfg: dict, max_corr: float, min_vol: float) -> List[str]:
    universe = sym_cfg["universe"]
    scored = []
    local = {}
    for s, prices in price_history.items():
        if s not in universe or not universe[s]["enabled"]:
            continue
        rets = pct_returns(prices)
        vol = realized_vol(rets)
        if vol < min_vol:
            continue
        score = float(universe[s]["base_weight"]) * vol
        scored.append((s, score, rets))
        local[s] = {"rets": rets}
    scored.sort(key=lambda x: x[1], reverse=True)

    selected: List[str] = []
    for s, _score, rets in scored:
        ok = True
        for sel in selected:
            c = corr(rets, local[sel]["rets"])
            if abs(c) > max_corr:
                ok = False
                break
        if ok:
            selected.append(s)
    return selected


class Blacklist:
    def __init__(self, ttl_minutes: int = 120, loss_streak_threshold: int = 3, path: str = "blacklist.json"):
        self.ttl = ttl_minutes * 60
        self.th = loss_streak_threshold
        self.path = path
        self._load()

    def _load(self):
        import os, json

        if not os.path.exists(self.path):
            self.data = {}
        else:
            try:
                self.data = json.load(open(self.path, "r", encoding="utf-8"))
            except Exception:
                self.data = {}
        now = time.time()
        for k, v in list(self.data.items()):
            if now - v.get("ts", 0) > self.ttl:
                del self.data[k]

    def save(self):
        import json

        json.dump(self.data, open(self.path, "w", encoding="utf-8"), ensure_ascii=False, indent=2)

    def update_streak(self, symbol: str, won: bool):
        rec = self.data.get(symbol, {"ts": 0, "streak": 0, "blacklisted": False})
        rec["streak"] = 0 if won else rec.get("streak", 0) + 1
        rec["ts"] = time.time()
        rec["blacklisted"] = rec["streak"] >= self.th
        self.data[symbol] = rec
        self.save()

    def is_blacklisted(self, symbol: str) -> bool:
        self._load()
        return self.data.get(symbol, {}).get("blacklisted", False)


