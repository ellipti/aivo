import os, json, time
from pathlib import Path


def md_report(oid, symbol, strategy, result, out_dir="incidents/"):
    os.makedirs(out_dir, exist_ok=True)
    tl = result["timeline"]
    kpi = tl.get("kpi", {})
    factors = "\n".join([f"- **{f['type']}** — {f['key']} ({f.get('detail','')})" for f in result.get("factors", [])]) or "- n/a"
    rows = []
    for e in tl.get("events", []):
        detail = {k: v for k, v in e.items() if k not in ("t", "kind", "oid")}
        rows.append(f"| {time.strftime('%H:%M:%S', time.gmtime(e['t']))} | {e['kind']} | {json.dumps(detail)} |")
    table = "\n".join(["| Time | Event | Detail |", "|---|---|---|", *rows])
    body = f"""# Incident Post-Mortem — {oid}
**Symbol:** {symbol}  |  **Strategy:** {strategy}  |  **Verdict:** {result['verdict']}

## Key Factors
{factors}

## Execution KPIs
- Max Slippage: **{kpi.get('slip_max',0)} pts**
- Max Latency: **{kpi.get('latency_max',0)} ms**
- Replaces: **{kpi.get('replaces',0)}**

## Timeline (last {tl['events'] and len(tl['events']) or 0} events)
{table}

## Suggested Actions
{os.linesep.join(['- ' + json.dumps(a) for a in result.get('actions', [])])}
"""
    p = Path(out_dir) / f"{oid}.md"
    p.write_text(body, encoding="utf-8")
    return str(p)


