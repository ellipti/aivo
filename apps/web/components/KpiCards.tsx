'use client';
import { useEffect, useState } from 'react';

export default function KpiCards() {
  const [data, setData] = useState<any | null>(null);
  useEffect(() => {
    const fetcher = () =>
      fetch('http://localhost:7001/metrics/kpis')
        .then((r) => r.json())
        .then(setData);
    fetcher();
    const id = setInterval(fetcher, 5000);
    return () => clearInterval(id);
  }, []);
  if (!data) return <div>Loading KPIs…</div>;
  return (
    <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
      <Card title="Closed Trades" value={data.closed_trades} />
      <Card title="Hit Rate (%)" value={data.hit_rate_pct} />
      <Card title="Avg R" value={data.avg_r} />
      <Card title="Cum R" value={data.cum_r} />
    </div>
  );
}

function Card({ title, value }: { title: string; value: any }) {
  return (
    <div className="p-4 bg-white/70 dark:bg-zinc-900 rounded-2xl shadow">
      <div className="text-sm opacity-70">{title}</div>
      <div className="text-2xl font-semibold">{String(value)}</div>
    </div>
  );
}
