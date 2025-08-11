from __future__ import annotations

import csv
from dataclasses import dataclass
from typing import List


@dataclass
class Bar:
    t: int
    o: float
    h: float
    l: float
    c: float
    v: float
    spr: float


def load_m1_csv(path: str) -> List[Bar]:
    out: List[Bar] = []
    with open(path, "r", encoding="utf-8") as f:
        rdr = csv.DictReader(f)
        for r in rdr:
            spr = float(r.get("spread", 0) or 0.0)
            out.append(
                Bar(
                    t=int(r["time"]),
                    o=float(r["open"]),
                    h=float(r["high"]),
                    l=float(r["low"]),
                    c=float(r["close"]),
                    v=float(r.get("volume", 0) or 0.0),
                    spr=spr,
                )
            )
    return out


@dataclass
class Tick:
    t: int
    bid: float
    ask: float
    v: float


def load_tick_csv(path: str) -> List[Tick]:
    out: List[Tick] = []
    with open(path, "r", encoding="utf-8") as f:
        rdr = csv.DictReader(f)
        for r in rdr:
            out.append(Tick(t=int(r["time"]), bid=float(r["bid"]), ask=float(r["ask"]), v=float(r.get("volume", 0) or 0.0)))
    return out


