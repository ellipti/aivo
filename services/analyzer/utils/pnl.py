import sqlite3, os
from datetime import datetime, timezone

DB_PATH = os.environ.get("AIVO_DB_PATH", "aivo_trades.db")

def _q(sql, params=()):
  con = sqlite3.connect(DB_PATH)
  try:
    cur = con.execute(sql, params)
    return cur.fetchall()
  finally:
    con.close()

def kpis():
  total = _q("SELECT COUNT(*) FROM trades")[0][0]
  closed = _q("SELECT COUNT(*) FROM closes")[0][0]
  wins = _q("SELECT COUNT(*) FROM closes WHERE r_multiple > 0")[0][0]
  avg_r = _q("SELECT AVG(r_multiple) FROM closes")[0][0] or 0.0
  cum_r = _q("SELECT COALESCE(SUM(r_multiple),0) FROM closes")[0][0] or 0.0
  hit = (wins / closed * 100.0) if closed else 0.0
  return {
    "total_trades": total,
    "closed_trades": closed,
    "hit_rate_pct": round(hit, 2),
    "avg_r": round(avg_r, 3),
    "cum_r": round(cum_r, 3),
  }

def equity_series(start_balance=10000.0, risk_per_trade_pct=1.0):
  rows = _q("SELECT r_multiple, closed_at FROM closes ORDER BY closed_at ASC")
  eq = start_balance
  series = []
  for r, ts in rows:
    risk_amt = eq * (risk_per_trade_pct/100.0)
    pnl_amt = risk_amt * (r or 0.0)
    eq += pnl_amt
    series.append({
      "t": datetime.fromtimestamp(ts, tz=timezone.utc).isoformat(),
      "equity": round(eq, 2),
      "r": round(r or 0.0, 3)
    })
  return {"start": start_balance, "risk_pct": risk_per_trade_pct, "series": series}

def daily_pnl():
  sql = """
  SELECT DATE(closed_at,'unixepoch') d, SUM(r_multiple) sum_r, COUNT(*) n
  FROM closes GROUP BY d ORDER BY d
  """
  out=[]
  for d, sum_r, n in _q(sql):
    out.append({"day": d, "sum_r": round(sum_r or 0.0, 3), "n": n})
  return out


