from __future__ import annotations

from typing import Dict, Callable, List


class EventBus:
    def __init__(self):
        self._subs: Dict[str, List[Callable]] = {}

    def publish(self, event: str, payload: dict):
        for cb in self._subs.get(event, []):
            try:
                cb(event, payload)
            except Exception:
                pass

    def subscribe(self, event: str, cb: Callable):
        self._subs.setdefault(event, []).append(cb)


