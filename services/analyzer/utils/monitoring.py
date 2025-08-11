import json, math, time
from pathlib import Path
from dataclasses import dataclass
from typing import Dict, Any, List, Optional, Tuple
import numpy as np

try:
    from scipy.stats import ks_2samp
    SCIPY_OK = True
except Exception:
    SCIPY_OK = False

# ---------- Config ----------
BASELINE_PATH = Path("storage/drift_baseline.json")
METRICS_PATH = Path("storage/perf_metrics.json")
BASELINE_EMA_ALPHA = 0.05


def _safe_mkdir(p: Path):
    p.parent.mkdir(parents=True, exist_ok=True)


def _psi(expected: np.ndarray, actual: np.ndarray, bins: int = 20) -> float:
    expected = expected[np.isfinite(expected)]
    actual = actual[np.isfinite(actual)]
    if len(expected) < 50 or len(actual) < 50:
        return 0.0
    qs = np.quantile(expected, np.linspace(0, 1, bins + 1))
    qs[0], qs[-1] = -np.inf, np.inf
    e_hist = np.histogram(expected, bins=qs)[0] / max(len(expected), 1)
    a_hist = np.histogram(actual, bins=qs)[0] / max(len(actual), 1)
    e_hist = np.clip(e_hist, 1e-6, None)
    a_hist = np.clip(a_hist, 1e-6, None)
    return float(np.sum((a_hist - e_hist) * np.log(a_hist / e_hist)))


def _zscore(x: np.ndarray) -> np.ndarray:
    x = x.astype(float)
    mu = np.nanmean(x)
    sd = np.nanstd(x) + 1e-9
    return (x - mu) / sd


def _cusum_shift(series: np.ndarray) -> float:
    x = series[np.isfinite(series)].astype(float)
    if len(x) < 50:
        return 0.0
    mu = np.mean(x)
    sd = np.std(x) + 1e-9
    k = 0.5 * sd
    pos = 0.0
    neg = 0.0
    smax = 0.0
    for v in x:
        pos = max(0.0, pos + (v - mu - k))
        neg = min(0.0, neg + (v - mu + k))
        smax = max(smax, abs(pos), abs(neg))
    return smax / (sd + 1e-9)


@dataclass
class DriftAction:
    level: int
    reason: str
    details: Dict[str, Any]
    timestamp: float


@dataclass
class MonitorConfig:
    symbol: str = "XAUUSD"
    timeframe: str = "M30"
    gap_tol_multiplier: float = 2.0
    spike_z: float = 5.0
    zero_volume_pct: float = 0.01
    psi_warn: float = 0.2
    psi_block: float = 0.3
    ks_p_block: float = 0.01
    cusum_sigma_block: float = 3.0
    winrate_drop_pct: float = 0.15
    dd_growth_factor: float = 2.0
    degrade_pos_factor: float = 0.5
    tighten_sl_atr: float = 0.5
    safe_pause_candles: int = 20


