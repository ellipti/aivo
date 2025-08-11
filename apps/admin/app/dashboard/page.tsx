'use client';
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
