from fastapi import APIRouter
from .orchestrator.runner import handle
from .orchestrator.kg_sync import KG

router = APIRouter(prefix="/playbook", tags=["playbook"])


@router.post("/trigger/{event}")
def trigger(event: str, payload: dict):
    return {"actions": handle(event, payload)}


@router.get("/kg")
def kg_dump():
    return {"nodes": [vars(n) for n in KG.nodes.values()], "edges": [vars(e) for e in KG.edges.values()]}


