from fastapi import APIRouter
from typing import Dict, List

router = APIRouter(prefix="/dashboard", tags=["correlation"])


def _pct_returns(prices: List[float]) -> List[float]:
    out: List[float] = []
    for i in range(1, len(prices)):
        prev = prices[i - 1]
        out.append(((prices[i] / prev) - 1.0) if prev != 0 else 0.0)
    return out


def _corr(a: List[float], b: List[float]) -> float:
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


@router.post("/corr")
def corr_matrix(payload: Dict[str, List[float]]):
    syms = list(payload.keys())
    rets = {s: _pct_returns(payload[s]) for s in syms}
    mat = []
    for s1 in syms:
        row = []
        for s2 in syms:
            row.append(_corr(rets[s1], rets[s2]))
        mat.append(row)
    return {"symbols": syms, "matrix": mat}


