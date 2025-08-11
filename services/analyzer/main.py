from __future__ import annotations

import json
import os
import time
import logging
from collections import deque
from datetime import datetime, timedelta, timezone
from typing import List, Literal, Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from openai import OpenAI


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
TE_API_CLIENT = os.getenv("TE_API_CLIENT", "")
TE_API_SECRET = os.getenv("TE_API_SECRET", "")
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

    return d


def call_openai_with_retry(system_prompt: str, user_prompt: str, retries: int = 1) -> ModelDecision:
    client = OpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else OpenAI()

    last_error: Optional[Exception] = None
    for attempt in range(retries + 1):
        try:
            resp = client.responses.create(
                model=MODEL,
                instructions=system_prompt,
                input=user_prompt,
                temperature=TEMPERATURE,
                max_output_tokens=MAX_OUTPUT_TOKENS,
                response_format={
                    "type": "json_schema",
                    "json_schema": model_schema_for_openai(),
                },
            )
            text = resp.output_text  # Already enforced to be JSON via schema
            data = json.loads(text)
            return ModelDecision.model_validate(data)
        except Exception as e:  # Parse or API error
            last_error = e
            time.sleep(0.5)
            continue

    logger.error("openai_error", extra={"error": str(last_error)})
    # Fallback minimal WAIT
    return ModelDecision(
        decision="WAIT",
        entry=None,
        stopLoss=None,
        takeProfit=None,
        confidence=0.0,
        rationale="LLM error or schema mismatch",
        risks=["LLM schema error"],
        tags=["fallback"],
    )


@app.get("/health")
def health():
    status = "ok"
    openai_status = "ok"
    try:
        # Very small, cheap probe
        probe = call_openai_with_retry(
            system_prompt="Health check",
            user_prompt="Respond with {\"decision\":\"WAIT\",\"confidence\":0.0,\"rationale\":\"health\",\"risks\":[\"none\"],\"tags\":[\"health\"]}",
            retries=0,
        )
        if probe.decision != "WAIT":
            openai_status = "degraded"
    except Exception:
        openai_status = "degraded"

    return {"status": status, "openai": openai_status}


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

    decision = call_openai_with_retry(system_prompt, user_prompt, retries=1)
    final = apply_guardrails(decision)

    RECENT_ANALYSES.append(
        {
            "ts": int(time.time() * 1000),
            "symbol": body.symbol,
            "timeframe": body.timeframe,
            "model": MODEL,
            "result": final.model_dump(),
        }
    )

    logger.info("response_analyze", extra={"decision": final.decision, "tags": final.tags})
    return final


@app.get("/signals")
def list_signals():
    """Return recent model analyses from in-memory ring buffer."""
    return {"items": list(RECENT_ANALYSES)}


# ----------------------------------------------------------------------------
# Economic Calendar (TradingEconomics)
# ----------------------------------------------------------------------------


class CalendarItem(BaseModel):
    timeUTC: str
    country: str
    event: str
    importance: Optional[str] = None
    forecast: Optional[str] = None
    previous: Optional[str] = None


async def fetch_te_calendar(symbols: list[str], lookahead_hours: int) -> list[CalendarItem]:
    import httpx

    # TradingEconomics API reference: https://docs.tradingeconomics.com/
    # Endpoint sample: https://api.tradingeconomics.com/calendar?d1=YYYY-MM-DD&d2=YYYY-MM-DD&importance=3&c=client:secret
    now = datetime.now(timezone.utc)
    d1 = now.strftime("%Y-%m-%d")
    d2 = (now + timedelta(hours=lookahead_hours)).strftime("%Y-%m-%d")

    # Map common FX symbols to countries; extend as needed
    symbol_to_countries = {
        "XAUUSD": ["United States"],
        "EURUSD": ["Euro Area", "United States"],
        "GBPUSD": ["United Kingdom", "United States"],
        "USDJPY": ["Japan", "United States"],
        "AUDUSD": ["Australia", "United States"],
        "USDCAD": ["Canada", "United States"],
        "USDCHF": ["Switzerland", "United States"],
        "NZDUSD": ["New Zealand", "United States"],
    }

    countries: set[str] = set()
    for s in symbols:
        countries.update(symbol_to_countries.get(s.upper(), []))
    c_param = ",".join(countries) if countries else "United States,Euro Area"

    auth = f"{TE_API_CLIENT}:{TE_API_SECRET}" if TE_API_CLIENT and TE_API_SECRET else None
    params = {
        "d1": d1,
        "d2": d2,
        "importance": "3",  # high-impact
    }
    if auth:
        params["c"] = auth

    url = "https://api.tradingeconomics.com/calendar"
    async with httpx.AsyncClient(timeout=10) as client:
        r = await client.get(url, params=params)
        r.raise_for_status()
        data = r.json()

    items: list[CalendarItem] = []
    for it in data:
        try:
            items.append(
                CalendarItem(
                    timeUTC=(it.get("DateUTC") or it.get("Date", "")),
                    country=it.get("Country", ""),
                    event=it.get("Event", ""),
                    importance=str(it.get("Importance", "")),
                    forecast=(it.get("Forecast") or it.get("ForecastValue")),
                    previous=(it.get("Previous") or it.get("PreviousValue")),
                )
            )
        except Exception:
            continue
    return items


@app.get("/calendar")
async def calendar(symbols: str, lookaheadHours: int = 48):
    symbol_list = [s.strip() for s in symbols.split(",") if s.strip()]
    items = await fetch_te_calendar(symbol_list, lookaheadHours)
    return {"symbols": symbol_list, "items": [it.model_dump() for it in items]}

