from __future__ import annotations

"""
Local run

  uvicorn services.analyzer.main:app --host 0.0.0.0 --port 7001 --reload

Quick test

  curl -s http://localhost:7001/health
  curl -s -X POST http://localhost:7001/analyze \
    -H "Content-Type: application/json" \
    -d '{
      "symbol":"XAUUSD", "timeframe":"H1",
      "price_snapshot": 2400.12,
      "technical": {"ema": 2398.5, "rsi": 52},
      "fundamentals": {"events": ["NFP Friday"]},
      "user_context": "trend-following"
    }'
"""

import json
import os
import time
import logging
from collections import deque
from typing import List, Literal, Optional

import httpx
from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from tenacity import retry, stop_after_attempt, wait_fixed
from .utils.decision_validator import Decision as VDecision, parse_gpt, validate, DecisionError
from .utils.event_bus import publish_event


# ----------------------------------------------------------------------------
# Config & Logging
# ----------------------------------------------------------------------------

def getenv_float(name: str, default: float) -> float:
    try:
        return float(os.getenv(name, str(default)))
    except Exception:
        return default


MODEL = os.getenv("MODEL") or os.getenv("OPENAI_MODEL") or "gpt-5-thinking"
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
TEMPERATURE = getenv_float("TEMPERATURE", 0.2)
MAX_OUTPUT_TOKENS = int(os.getenv("RESPONSE_TOKENS", "800"))
MIN_RR = getenv_float("MIN_RR", 1.5)


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:  # type: ignore[override]
        payload = {
            "ts": int(time.time() * 1000),
            "level": record.levelname,
            "message": record.getMessage(),
        }
        if record.__dict__:
            extra = {k: v for k, v in record.__dict__.items() if k not in ("msg", "args")}
            payload.update(extra)
        return json.dumps(payload, ensure_ascii=False)


handler = logging.StreamHandler()
handler.setFormatter(JsonFormatter())
logger = logging.getLogger("aivo.analyzer")
logger.setLevel(logging.INFO)
if not logger.handlers:
    logger.addHandler(handler)


# ----------------------------------------------------------------------------
# App & Models
# ----------------------------------------------------------------------------

app = FastAPI(title="AIVO Analyzer API")
from . import metrics as metrics
from . import tuner_api
from . import portfolio_api
from . import executions_api
from . import slippage_api
from . import calibrate_api
from . import online_calib_api
from . import monitor_api
from . import playbook_api
from . import copilot_api
from . import swarm_api
from . import strategy_api
from . import exposure_api
from . import exposure_sse
from . import corr_api
from . import incidents_api
from . import news_api
from . import intermarket_api
from . import routing_api
from . import ensemble_api
app.include_router(metrics.router)
app.include_router(tuner_api.router)
app.include_router(portfolio_api.router)
app.include_router(executions_api.router)
app.include_router(slippage_api.router)
app.include_router(calibrate_api.router)
app.include_router(online_calib_api.router)
app.include_router(monitor_api.router)
app.include_router(playbook_api.router)
app.include_router(copilot_api.router)
app.include_router(swarm_api.router)
app.include_router(strategy_api.router)
app.include_router(exposure_api.router)
app.include_router(exposure_sse.router)
app.include_router(corr_api.router)
app.include_router(incidents_api.router)
app.include_router(news_api.router)
app.include_router(intermarket_api.router)
app.include_router(routing_api.router)
app.include_router(ensemble_api.router)


class Technical(BaseModel):
    ema: Optional[float] = None
    rsi: Optional[float] = None
    macd: Optional[float] = None
    # Extend with more indicators as needed


class Fundamentals(BaseModel):
    events: List[str] = Field(default_factory=list)


class AnalyzeInput(BaseModel):
    symbol: str
    timeframe: str
    price_snapshot: Optional[float] = None
    technical: Optional[Technical] = None
    fundamentals: Optional[Fundamentals] = None
    user_context: Optional[str] = None


Decision = Literal["BUY", "SELL", "WAIT"]


class ModelDecision(BaseModel):
    decision: Decision
    entry: Optional[float] = None
    stopLoss: Optional[float] = None
    takeProfit: Optional[float] = None
    confidence: float = Field(ge=0.0, le=1.0)
    rationale: str
    risks: List[str]
    tags: List[str]


