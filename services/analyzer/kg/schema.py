from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Any
import uuid


@dataclass
class Node:
    id: str
    type: str  # SYMBOL | SESSION | STRATEGY | RISK | GUARD | EVENT
    attrs: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Edge:
    id: str
    src: str
    dst: str
    type: str  # REL | CAUSES | INFLUENCES | RUNS_ON | BLOCKED_BY
    attrs: Dict[str, Any] = field(default_factory=dict)


class Graph:
    def __init__(self):
        self.nodes: Dict[str, Node] = {}
        self.edges: Dict[str, Edge] = {}

    def add_node(self, type: str, **attrs) -> str:
        nid = attrs.get("id") or str(uuid.uuid4())
        self.nodes[nid] = Node(id=nid, type=type, attrs=attrs)
        return nid

    def add_edge(self, src: str, dst: str, type: str, **attrs) -> str:
        eid = str(uuid.uuid4())
        self.edges[eid] = Edge(id=eid, src=src, dst=dst, type=type, attrs=attrs)
        return eid

    def find(self, **attrs) -> List[Node]:
        out: List[Node] = []
        for n in self.nodes.values():
            ok = True
            for k, v in attrs.items():
                if n.attrs.get(k) != v:
                    ok = False
                    break
            if ok:
                out.append(n)
        return out


