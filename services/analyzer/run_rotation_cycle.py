from __future__ import annotations

from datetime import datetime, timezone
from .utils.news_scheduler import load_sched, in_session, news_blackout
from .utils.symbol_rotation import load_symbols, build_rotation, Blacklist
from .utils.logger import info, warn


def get_prices(symbol: str, bars: int) -> list[float]:  # placeholder hook
    raise NotImplementedError


def get_upcoming_events(symbol: str) -> list[dict]:  # placeholder hook
    return []


def run_cycle_for(symbol: str, timeframe: str) -> None:  # placeholder hook
    raise NotImplementedError


def choose_symbol(timeframe: str = "M30"):
    SC = load_sched()
    SYM = load_symbols()
    now = datetime.now(timezone.utc)

    _ = in_session(now, SC["session_windows_utc"])  # session tag if needed

    price_hist: dict[str, list[float]] = {}
    for s in SYM["universe"].keys():
        try:
            px = get_prices(s, bars=SYM["rotation"]["lookback_bars"])  # -> [close...]
        except Exception:
            px = []
        if len(px) < 30:
            continue
        price_hist[s] = px

    selected = build_rotation(
        price_history=price_hist,
        sym_cfg=SYM,
        max_corr=float(SYM["rotation"]["max_correlation"]),
        min_vol=float(SYM["rotation"]["min_volatility"]),
    )
    if not selected:
        warn("rotation.empty")
        return None

    bl = Blacklist(
        ttl_minutes=int(SYM["rotation"]["drawdown_blacklist_minutes"]),
        loss_streak_threshold=int(SYM["rotation"]["loss_streak_to_blacklist"]),
    )
    for sym in selected:
        events = get_upcoming_events(sym)  # [{time_utc, impact, symbols, title}]
        blocked, _reason = news_blackout(now, sym, events, before=30, after=30)
        if blocked:
            continue
        if load_sched().get("skip_if_blacklisted", True) and bl.is_blacklisted(sym):
            continue
        return sym
    return None


def rotation_loop():
    SC = load_sched()
    tf = SC["timeframes"][0]
    sym = choose_symbol(tf)
    if not sym:
        warn("no_symbol_ready")
        return
    info("rotation.pick", symbol=sym, tf=tf)
    run_cycle_for(sym, tf)


if __name__ == "__main__":
    rotation_loop()


