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
import httpx

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


# -------- Policy --------
def get_policy() -> Dict[str, Any]:
  return {
    "riskPct": float(os.getenv("MAX_RISK_PCT", "1.0")),
    "minRR": float(os.getenv("MIN_RR", "1.5")),
    "deviation": int(os.getenv("DEFAULT_DEVIATION", "10")),
  }


@app.get("/policy")
async def policy():
  return JSONResponse(get_policy())


# -------- Auto trade pipeline --------
class AnalyzeRequest(BaseModel):
  instrument: str
  timeframe: Literal["M1","M5","M15","M30","H1","H4","D1"]
  user_context: Optional[str] = None


class DecisionPayload(BaseModel):
  decision: Literal["BUY","SELL","WAIT"]
  entry: Optional[float]
  stopLoss: Optional[float]
  takeProfit: Optional[float]
  confidence: float
  rationale: str
  risks: list[str]
  tags: list[str]


class AutoTradeRequest(BaseModel):
  instrument: str
  timeframe: str
  riskPct: Optional[float] = None
  user_context: Optional[str] = None


class AutoTradeResponse(BaseModel):
  analysis: DecisionPayload
  policy: Dict[str, Any]
  position: Optional[Dict[str, Any]] = None
  order: Optional[Dict[str, Any]] = None
  skipped: bool
  reason: Optional[str] = None
  hint: Optional[str] = None


@app.post("/trade/auto")
async def trade_auto(req: AutoTradeRequest, Idempotency_Key: Optional[str] = Header(default=None, alias="Idempotency-Key")):
  state = init_state()
  if not state.get("authorized"):
    return unauthorized_response()

  core = (req.instrument or "").upper().replace("/", "")
  try:
    resolved = mt5_adapter.resolve_symbol(core)
  except Exception as e:
    return JSONResponse(status_code=400, content={"error": True, "reason": "resolve_failed", "message": str(e)})

  # Step 1: call analyzer
  analyzer_url = os.getenv("EXECUTOR_ANALYZER_URL", "http://localhost:7001").rstrip("/")
  payload = {"symbol": core, "timeframe": req.timeframe, "user_context": req.user_context}
  try:
    async with httpx.AsyncClient(timeout=15.0) as client:
      r = await client.post(f"{analyzer_url}/analyze", json=payload)
      r.raise_for_status()
      data = r.json()
  except Exception as e:
    return JSONResponse(status_code=502, content={"error": True, "reason": "analyzer_error", "message": str(e)})

  # Step 2: validate decision
  try:
    analysis = DecisionPayload(**data)
  except Exception as e:
    return JSONResponse(status_code=502, content={"error": True, "reason": "analysis_invalid", "message": str(e)})

  if analysis.decision == "WAIT" or analysis.entry is None or analysis.stopLoss is None or analysis.takeProfit is None:
    return JSONResponse(AutoTradeResponse(analysis=analysis, policy=get_policy(), skipped=True, reason="decision_wait").model_dump())

  rr = abs(analysis.takeProfit - analysis.entry) / max(abs(analysis.entry - analysis.stopLoss), 1e-9)
  pol = get_policy()
  if rr < float(pol["minRR"]):
    return JSONResponse(AutoTradeResponse(analysis=analysis, policy={**pol, "rr": rr}, skipped=True, reason="rr_below_min").model_dump())

  # Step 3: sizing
  snap = mt5_adapter.symbol_snapshot(resolved)
  ai = None
  try:
    import MetaTrader5 as mt5  # type: ignore
    ai = mt5.account_info()
  except Exception:
    ai = None
  balance = float(getattr(ai, "balance", 0.0) or 0.0)
  risk_pct = float(req.riskPct if req.riskPct is not None else pol["riskPct"])
  risk_amount = balance * (risk_pct / 100.0)
  price_dist = abs(analysis.entry - analysis.stopLoss)
  tick_value_per_lot = float(snap.get("trade_tick_value") or 0.0)
  ticks_per_price_unit = 1.0 / float((snap.get("trade_tick_size") or 1.0))
  loss_per_lot_at_sl = max(price_dist * ticks_per_price_unit * tick_value_per_lot, 1e-9)
  lots_raw = risk_amount / loss_per_lot_at_sl
  # snap lots to min/step
  min_vol = float(snap.get("volume_min") or 0.01)
  step = float(snap.get("volume_step") or 0.01)
  precision = max(0, str(step)[::-1].find(".")) if isinstance(step, float) else 2
  lots_rounded = max(min_vol, round(lots_raw / step) * step)
  lots_rounded = round(lots_rounded, precision)
  units = int(lots_rounded * int(os.getenv("MT5_UNITS_PER_LOT", "100000") or 100000))

  # Step 4: execution
  digits = int(snap.get("digits") or 5)
  point = float(snap.get("point") or 0.01)
  bid = float(snap.get("tick", {}).get("bid") or 0.0)
  ask = float(snap.get("tick", {}).get("ask") or 0.0)
  analysis.entry = round(float(analysis.entry), digits)
  analysis.stopLoss = round(float(analysis.stopLoss), digits)
  analysis.takeProfit = round(float(analysis.takeProfit), digits)
  side = analysis.decision

  # market vs pending
  is_market = False
  if side == "BUY":
    is_market = abs(analysis.entry - ask) <= 2 * point
  else:
    is_market = abs(analysis.entry - bid) <= 2 * point

  body = {
    "instrument": resolved,
    "side": side,
    "units": units,
    "sl": analysis.stopLoss,
    "tp": analysis.takeProfit,
    "deviation": pol["deviation"],
  }
  if is_market:
    body["entryType"] = "market"
  else:
    body["entryType"] = "limit"
    body["entry"] = analysis.entry

  # Idempotency
  if not hasattr(trade_auto, "_idem_cache"):
    setattr(trade_auto, "_idem_cache", {})
  cache: Dict[str, Tuple[int, Dict[str, Any]]] = getattr(trade_auto, "_idem_cache")  # type: ignore
  now_ms = int(datetime.now().timestamp() * 1000)
  window_ms = 10 * 60 * 1000
  for k in list(cache.keys()):
    if now_ms - cache[k][0] > window_ms:
      del cache[k]
  key = None
  if Idempotency_Key:
    m = hashlib.sha256()
    m.update(Idempotency_Key.encode("utf-8"))
    m.update(str(body).encode("utf-8"))
    key = m.hexdigest()
    if key in cache:
      return JSONResponse(cache[key][1])

  t0 = perf_counter()
  order = mt5_adapter.place_order(body)
  latency_ms = int((perf_counter() - t0) * 1000)

  # structured log
  try:
    print({
      "t": datetime.utcnow().isoformat() + "Z",
      "action": "trade_auto",
      "instrument": resolved,
      "side": side,
      "lots": lots_rounded,
      "units": units,
      "price": body.get("entry"),
      "sl": body.get("sl"),
      "tp": body.get("tp"),
      "retcode": order.get("retcode"),
      "ticket": order.get("order") or order.get("deal"),
      "latency_ms": latency_ms,
      "rr": rr,
    })
  except Exception:
    pass

  resp = AutoTradeResponse(
    analysis=analysis,
    policy={**pol, "rr": rr, "lots": lots_rounded, "units": units},
    position=None,
    order=order,
    skipped=False,
  )
  data_resp = resp.model_dump()
  if key:
    cache[key] = (now_ms, data_resp)
  return JSONResponse(data_resp)

