from __future__ import annotations

import json, os
from typing import Dict, Any


PATH = "storage/params.json"


def load_store() -> Dict[str, Any]:
    if os.path.exists(PATH):
        try:
            return json.load(open(PATH, "r", encoding="utf-8"))
        except Exception:
            return {}
    return {}


def save_store(data: Dict[str, Any]):
    os.makedirs(os.path.dirname(PATH) or ".", exist_ok=True)
    json.dump(data, open(PATH, "w", encoding="utf-8"), ensure_ascii=False, indent=2)


def get_params(strategy_id: str) -> Dict[str, Any]:
    return load_store().get(strategy_id, {})


def update_params(strategy_id: str, params: Dict[str, Any]):
    st = load_store()
    st[strategy_id] = params
    save_store(st)


