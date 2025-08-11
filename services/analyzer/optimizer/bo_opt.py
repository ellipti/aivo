from __future__ import annotations

import json, time
from typing import Dict, Any, List, Tuple

try:
    from skopt import gp_minimize
    from skopt.space import Real, Integer
    SKOPT_OK = True
except Exception:
    SKOPT_OK = False


def _dim_space(dim: Dict[str, List[float]]):
    space = []
    for k, v in dim.items():
        a, b = v
        if isinstance(a, int) and isinstance(b, int):
            space.append(Integer(int(a), int(b), name=k))
        else:
            space.append(Real(float(a), float(b), name=k))
    return space


def run_bo(objective_fn, dimensions: Dict[str, List[float]], n_calls: int = 30) -> Tuple[Dict[str, Any], float]:
    if not SKOPT_OK:
        return ({}, 0.0)
    keys = list(dimensions.keys())
    space = _dim_space(dimensions)

    def obj(x_list):
        params = {k: x for k, x in zip(keys, x_list)}
        return float(objective_fn(params))

    res = gp_minimize(obj, space, n_calls=n_calls, random_state=42)
    best = {k: v for k, v in zip(keys, res.x)}
    return best, float(res.fun)