# In-memory store of last analyses (request + result)
RECENT_ANALYSES: deque[dict] = deque(maxlen=100)


def build_system_prompt() -> str:
    # Bilingual, compact, and instruction-heavy
    return (
        "You are AIVO Trading Analyst. Produce concise, actionable trading decisions.\n"
        "- Output MUST follow the provided JSON schema (no extra keys).\n"
        "- Consider technicals, fundamentals, price context, and timeframe.\n"
        "- If data is insufficient or unclear, prefer WAIT with rationale.\n\n"
        "Та AIVO арилжааны шинжээч. Богино, хэрэгжихүйц дүгнэлт гаргана уу.\n"
        "- Гаралт заасан JSON схемийг яг баримтлана.\n"
        "- Техникийн болон суурь мэдээлэл, үнийн орчин, timeframe-г харгалз.\n"
        "- Мэдээлэл хангалтгүй бол WAIT шийдвэрийг илүүд үз."
    )


def build_user_prompt(payload: AnalyzeInput) -> str:
    parts: List[str] = [
        f"Symbol: {payload.symbol}",
        f"Timeframe: {payload.timeframe}",
    ]
    if payload.price_snapshot is not None:
        parts.append(f"PriceSnapshot: {payload.price_snapshot}")
    if payload.technical is not None:
        parts.append(f"Technical: {payload.technical.model_dump_json()}")
    if payload.fundamentals is not None:
        parts.append(f"Fundamentals: {payload.fundamentals.model_dump_json()}")
    if payload.user_context:
        parts.append(f"UserContext: {payload.user_context}")
    parts.append(
        "Produce a JSON object ONLY (no prose) matching the schema."
    )
    return "\n".join(parts)


def model_schema_for_openai() -> dict:
    return {
        "name": "trading_decision",
        "strict": True,
        "schema": {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "decision": {"type": "string", "enum": ["BUY", "SELL", "WAIT"]},
                "entry": {"type": ["number", "null"]},
                "stopLoss": {"type": ["number", "null"]},
                "takeProfit": {"type": ["number", "null"]},
                "confidence": {"type": "number", "minimum": 0.0, "maximum": 1.0},
                "rationale": {"type": "string"},
                "risks": {"type": "array", "items": {"type": "string"}},
                "tags": {"type": "array", "items": {"type": "string"}},
            },
            "required": [
                "decision",
                "confidence",
                "rationale",
                "risks",
                "tags",
            ],
        },
    }


def apply_guardrails(d: ModelDecision) -> ModelDecision:
    # If non-WAIT but missing critical numeric fields -> force WAIT
    if d.decision != "WAIT":
        if d.entry is None or d.stopLoss is None or d.takeProfit is None:
            d.decision = "WAIT"
            d.rationale += " | Guardrail: Missing price levels -> WAIT"
            return d

        # Enforce min RR >= configured threshold
        try:
            risk = abs((d.entry or 0) - (d.stopLoss or 0))
            reward = abs((d.takeProfit or 0) - (d.entry or 0))
            rr = reward / risk if risk > 0 else 0.0
        except Exception:
            rr = 0.0

        if rr < MIN_RR:
            d.decision = "WAIT"
            d.rationale += f" | Guardrail: RR {rr:.2f} < {MIN_RR:.2f} -> WAIT"

    # Additional decision validation and filtering
    try:
        vd = VDecision(
            decision=d.decision,
            entry=d.entry,
            sl=d.stopLoss,
            tp=d.takeProfit,
            reason=d.rationale,
        )
        vd = validate(vd, symbol="XAUUSD", min_rr=MIN_RR, min_distance_pts=10.0)
        d.decision = vd.decision
        d.entry = vd.entry
        d.stopLoss = vd.sl
        d.takeProfit = vd.tp
        d.rationale = vd.reason or d.rationale
    except DecisionError as e:
        d.decision = "WAIT"
        d.entry = None
        d.stopLoss = None
        d.takeProfit = None
        d.rationale = (d.rationale + f" | Filtered: {e}").strip()
    return d


def _extract_output_text(resp_json: dict) -> str:
    # SDK provides output_text; REST may only have output list
    if isinstance(resp_json.get("output_text"), str):
        return resp_json["output_text"]
    parts: List[str] = []
    for item in resp_json.get("output", []) or []:
        if item.get("type") == "message":
            for c in item.get("content", []) or []:
                t = c.get("text")
                if isinstance(t, str):
                    parts.append(t)
    return "\n".join(parts)


