from __future__ import annotations

from dataclasses import dataclass
import math, random


@dataclass
class QueueState:
    best_px: float
    my_pos: float
    depth: float


def step_queue(q: QueueState, dt_ms: int, arrival_lambda: float, cancel_mu: float, aggress_ratio: float, impact_k: float) -> QueueState:
    dt_s = max(1e-6, dt_ms / 1000.0)
    if hasattr(random, "poisson"):
        arr = random.poisson(lam=arrival_lambda * dt_s)  # type: ignore[attr-defined]
    else:
        p = min(1.0, arrival_lambda * dt_s / 100.0)
        arr = sum(1 for _ in range(100) if random.random() < p)
    eat = arr * aggress_ratio * impact_k
    canc = q.depth * (1 - math.exp(-cancel_mu * dt_s))
    eat_amt = min(q.depth, eat)
    q.depth = max(0.0, q.depth - eat_amt - canc)
    front_cut = min(q.my_pos, eat_amt + canc * (q.my_pos / max(1e-9, q.depth + q.my_pos)))
    q.my_pos = max(0.0, q.my_pos - front_cut)
    return q


def filled(q: QueueState) -> bool:
    return q.my_pos <= 1e-6


