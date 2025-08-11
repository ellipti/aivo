import csv, json, sys

TPL = """<!doctype html><meta charset="utf-8"><title>AIVO BT Report</title>
<style>body{font:14px system-ui;margin:20px}table{border-collapse:collapse;width:100%}th,td{padding:6px;border-bottom:1px solid #eee}</style>
<h1>AIVO Backtest Report</h1>
<div>Closed: {closed} | Hit: {hit}% | AvgR: {avg_r} | CumR: {cum_r}</div>
<table><tr><th>#</th><th>Side</th><th>Fill</th><th>Exit</th><th>R</th><th>Note</th></tr>{rows}</table>"""


def main(trades_csv, stats_json, out_html):
    s = json.load(open(stats_json, "r", encoding="utf-8"))
    rows = []
    with open(trades_csv, "r", encoding="utf-8") as f:
        for i, r in enumerate(csv.DictReader(f), 1):
            rows.append(
                f"<tr><td>{i}</td><td>{r['side']}</td><td>{r['fill']}</td><td>{r['exit']}</td><td>{r['r']}</td><td>{r['note']}</td></tr>"
            )
    open(out_html, "w", encoding="utf-8").write(
        TPL.format(closed=s["closed_trades"], hit=s["hit_rate_pct"], avg_r=s["avg_r"], cum_r=s["cum_r"], rows="\n".join(rows))
    )


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2], sys.argv[3])


