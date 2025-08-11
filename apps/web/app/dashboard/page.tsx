export default function DashboardPage() {
  return (
    <main className="container mx-auto px-4 py-10 space-y-8">
      <h1 className="text-2xl font-semibold">Dashboard</h1>
      <section>
        <h2 className="font-medium mb-2">KPIs</h2>
        <div className="grid md:grid-cols-4 gap-4">
          {['PnL', 'Win Rate', 'Sharpe', 'Open Trades'].map((k) => (
            <div key={k} className="rounded-lg border p-4">
              <div className="text-sm text-muted-foreground">{k}</div>
              <div className="text-2xl font-bold">--</div>
            </div>
          ))}
        </div>
      </section>
      <section>
        <h2 className="font-medium mb-2">Orders</h2>
        <OrdersTable />
      </section>
      <section>
        <h2 className="font-medium mb-2">Signals</h2>
        <SignalsList />
        <div className="pt-4">
          <a
            href="/analyze"
            className="inline-flex items-center rounded-md bg-primary px-4 py-2 text-primary-foreground hover:opacity-90"
          >
            GPT Analyze
          </a>
        </div>
      </section>
    </main>
  );
}

async function getOrders() {
  const res = await fetch(`${process.env['NEXT_PUBLIC_URL'] ?? ''}/api/orders`, {
    cache: 'no-store',
  });
  return res.json().catch(() => ({ orders: [] }));
}

async function getSignals() {
  const res = await fetch(`${process.env['NEXT_PUBLIC_URL'] ?? ''}/api/signals`, {
    cache: 'no-store',
  });
  return res.json().catch(() => ({ items: [] }));
}

async function OrdersTable() {
  const data = await getOrders();
  const items = (data.orders || data) as any[];
  return (
    <div className="rounded-lg border overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="bg-muted/50 text-left">
            <th className="p-2">Time</th>
            <th className="p-2">Instrument</th>
            <th className="p-2">Side</th>
            <th className="p-2">Units</th>
            <th className="p-2">Status</th>
          </tr>
        </thead>
        <tbody>
          {items.slice(0, 10).map((o: any, i: number) => (
            <tr key={o.id || i} className="border-t">
              <td className="p-2">{o.time || '--'}</td>
              <td className="p-2">{o.instrument || o.symbol || '--'}</td>
              <td className="p-2">{o.side || '--'}</td>
              <td className="p-2">{o.units || '--'}</td>
              <td className="p-2">{o.state || o.status || '--'}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

async function SignalsList() {
  const data = await getSignals();
  const items = (data.items || []) as any[];
  return (
    <ul className="space-y-2 text-sm">
      {items
        .slice()
        .reverse()
        .slice(0, 10)
        .map((s: any, i: number) => (
          <li key={i} className="border rounded-md p-3">
            <div className="text-muted-foreground">
              {new Date(s.ts || Date.now()).toLocaleString()}
            </div>
            <div>
              {s.symbol} {s.timeframe} → {s.result?.decision}
            </div>
          </li>
        ))}
    </ul>
  );
}
