from __future__ import annotations

from .event_bus import EventBus
from .playbook import PlaybookEngine
from .actions import dispatch
from .kg_sync import on_drift, on_perf_cliff, on_data_anomaly

BUS = EventBus()
PB = PlaybookEngine()

BUS.subscribe("DRIFT_ALERT", on_drift)
BUS.subscribe("PERF_CLIFF", on_perf_cliff)
BUS.subscribe("DATA_ANOMALY", on_data_anomaly)


def handle(event: str, payload: dict):
    BUS.publish(event, payload)
    acts = PB.eval(event, payload)
    for a in acts:
        dispatch(a, payload)
    return acts


