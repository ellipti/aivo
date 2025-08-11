'use client';
import { useEffect, useState } from 'react';
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer } from 'recharts';

export default function DailyPnL() {
  const [data, setData] = useState<any[]>([]);
  useEffect(() => {
    const fetcher = () =>
      fetch('http://localhost:7001/metrics/daily')
        .then((r) => r.json())
        .then(setData);
    fetcher();
    const id = setInterval(fetcher, 60000);
    return () => clearInterval(id);
  }, []);
  return (
    <div className="p-4 bg-white/70 dark:bg-zinc-900 rounded-2xl shadow h-72">
      <div className="mb-2 text-sm opacity-70">Daily P&L (R)</div>
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={data}>
          <XAxis dataKey="day" />
          <YAxis />
          <Tooltip />
          <Bar dataKey="sum_r" />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
