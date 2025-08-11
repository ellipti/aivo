from __future__ import annotations

import csv
from dataclasses import dataclass
from typing import List


@dataclass
class Tick:
    t: int
    bid: float
    ask: float
    v: float


def load_ticks(path: str) -> List[Tick]:
    out: List[Tick] = []
    with open(path, "r", encoding="utf-8") as f:
        rdr = csv.DictReader(f)
        for r in rdr:
            out.append(Tick(t=int(r["time"]), bid=float(r["bid"]), ask=float(r["ask"]), v=float(r.get("volume", 0) or 0.0)))
    return out


