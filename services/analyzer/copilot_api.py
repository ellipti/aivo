from __future__ import annotations

import os, json
from typing import Any, Dict

import httpx
from fastapi import APIRouter
from pydantic import BaseModel

from .orchestrator.kg_sync import KG
from .orchestrator.playbook import PlaybookEngine


router = APIRouter(prefix="/copilot", tags=["copilot"])
PB = PlaybookEngine()


MODEL = os.getenv("OPENAI_MODEL") or os.getenv("MODEL") or "gpt-5-thinking"
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")


class AskBody(BaseModel):
    query: str


class SuggestRuleBody(BaseModel):
    context: Dict[str, Any]


class ApplyRuleBody(BaseModel):
    rule: Dict[str, Any]


def _ask_openai(prompt: str) -> str:
    if not OPENAI_API_KEY:
        return "LLM key not configured. Provide OPENAI_API_KEY to enable copilot."
    url = "https://api.openai.com/v1/responses"
    headers = {"Authorization": f"Bearer {OPENAI_API_KEY}", "Content-Type": "application/json"}
    payload = {
        "model": MODEL,
        "input": prompt,
        "temperature": 0.2,
        "max_output_tokens": 800,
    }
    with httpx.Client(timeout=60) as client:
        r = client.post(url, headers=headers, json=payload)
        r.raise_for_status()
        data = r.json()
    # Prefer output_text if present
    if isinstance(data.get("output_text"), str):
        return data["output_text"]
    # Fallback combine outputs
    parts = []
    for item in data.get("output", []) or []:
        if item.get("type") == "message":
            for c in item.get("content", []) or []:
                t = c.get("text")
                if isinstance(t, str):
                    parts.append(t)
    return "\n".join(parts) if parts else ""


@router.post("/ask")
def ask_copilot(body: AskBody):
    kg_data = {"nodes": [vars(n) for n in KG.nodes.values()], "edges": [vars(e) for e in KG.edges.values()]}
    pb_data = PB.cfg
    prompt = (
        "You are AIVO's trading automation copilot.\n"
        f"User Question: {body.query}\n"
        f"Knowledge Graph (JSON): {json.dumps(kg_data)}\n"
        f"Current Playbooks (JSON): {json.dumps(pb_data)}\n"
        "Answer clearly in Mongolian. If relevant, suggest concrete actions."
    )
    answer = _ask_openai(prompt)
    return {"answer": answer}


@router.post("/suggest_rule")
def suggest_rule(body: SuggestRuleBody):
    schema_hint = {
        "id": "STRING",
        "when": {"event": "STRING", "symbols": ["OPTIONAL"], "any_symbol": "OPTIONAL_BOOL"},
        "if": [{"metric": "STRING.nested", "op": ">|<|>=|<=|==|!=", "value": "NUMBER"}],
        "then": [{"action": "SAFE_MODE_ON|PAUSE|ROTATE_SYMBOL|NOTIFY", "minutes": "OPT", "reason": "OPT", "msg": "OPT"}],
    }
    prompt = (
        "Suggest ONE new playbook rule as pure JSON (no prose) matching this schema: "
        f"{json.dumps(schema_hint)}\n"
        f"Context (JSON): {json.dumps(body.context)}\n"
        "Ensure keys and types are valid."
    )
    text = _ask_openai(prompt)
    # Try parse JSON directly
    try:
        rule = json.loads(text)
    except Exception:
        rule = {"raw": text}
    return {"rule": rule}


@router.post("/apply_rule")
def apply_rule(body: ApplyRuleBody):
    cfg_path = "configs/playbooks.json"
    cfg = json.load(open(cfg_path, "r", encoding="utf-8"))
    rule = body.rule
    # Minimal validation
    if not isinstance(rule, dict) or "id" not in rule or "when" not in rule or "then" not in rule:
        return {"ok": False, "reason": "invalid_rule"}
    # Upsert by id
    found = False
    for i, pb in enumerate(cfg.get("playbooks", [])):
        if pb.get("id") == rule["id"]:
            cfg["playbooks"][i] = rule
            found = True
            break
    if not found:
        cfg.setdefault("playbooks", []).append(rule)
    json.dump(cfg, open(cfg_path, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    # Reload engine config
    PB.cfg = cfg
    return {"ok": True, "applied": rule.get("id")}