@retry(stop=stop_after_attempt(3), wait=wait_fixed(0.5))
def call_openai_with_retry(system_prompt: str, user_prompt: str) -> ModelDecision:
    if not OPENAI_API_KEY:
        # No key: return WAIT stub so service remains usable locally
        return ModelDecision(
            decision="WAIT", entry=None, stopLoss=None, takeProfit=None,
            confidence=0.0, rationale="OPENAI_API_KEY missing", risks=["no_key"], tags=["stub"]
        )

    url = "https://api.openai.com/v1/responses"
    headers = {
        "Authorization": f"Bearer {OPENAI_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": MODEL,
        "instructions": system_prompt,
        "input": user_prompt,
        "temperature": TEMPERATURE,
        "max_output_tokens": MAX_OUTPUT_TOKENS,
        "response_format": {"type": "json_schema", "json_schema": model_schema_for_openai()},
    }

    with httpx.Client(timeout=30) as client:
        r = client.post(url, headers=headers, json=payload)
        r.raise_for_status()
        data = r.json()
    text = _extract_output_text(data)
    # Try strict parse first, then fallback to tolerant parser
    try:
        parsed = json.loads(text)
        return ModelDecision.model_validate(parsed)
    except Exception:
        v = parse_gpt(text)
        mapped = {
            "decision": v.decision,
            "entry": v.entry,
            "stopLoss": v.sl,
            "takeProfit": v.tp,
            "confidence": 0.0,
            "rationale": v.reason or "parsed_fallback",
            "risks": [],
            "tags": ["fallback_parser"],
        }
        return ModelDecision.model_validate(mapped)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/analyze", response_model=ModelDecision)
def analyze(body: AnalyzeInput) -> ModelDecision:
    system_prompt = build_system_prompt()
    user_prompt = build_user_prompt(body)

    logger.info(
        "request_analyze",
        extra={
            "symbol": body.symbol,
            "timeframe": body.timeframe,
        },
    )

    decision = call_openai_with_retry(system_prompt, user_prompt)
    final = apply_guardrails(decision)
    # Compute RR for logging
    rr = None
    try:
        if final.entry is not None and final.stopLoss is not None and final.takeProfit is not None:
            risk = abs(final.entry - final.stopLoss)
            reward = abs(final.takeProfit - final.entry)
            rr = (reward / risk) if risk > 0 else 0.0
    except Exception:
        rr = None

    RECENT_ANALYSES.append(
        {
            "ts": int(time.time() * 1000),
            "symbol": body.symbol,
            "timeframe": body.timeframe,
            "model": MODEL,
            "result": final.model_dump(),
        }
    )

    logger.info(
        "response_analyze",
        extra={
            "symbol": body.symbol,
            "tf": body.timeframe,
            "decision": final.decision,
            "rr": rr,
            "confidence": final.confidence,
        },
    )
    # Publish to event bus (signals)
    try:
        publish_event(
            "signal",
            {
                "symbol": body.symbol,
                "timeframe": body.timeframe,
                "decision": final.decision,
                "entry": final.entry,
                "sl": final.stopLoss,
                "tp": final.takeProfit,
                "confidence": final.confidence,
                "rr": rr,
            },
        )
    except Exception:
        pass
    return final


@app.get("/signals")
def list_signals():
    """Return recent model analyses from in-memory ring buffer."""
    return {"items": list(RECENT_ANALYSES)}


# ----------------- SSE stream (simple) -----------------

STREAM_KEY = os.getenv("AIVO_STREAM_KEY", "aivo_events")
import redis
_redis = redis.Redis(host=os.getenv("REDIS_HOST", "localhost"), port=int(os.getenv("REDIS_PORT", "6379")), decode_responses=True)

def _iter_stream():
    last_id = "$"
    while True:
        try:
            resp = _redis.xread({STREAM_KEY: last_id}, block=5000, count=10)
            if resp:
                _, messages = resp[0]
                for msg_id, fields in messages:
                    last_id = msg_id
                    data = fields.get("data")
                    if data:
                        yield f"data: {data}\n\n"
        except Exception:
            yield "event: ping\n\n"

@app.get("/events/stream")
def stream_events():
    return StreamingResponse(_iter_stream(), media_type="text/event-stream")

