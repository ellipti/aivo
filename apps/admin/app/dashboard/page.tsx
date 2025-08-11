'use client';
import { useEffect, useState } from 'react';
import {
  ResponsiveContainer,
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  BarChart,
  Bar,
} from 'recharts';

const timeData = Array.from({ length: 8 }).map((_, i) => ({
  t: `T${i + 1}`,
  v: Math.round(Math.random() * 100),
}));

export default function DashboardPage() {
  const [positions, setPositions] = useState<number>(0);
  const [orders, setOrders] = useState<number>(0);

  useEffect(() => {
    const load = async () => {
      try {
        const [p, o] = await Promise.all([
          fetch('/api/positions').then((r) => r.json()),
          fetch('/api/orders').then((r) => r.json()),
        ]);
        setPositions((p?.items || []).length);
        setOrders((o?.items || []).length);
      } catch {
        // ignore
      }
    };
    load();
  }, []);

  return (
    <div className="space-y-10">
      <section>
        <h1 className="text-2xl font-semibold mb-4">System Health</h1>
        <div className="grid md:grid-cols-2 gap-4">
          <div className="rounded-lg border p-4">
            <div className="text-sm text-muted-foreground">Analyzer</div>
            <div className="text-xl font-bold">Healthy</div>
          </div>
          <div className="rounded-lg border p-4">
            <div className="text-sm text-muted-foreground">Executor</div>
            <div className="text-xl font-bold">Healthy</div>
          </div>
        </div>
        <div className="grid md:grid-cols-2 gap-4 mt-4">
          <div className="rounded-lg border p-4">
            <div className="text-sm text-muted-foreground">Open Positions</div>
            <div className="text-2xl font-bold">{positions}</div>
          </div>
          <div className="rounded-lg border p-4">
            <div className="text-sm text-muted-foreground">Pending Orders</div>
            <div className="text-2xl font-bold">{orders}</div>
          </div>
        </div>
      </section>

      <section className="grid md:grid-cols-2 gap-8">
        <div className="rounded-lg border p-4">
          <div className="mb-2 font-medium">Request Throughput</div>
          <div className="h-48">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={timeData}>
                <XAxis dataKey="t" />
                <YAxis />
                <Tooltip />
                <Line type="monotone" dataKey="v" stroke="#4f46e5" />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>
        <div className="rounded-lg border p-4">
          <div className="mb-2 font-medium">Error Rate</div>
          <div className="h-48">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={timeData}>
                <XAxis dataKey="t" />
                <YAxis />
                <Tooltip />
                <Bar dataKey="v" fill="#ef4444" />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      </section>

      <section className="grid md:grid-cols-2 gap-8">
        <div className="rounded-lg border p-4">
          <div className="mb-2 font-medium">GPT Usage</div>
          <div className="h-48">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={timeData}>
                <XAxis dataKey="t" />
                <YAxis />
                <Tooltip />
                <Line type="monotone" dataKey="v" stroke="#22c55e" />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>
        <div className="rounded-lg border p-4">
          <div className="mb-2 font-medium">User Growth</div>
          <div className="h-48">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={timeData}>
                <XAxis dataKey="t" />
                <YAxis />
                <Tooltip />
                <Bar dataKey="v" fill="#06b6d4" />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      </section>
    </div>
  );
}
