from __future__ import annotations
from typing import List, Dict
from ..utils.stats_tools import ks_stat, psi


def collect_features(rows: List[Dict]) -> Dict[str, List[float]]:
    out = {"ret": [], "range": [], "body": [], "vol": []}
    for i in range(1, len(rows)):
        c = rows[i]
        p = rows[i - 1]
        ret = (c["close"] / p["close"] - 1.0)
        rng = (c["high"] - c["low"]) / max(1e-9, p["close"])
        body = abs(c["close"] - c["open"]) / max(1e-9, p["close"])
        vol = float(c.get("tick_volume", c.get("volume", 0.0)))
        out["ret"].append(ret)
        out["range"].append(rng)
        out["body"].append(body)
        out["vol"].append(vol)
    return out


def drift_tests(ref_features: Dict[str, List[float]], cur_features: Dict[str, List[float]], ks_th: float, psi_th: float):
    res = {}
    for k in ref_features.keys():
        ks = ks_stat(ref_features[k], cur_features[k])
        ps = psi(ref_features[k], cur_features[k])
        res[k] = {"ks": round(ks, 3), "psi": round(ps, 3), "drift": (ks > ks_th or ps > psi_th)}
    return res


