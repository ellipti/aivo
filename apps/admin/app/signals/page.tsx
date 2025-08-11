'use client';
import { useMemo, useState } from 'react';

const initial = Array.from({ length: 20 }).map((_, i) => ({
  id: i + 1,
  text: `Signal ${i + 1} rationale...`,
  ts: Date.now() - i * 60000,
}));

export default function SignalsPage() {
  const [q, setQ] = useState('');
  const data = useMemo(
    () => initial.filter((s) => s.text.toLowerCase().includes(q.toLowerCase())),
    [q],
  );
  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-semibold">Signals</h1>
      <input
        value={q}
        onChange={(e) => setQ(e.target.value)}
        placeholder="Search"
        className="w-full max-w-sm border rounded-md px-3 py-2"
      />
      <ul className="space-y-2">
        {data.map((s) => (
          <li key={s.id} className="border rounded-md p-3 text-sm">
            <div className="text-muted-foreground">{new Date(s.ts).toLocaleString()}</div>
            <div>{s.text}</div>
          </li>
        ))}
      </ul>
    </div>
  );
}
