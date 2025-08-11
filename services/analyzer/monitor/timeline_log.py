import json, os, time

PATH = "incidents/_events.jsonl"


def log_event(kind: str, oid: str, **kw):
    os.makedirs(os.path.dirname(PATH), exist_ok=True)
    kw.update({"t": int(time.time()), "kind": kind, "oid": oid})
    with open(PATH, "a", encoding="utf-8") as f:
        f.write(json.dumps(kw, ensure_ascii=False) + "\n")


