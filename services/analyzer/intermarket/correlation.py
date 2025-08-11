from __future__ import annotations

from typing import List, Dict
import json


CFG = json.load(open("configs/intermarket.json", "r", encoding="utf-8"))


def _pct_returns(series: List[float]) -> List[float]:
    out: List[float] = []
    for i in range(1, len(series)):
        a = series[i - 1]
        b = series[i]
        out.append(((b / a) - 1.0) if a != 0 else 0.0)
    return out


def pearson(a: List[float], b: List[float]) -> float:
    n = min(len(a), len(b))
    if n < 5:
        return 0.0
    ax = a[-n:]
    bx = b[-n:]
    ma = sum(ax) / n
    mb = sum(bx) / n
    num = sum((x - ma) * (y - mb) for x, y in zip(ax, bx))
    den = (sum((x - ma) ** 2 for x in ax) * sum((y - mb) ** 2 for y in bx)) ** 0.5 or 1e-9
    v = num / den
    return max(-1.0, min(1.0, v))


def spearman(a: List[float], b: List[float]) -> float:
    # Simple rank correlation
    n = min(len(a), len(b))
    if n < 5:
        return 0.0
    from math import sqrt

    def ranks(x: List[float]):
        order = sorted(range(len(x)), key=lambda i: x[i])
        r = [0] * len(x)
        for i, idx in enumerate(order):
            r[idx] = i + 1
        return r

    ra = ranks(a[-n:])
    rb = ranks(b[-n:])
    d2 = sum((x - y) ** 2 for x, y in zip(ra, rb))
    return 1 - 6 * d2 / (n * (n * n - 1))


def calc(method: str, close_a: List[float], close_b: List[float]) -> float:
    a = _pct_returns(close_a)
    b = _pct_returns(close_b)
    return pearson(a, b) if method == "pearson" else spearman(a, b)


def evaluate(payload: Dict[str, List[float]]) -> Dict[str, float]:
    out: Dict[str, float] = {}
    for pr in CFG["pairs"]:
        a = pr["a"]
        b = pr["b"]
        v = calc(pr.get("method", "pearson"), payload.get(a, []), payload.get(b, []))
        if pr.get("relation") == "inverse":
            v = -v
        out[f"{a}/{b}"] = v
    return out


