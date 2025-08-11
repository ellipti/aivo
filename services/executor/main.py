from __future__ import annotations

"""
Local run (ATTACH-ONLY):

  uvicorn services.executor.main:app --host 0.0.0.0 --port 7002 --reload

Behavior: attaches to a running MT5 terminal session. It will NOT login with
credentials unless MT5_FORCE_LOGIN=true. If not authorized, trading endpoints
return 503 with reason mt5_not_authorized.

Examples:
  - Place market:
    POST /orders/place {"instrument":"XAUUSD","side":"BUY","units":10000,"entryType":"market","sl":3368,"tp":3390}
  - Place pending auto STOP/LIMIT:
    POST /orders/place {"instrument":"XAUUSD","side":"BUY","units":10000,"entry":3378,"sl":3368,"tp":3390}
  - Modify SL/TP:
    POST /orders/modify {"orderId":"123456","sl":3365,"tp":3395}
  - Partial close 50%:
    POST /orders/close {"orderId":"123456","volumePct":50}
  - Cancel pending:
    POST /orders/cancel {"orderId":"123456"}
"""

import os
from datetime import datetime, time as dtime
from pathlib import Path
from typing import Any, Dict, Optional

from dotenv import load_dotenv
from fastapi import FastAPI, Header
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from typing import Literal

from . import mt5_adapter
from time import perf_counter
from collections import deque
import hashlib
from typing import Deque, Tuple

# Load .env adjacent to this file
load_dotenv(dotenv_path=Path(__file__).with_name(".env"))

MODE = "mt5"
FORCE_LOGIN = os.getenv("MT5_FORCE_LOGIN", "false").lower() == "true"
MT5_PATH = os.getenv("MT5_PATH") or None
MT5_LOGIN = int(os.getenv("MT5_LOGIN")) if (os.getenv("MT5_LOGIN") and FORCE_LOGIN) else None
MT5_PASSWORD = os.getenv("MT5_PASSWORD") if FORCE_LOGIN else None
MT5_SERVER = os.getenv("MT5_SERVER") if FORCE_LOGIN else None


app = FastAPI(title="AIVO Executor API")


class PlaceOrderBody(BaseModel):
  instrument: Optional[str] = None
  symbol: Optional[str] = None
  side: Literal["BUY", "SELL"]
  units: int
  entryType: Literal["market", "limit", "stop"] = "market"
  limitPrice: Optional[float] = None
  entry: Optional[float] = None
  sl: Optional[float] = None
  tp: Optional[float] = None
  deviation: Optional[int] = 10


class CloseOrderBody(BaseModel):
  orderId: str


class RiskPositionSizeBody(BaseModel):
  balance: float
  riskPct: float
  slPips: float


def init_state() -> Dict[str, Any]:
  return mt5_adapter.init_mt5(
      path=MT5_PATH,
      force_login=FORCE_LOGIN,
      login=MT5_LOGIN,
      password=MT5_PASSWORD,
      server=MT5_SERVER,
  )


def unauthorized_response() -> JSONResponse:
  return JSONResponse(status_code=503, content={
      "error": True,
      "reason": "mt5_not_authorized",
      "hint": "Open MT5 terminal, login to your account, then retry."
  })


# ------------------------------ Endpoints -----------------------------------


@app.get("/health")
async def health():
    state = init_state()
    return JSONResponse({
        "status": ("ok" if state.get("authorized") else state.get("status", "no_session")),
        "mode": MODE,
        "authorized": bool(state.get("authorized")),
        "terminal": state.get("terminal"),
        "account": state.get("account"),
        "server": state.get("server"),
    })