class DriftMonitor:
    def __init__(self, cfg: MonitorConfig, send_telegram=None, logger_print=print):
        self.cfg = cfg
        self.send_telegram = send_telegram or (lambda msg: None)
        self.log = logger_print
        _safe_mkdir(BASELINE_PATH)
        self.baseline = self._load_json(BASELINE_PATH, default={})
        self.metrics = self._load_json(METRICS_PATH, default={"trades": [], "equity": []})

    @staticmethod
    def _load_json(path: Path, default: Any) -> Any:
        try:
            if path.exists():
                return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            pass
        return default

    @staticmethod
    def _dump_json(path: Path, obj: Any):
        _safe_mkdir(path)
        path.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")

    # ---------- Integrity ----------
    def check_integrity(self, candles: List[Dict[str, Any]], timeframe_sec: int) -> List[str]:
        issues = []
        if not candles or len(candles) < 50:
            return ["INSUFFICIENT_DATA"]

        times = np.array([c["time"] for c in candles], dtype=float)
        vols = np.array([c.get("tick_volume", np.nan) for c in candles], dtype=float)
        highs = np.array([c["high"] for c in candles], dtype=float)
        lows = np.array([c["low"] for c in candles], dtype=float)
        closes = np.array([c["close"] for c in candles], dtype=float)

        diffs = np.diff(times)
        if np.any(diffs > self.cfg.gap_tol_multiplier * timeframe_sec):
            issues.append("CANDLE_GAP")

        zero_pct = float(np.mean(vols == 0))
        if zero_pct > self.cfg.zero_volume_pct:
            issues.append(f"ZERO_VOLUME_{zero_pct:.3f}")

        rng = highs - lows
        if float(np.mean(rng == 0)) > 0.01:
            issues.append("FLAT_BARS")

        returns = np.diff(closes) / (closes[:-1] + 1e-9)
        if np.any(np.abs(_zscore(returns)) > self.cfg.spike_z):
            issues.append("SPIKE_OUTLIERS")

        return issues

    # ---------- Feature Drift ----------
    def compute_features(self, candles: List[Dict[str, Any]]) -> Dict[str, np.ndarray]:
        closes = np.array([c["close"] for c in candles], dtype=float)
        highs = np.array([c["high"] for c in candles], dtype=float)
        lows = np.array([c["low"] for c in candles], dtype=float)

        def ema(x, n):
            a = 2 / (n + 1)
            y = np.zeros_like(x)
            y[0] = x[0]
            for i in range(1, len(x)):
                y[i] = a * x[i] + (1 - a) * y[i - 1]
            return y

        ret = np.diff(closes, prepend=closes[0]) / (closes + 1e-9)
        tr = np.maximum(highs - lows, np.maximum(np.abs(highs - np.roll(closes, 1)), np.abs(lows - np.roll(closes, 1))))
        tr[0] = highs[0] - lows[0]
        atr = ema(tr, 14)
        ema50 = ema(closes, 50)
        ema200 = ema(closes, 200)
        ma_slope = np.gradient(ema50)

        macd = ema(closes, 12) - ema(closes, 26)
        signal = ema(macd, 9)
        macd_hist = macd - signal

        rsi = self._rsi(closes, 14)

        return {"ret": ret, "atr": atr, "ema50": ema50, "ema200": ema200, "ma_slope": ma_slope, "macd_hist": macd_hist, "rsi": rsi}

    @staticmethod
    def _rsi(prices: np.ndarray, n: int) -> np.ndarray:
        diff = np.diff(prices, prepend=prices[0])
        up = np.clip(diff, 0, None)
        down = -np.clip(diff, None, 0)
        ema_up = np.convolve(up, np.ones(n) / n, mode="same")
        ema_dn = np.convolve(down, np.ones(n) / n, mode="same") + 1e-9
        rs = ema_up / ema_dn
        rsi = 100 - (100 / (1 + rs))
        return rsi

    def _bootstrap_baseline(self, feats: Dict[str, np.ndarray]):
        for k, v in feats.items():
            self.baseline.setdefault(k, {"mu": float(np.nanmean(v)), "sd": float(np.nanstd(v) + 1e-9), "samples": 1000})
        self._dump_json(BASELINE_PATH, self.baseline)

    def _update_baseline(self, feats: Dict[str, np.ndarray]):
        for k, v in feats.items():
            mu0 = self.baseline[k]["mu"]
            sd0 = self.baseline[k]["sd"]
            mu1 = float(np.nanmean(v))
            sd1 = float(np.nanstd(v) + 1e-9)
            self.baseline[k]["mu"] = (1 - BASELINE_EMA_ALPHA) * mu0 + BASELINE_EMA_ALPHA * mu1
            self.baseline[k]["sd"] = (1 - BASELINE_EMA_ALPHA) * sd0 + BASELINE_EMA_ALPHA * sd1
        self._dump_json(BASELINE_PATH, self.baseline)

    def feature_drift(self, feats: Dict[str, np.ndarray]) -> Dict[str, Dict[str, float]]:
        results = {}
        for k, v in feats.items():
            if k not in self.baseline:
                self._bootstrap_baseline(feats)
                break
        for k, v in feats.items():
            mu = self.baseline[k]["mu"]
            sd = self.baseline[k]["sd"]
            rng = len(v)
            synth = np.random.normal(mu, max(sd, 1e-6), size=rng)
            psi = _psi(synth, v, bins=20)
            ks_p = 1.0
            if SCIPY_OK:
                try:
                    ks_p = ks_2samp(synth, v, alternative="two-sided", mode="auto").pvalue
                except Exception:
                    ks_p = 1.0
            results[k] = {"psi": float(psi), "ks_p": float(ks_p)}
        return results

    # ---------- Performance Drift ----------
    def record_trade(self, pnl_r: float, was_win: bool, equity: float):
        self.metrics.setdefault("trades", []).append({"pnl_r": pnl_r, "win": int(was_win), "ts": time.time()})
        self.metrics.setdefault("equity", []).append(equity)
        self._dump_json(METRICS_PATH, self.metrics)

    def performance_drift(self) -> Dict[str, float]:
        trades = self.metrics.get("trades", [])[-30:]
        equity = self.metrics.get("equity", [])[-300:]
        if len(trades) < 10 or len(equity) < 50:
            return {"winrate": 1.0, "avg_r": 0.0, "dd": 0.0, "cusum": 0.0}
        wins = [t["win"] for t in trades]
        pnlr = [t["pnl_r"] for t in trades]
        winrate = float(np.mean(wins))
        avg_r = float(np.mean(pnlr))
        eq = np.array(equity, dtype=float)
        peak = np.maximum.accumulate(eq)
        dd = float(np.max((peak - eq) / np.maximum(peak, 1e-9)))
        cusum = _cusum_shift(eq)
        return {"winrate": winrate, "avg_r": avg_r, "dd": dd, "cusum": cusum}

    # ---------- Decision ----------
    def decide_action(self, integrity_issues: List[str], feat_stats: Dict[str, Dict[str, float]], perf_stats: Dict[str, float]) -> DriftAction:
        lvl = 0
        reasons: List[str] = []

        if integrity_issues:
            reasons.append(f"Integrity:{'|'.join(integrity_issues)}")
            lvl = max(lvl, 2 if any(x in ["CANDLE_GAP", "SPIKE_OUTLIERS"] for x in integrity_issues) else 1)

        max_psi = max((s["psi"] for s in feat_stats.values()), default=0.0)
        min_ksp = min((s["ks_p"] for s in feat_stats.values()), default=1.0)
        if max_psi > self.cfg.psi_warn:
            lvl = max(lvl, 1)
            reasons.append(f"PSI={max_psi:.2f}")
        if max_psi > self.cfg.psi_block or min_ksp < self.cfg.ks_p_block:
            lvl = max(lvl, 2)
            reasons.append(f"KS_p={min_ksp:.3f}")

        wr = perf_stats.get("winrate", 1.0)
        avg_r = perf_stats.get("avg_r", 0.0)
        dd = perf_stats.get("dd", 0.0)
        cusum = perf_stats.get("cusum", 0.0)

        base_wr = float(self.baseline.get("_winrate", 0.58))
        base_dd = float(self.baseline.get("_dd", 0.10))
        if wr < (base_wr - self.cfg.winrate_drop_pct):
            lvl = max(lvl, 2)
            reasons.append(f"WinRate↓ {wr:.2f} < {base_wr:.2f}-{self.cfg.winrate_drop_pct:.2f}")
        if dd > (self.cfg.dd_growth_factor * base_dd):
            lvl = max(lvl, 2)
            reasons.append(f"DD↑ {dd:.2f} > {self.cfg.dd_growth_factor:.1f}×{base_dd:.2f}")
        if cusum > self.cfg.cusum_sigma_block:
            lvl = max(lvl, 3)
            reasons.append(f"CUSUM {cusum:.2f}σ")

        return DriftAction(level=lvl, reason="; ".join(reasons), details={"max_psi": max_psi, "min_ksp": min_ksp, "wr": wr, "avg_r": avg_r, "dd": dd, "cusum": cusum}, timestamp=time.time())

    def apply_policy(self, action: DriftAction) -> Dict[str, Any]:
        policy: Dict[str, Any] = {"trade_allowed": True, "pos_factor": 1.0, "sl_tighten_atr": 0.0, "confirm_extra": 0, "pause_candles": 0, "safe_mode": False}
        if action.level == 0:
            return policy
        if action.level == 1:
            self._notify(f"⚠️ Drift Warning: {action.reason}")
            policy["confirm_extra"] = 1
            return policy
        if action.level == 2:
            self._notify(f"🟠 Drift Degrade: {action.reason}\n→ size×{self.cfg.degrade_pos_factor}, SL tighten +{self.cfg.tighten_sl_atr}*ATR")
            policy.update({"pos_factor": self.cfg.degrade_pos_factor, "sl_tighten_atr": self.cfg.tighten_sl_atr, "confirm_extra": 1})
            return policy
        if action.level >= 3:
            self._notify(f"🔴 Safe-Mode: {action.reason}\n→ WAIT only, pause {self.cfg.safe_pause_candles} candles")
            policy.update({"trade_allowed": False, "safe_mode": True, "pause_candles": self.cfg.safe_pause_candles})
            return policy

    def _notify(self, msg: str):
        try:
            self.send_telegram(msg)
        except Exception:
            self.log(msg)

    def pre_trade_guard(self, candles: List[Dict[str, Any]], timeframe_sec: int) -> Tuple[Dict[str, Any], DriftAction]:
        issues = self.check_integrity(candles, timeframe_sec)
        feats = self.compute_features(candles[-300:])
        if not self.baseline:
            self._bootstrap_baseline(feats)
        feat_stats = self.feature_drift(feats)
        perf_stats = self.performance_drift()
        action = self.decide_action(issues, feat_stats, perf_stats)
        policy = self.apply_policy(action)
        if action.level <= 1:
            self._update_baseline(feats)
            if "trades" in self.metrics and len(self.metrics["trades"]) >= 50:
                wr = np.mean([t["win"] for t in self.metrics["trades"][-200:]])
                eq = np.array(self.metrics["equity"][-500:], dtype=float)
                if len(eq) > 0:
                    peak = np.maximum.accumulate(eq)
                    dd = float(np.max((peak - eq) / np.maximum(peak, 1e-9)))
                else:
                    dd = 0.1
                self.baseline["_winrate"] = float(wr)
                self.baseline["_dd"] = float(dd)
                self._dump_json(BASELINE_PATH, self.baseline)
        return policy, action


