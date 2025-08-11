import { WorldMapHero } from '../components/WorldMapHero';
import Link from 'next/link';

export default function Page() {
  return (
    <main className="container mx-auto px-4 py-10 space-y-16">
      <section className="grid md:grid-cols-2 gap-8 items-center">
        <div className="space-y-4">
          <h1 className="text-4xl md:text-5xl font-bold">AIVO AI TRADE</h1>
          <p className="text-lg text-muted-foreground">
            GPT-д суурилсан судалгаа + автомажсан арилжаа
          </p>
          <div className="flex gap-3 pt-2">
            <Link
              href="/login"
              className="inline-flex items-center rounded-md bg-primary px-4 py-2 text-primary-foreground hover:opacity-90"
            >
              Get Started
            </Link>
            <Link
              href="/dashboard"
              className="inline-flex items-center rounded-md border px-4 py-2 hover:bg-accent"
            >
              View Dashboard
            </Link>
          </div>
        </div>
        <WorldMapHero />
      </section>

      <section className="space-y-6">
        <h2 className="text-2xl font-semibold">Capabilities</h2>
        <div className="grid md:grid-cols-3 gap-4">
          {['GPT Analysis', 'Guardrails', 'Automated Execution'].map((t) => (
            <div key={t} className="rounded-lg border p-4">
              <h3 className="font-medium">{t}</h3>
              <p className="text-sm text-muted-foreground">Production-ready by design.</p>
            </div>
          ))}
        </div>
      </section>

      <section className="space-y-6">
        <h2 className="text-2xl font-semibold">How it works</h2>
        <ol className="grid md:grid-cols-4 gap-4 list-none">
          {['Data', 'GPT', 'Guardrails', 'Execute'].map((t, i) => (
            <li key={t} className="rounded-lg border p-4">
              <div className="text-3xl font-bold">{i + 1}</div>
              <div className="font-medium">{t}</div>
            </li>
          ))}
        </ol>
      </section>

      <section className="space-y-6">
        <h2 className="text-2xl font-semibold">Security</h2>
        <p className="text-muted-foreground">
          Principle of least privilege, audit logs, and secrets hygiene.
        </p>
      </section>

      <section className="space-y-6">
        <h2 className="text-2xl font-semibold">Pricing</h2>
        <p className="text-muted-foreground">Coming soon.</p>
      </section>
    </main>
  );
}
