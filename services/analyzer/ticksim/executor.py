from __future__ import annotations

from dataclasses import dataclass
from typing import List
from .loader import Tick
from .queue_model import QueueState, step_queue, filled


@dataclass
class ExecResult:
    ok: bool
    fill_price: float
    waited_ms: int
    slip_pts: float
    reason: str


def simulate_limit_fill(
    ticks: List[Tick],
    *,
    side: str,
    entry: float,
    sl: float,
    tp: float,
    lots: float,
    point: float,
    offset_pts: int,
    q_init: float,
    lam: float,
    mu: float,
    aggress: float,
    impact_k: float,
    max_wait_ms: int,
) -> ExecResult:
    if not ticks:
        return ExecResult(False, 0.0, 0, 0.0, "no_ticks")
    t0 = ticks[0].t
    px0 = ticks[0].bid if side == "BUY" else ticks[0].ask
    limit_px = (px0 - offset_pts * point) if side == "BUY" else (px0 + offset_pts * point)
    q = QueueState(best_px=limit_px, my_pos=q_init, depth=q_init)

    elapsed = 0
    for i in range(1, len(ticks)):
        dt = max(1, ticks[i].t - ticks[i - 1].t)
        q = step_queue(q, dt_ms=dt, arrival_lambda=lam, cancel_mu=mu, aggress_ratio=aggress, impact_k=impact_k)
        elapsed += dt
        if filled(q):
            slip_pts = abs(limit_px - entry) / max(point, 1e-9)
            return ExecResult(True, limit_px, elapsed, slip_pts, "filled")
        if elapsed >= max_wait_ms:
            return ExecResult(False, 0.0, elapsed, 0.0, "timeout")
    return ExecResult(False, 0.0, elapsed, 0.0, "ran_out")