@app.post("/orders/place")
async def orders_place(body: PlaceOrderBody, Idempotency_Key: Optional[str] = Header(default=None, alias="Idempotency-Key")):
    state = init_state()
    if not state.get("authorized"):
        return unauthorized_response()
    # Idempotency (10 min)
    now_ms = int(datetime.now().timestamp() * 1000)
    window_ms = 10 * 60 * 1000
    if not hasattr(orders_place, "_idem_cache"):
        setattr(orders_place, "_idem_cache", {})
    cache: Dict[str, Tuple[int, Dict[str, Any]]] = getattr(orders_place, "_idem_cache")  # type: ignore
    # purge old
    for k in list(cache.keys()):
        if now_ms - cache[k][0] > window_ms:
            del cache[k]
    payload = body.model_dump(by_alias=True)
    # Normalize instrument/symbol
    core = (payload.get("instrument") or payload.get("symbol") or "").upper().replace("/", "")
    if payload.get("symbol") and not payload.get("instrument"):
        try:
            print({"warn": "symbol_used_without_instrument", "symbol": payload.get("symbol")})
        except Exception:
            pass
    if not core:
        return JSONResponse(status_code=400, content={"error": True, "reason": "invalid_instrument"})
    try:
        resolved = mt5_adapter.resolve_symbol(core)
    except Exception as e:
        return JSONResponse(status_code=400, content={"error": True, "reason": "resolve_failed", "message": str(e)})
    payload["symbol"] = resolved
    payload["instrument"] = resolved

    # Auto classify pending if entry provided but no entryType
    if (payload.get("entry") is not None) and (not payload.get("entryType") or payload.get("entryType") == ""):
        payload["entryType"] = "limit"
    key = None
    if Idempotency_Key:
        m = hashlib.sha256()
        m.update(Idempotency_Key.encode("utf-8"))
        m.update(str(payload).encode("utf-8"))
        key = m.hexdigest()
        if key in cache:
            return JSONResponse(cache[key][1])

    t0 = perf_counter()
    data = mt5_adapter.place_order(payload)
    latency_ms = int((perf_counter() - t0) * 1000)
    # structured log
    try:
        print({
            "t": datetime.utcnow().isoformat() + "Z",
            "symbol": payload.get("symbol") or payload.get("instrument"),
            "side": payload.get("side"),
            "lots": payload.get("units"),
            "price": payload.get("limitPrice") or payload.get("entry"),
            "sl": payload.get("sl"),
            "tp": payload.get("tp"),
            "retcode": data.get("retcode"),
            "ticket": data.get("order") or data.get("deal"),
            "latency_ms": latency_ms,
        })
    except Exception:
        pass
    if key:
        cache[key] = (now_ms, data)
    return JSONResponse(data)


@app.get("/orders")
async def orders_list():
    state = init_state()
    if not state.get("authorized"):
        return unauthorized_response()
    data = mt5_adapter.list_orders()
    return JSONResponse(data)


@app.post("/orders/close")
async def orders_close(body: CloseOrderBody):
    state = init_state()
    if not state.get("authorized"):
        return unauthorized_response()
    # optional partial close via volumePct
    volume_pct: Optional[float] = None
    try:
        # if JSON contains it, pydantic won't parse here (not in model) so extract manually is simpler
        volume_pct = None
    except Exception:
        volume_pct = None
    data = mt5_adapter.close_order(body.orderId, volume_pct=volume_pct)
    return JSONResponse(data)


@app.post("/orders/cancel")
async def orders_cancel(body: Dict[str, Any]):
    state = init_state()
    if not state.get("authorized"):
        return unauthorized_response()
    order_id = str(body.get("orderId"))
    try:
        data = mt5_adapter.close_order(order_id)  # remove pending handled inside
        return JSONResponse(data)
    except Exception as e:
        return JSONResponse(status_code=502, content={
            "error": True,
            "reason": "broker_error",
            "message": str(e),
        })


@app.post("/orders/modify")
async def orders_modify(body: Dict[str, Any]):
    state = init_state()
    if not state.get("authorized"):
        return unauthorized_response()
    order_id = str(body.get("orderId"))
    sl = body.get("sl")
    tp = body.get("tp")
    try:
        data = mt5_adapter.modify_order(order_id, sl=sl, tp=tp)
        return JSONResponse(data)
    except Exception as e:
        snap = {"error": True, "reason": "broker_error", "message": str(e)}
        return JSONResponse(status_code=502, content=snap)


