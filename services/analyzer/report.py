import json, sys
from datetime import datetime

TPL = """<!doctype html><html><head><meta charset="utf-8">
<title>AIVO Backtest Report</title>
<style>body{font:14px system-ui;margin:20px;} .kpi{display:grid;grid-template-columns:repeat(4,1fr);gap:12px}
.card{padding:12px;border:1px solid #e5e7eb;border-radius:12px;background:#fff}
table{border-collapse:collapse;width:100%}td,th{border-bottom:1px solid #eee;padding:6px;text-align:left}
small{opacity:.6}
</style></head><body>
<h1>AIVO Backtest Report</h1>
<div class="kpi">
<div class="card"><b>Closed Trades</b><div>{closed}</div></div>
<div class="card"><b>Hit Rate</b><div>{hit_rate_pct}%</div></div>
<div class="card"><b>Avg R</b><div>{avg_r}</div></div>
<div class="card"><b>Cum R</b><div>{cum_r}</div></div>
</div>
<h2>Trades</h2>
<table><tr><th>#</th><th>Exit</th><th>R</th><th>Time</th><th>OID</th></tr>
{rows}
</table>
</body></html>"""


def main(inp: str, outp: str) -> None:
    d = json.load(open(inp, "r", encoding="utf-8"))
    rows = []
    for i, s in enumerate(d.get("stats", []), 1):
        ts = datetime.utcfromtimestamp(s["ts"]).isoformat()
        rows.append(
            f"<tr><td>{i}</td><td>{s['exit']}</td><td>{round(s['r'],3)}</td><td><small>{ts}</small></td><td><small>{s['oid']}</small></td></tr>"
        )
    html = TPL.format(
        **{k: d.get(k, "") for k in ["closed_trades", "hit_rate_pct", "avg_r", "cum_r"]},
        rows="\n".join(rows),
    )
    open(outp, "w", encoding="utf-8").write(html)
    print("Saved:", outp)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])


