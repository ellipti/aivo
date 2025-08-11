'use client';
import { useEffect, useState } from 'react';
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer } from 'recharts';

export default function EquityChart() {
  const [data, setData] = useState<any[]>([]);
  useEffect(() => {
    const fetcher = () =>
      fetch('http://localhost:7001/metrics/equity?start_balance=10000&risk_pct=1')
        .then((r) => r.json())
        .then((d) => setData(d.series || []));
    fetcher();
    const id = setInterval(fetcher, 5000);
    return () => clearInterval(id);
  }, []);
  return (
    <div className="p-4 bg-white/70 dark:bg-zinc-900 rounded-2xl shadow h-80">
      <div className="mb-2 text-sm opacity-70">Equity Curve</div>
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={data}>
          <XAxis dataKey="t" hide />
          <YAxis domain={['auto', 'auto']} />
          <Tooltip />
          <Line type="monotone" dataKey="equity" dot={false} />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