@app.get("/positions")
async def positions():
    state = init_state()
    if not state.get("authorized"):
        return unauthorized_response()
    data = mt5_adapter.list_positions()
    return JSONResponse(data)


@app.get("/broker/symbols")
async def broker_symbols():
    state = init_state()
    if not state.get("authorized"):
        return unauthorized_response()
    data = mt5_adapter.list_symbols()
    return JSONResponse(data)


@app.get("/broker/inspect")
async def broker_inspect(instrument: Optional[str] = None, entry: Optional[float] = None, side: Optional[str] = None):
    state = init_state()
    if not state.get("authorized"):
        return unauthorized_response()
    core = (instrument or "").upper().replace("/", "")
    if not core:
        return JSONResponse(status_code=400, content={"error": True, "reason": "invalid_instrument"})
    try:
        resolved = mt5_adapter.resolve_symbol(core)
        snap = mt5_adapter.symbol_snapshot(resolved)
    except Exception as e:
        return JSONResponse(status_code=400, content={"error": True, "reason": "resolve_failed", "message": str(e)})
    # decision preview
    decision = None
    try:
        bid = float(snap.get("tick", {}).get("bid"))
        ask = float(snap.get("tick", {}).get("ask"))
        et = None
        if entry is not None and side in ("BUY", "SELL"):
            if side == "BUY":
                et = "BUY_STOP" if float(entry) > ask else "BUY_LIMIT"
            else:
                et = "SELL_STOP" if float(entry) < bid else "SELL_LIMIT"
        decision = {"type": et, "usedPrice": entry if entry is not None else (ask if side == "BUY" else bid)}
    except Exception:
        pass
    return JSONResponse({
        "core": core,
        "resolved": resolved,
        **snap,
        "decisionPreview": decision,
    })


@app.post("/risk/position-size")
async def risk_position_size(body: RiskPositionSizeBody):
  risk_amount = body.balance * (body.riskPct / 100.0)
  pip_value_per_unit = 0.0001
  if body.slPips <= 0:
    return JSONResponse(status_code=400, content={"error": True, "message": "slPips must be > 0"})
  units = int(max(1, round(risk_amount / (body.slPips * pip_value_per_unit))))
  return JSONResponse({"units": units})


@app.get("/schedule/allowed-now")
async def schedule_allowed_now():
  try:
    from zoneinfo import ZoneInfo
  except Exception:
    ZoneInfo = None  # type: ignore
  tzname = os.getenv("TZ_SCHEDULE", "Asia/Ulaanbaatar")
  start = os.getenv("SCHEDULE_START", "09:00")
  end = os.getenv("SCHEDULE_END", "17:00")
  s_hour, s_min = [int(x) for x in start.split(":")]
  e_hour, e_min = [int(x) for x in end.split(":")]
  tz = ZoneInfo(tzname) if ZoneInfo else None
  now = datetime.now(tz) if tz else datetime.now()
  now_t = dtime(now.hour, now.minute)
  window = (dtime(s_hour, s_min), dtime(e_hour, e_min))
  allowed = window[0] <= now_t <= window[1]
  return JSONResponse({"allowed": allowed, "now": now.isoformat(), "window": {"start": start, "end": end, "tz": tzname}})


# --- Metrics (very small surface; extend as needed) ---
_metrics = {
    "aivo_orders_total": {"BUY": 0, "SELL": 0},
}


@app.get("/metrics")
async def metrics():
  lines = []
  lines.append("# HELP aivo_orders_total Total orders placed by side")
  lines.append("# TYPE aivo_orders_total counter")
  for side, val in _metrics["aivo_orders_total"].items():
    lines.append(f'aivo_orders_total{{side="{side}"}} {val}')
  return JSONResponse("\n".join(lines))

