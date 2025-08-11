'use client';
import { useEffect } from 'react';
import { useForm } from 'react-hook-form';

type Values = {
  riskPolicy: {
    maxRiskPct: number;
    maxConcurrentTrades: number;
    minRR: number;
    atrMultiplierForSL: number;
  };
  schedule: {
    timezone: string;
    sessions: { tokyo: boolean; london: boolean; newyork: boolean };
  };
  newsFilter: { highImpactOnly: boolean };
};

export default function SettingsPage() {
  const { register, handleSubmit, reset } = useForm<Values>();

  useEffect(() => {
    fetch('/api/config')
      .then((r) => r.json())
      .then((j) => reset(j))
      .catch(() => {
        reset({
          riskPolicy: {
            maxRiskPct: 1,
            maxConcurrentTrades: 3,
            minRR: 1.5,
            atrMultiplierForSL: 1.5,
          },
          schedule: {
            timezone: 'Asia/Ulaanbaatar',
            sessions: { tokyo: true, london: true, newyork: true },
          },
          newsFilter: { highImpactOnly: true },
        });
      });
  }, [reset]);

  const onSubmit = async (v: Values) => {
    await fetch('/api/config', {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(v),
    });
    alert('Saved');
  };

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="space-y-6 max-w-xl">
      <h1 className="text-2xl font-semibold">Settings</h1>

      <section className="space-y-3">
        <h2 className="font-medium">Risk Policy</h2>
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="block text-sm mb-1">MaxRisk %</label>
            <input
              type="number"
              step="0.1"
              className="w-full border rounded-md px-3 py-2"
              {...register('riskPolicy.maxRiskPct', { valueAsNumber: true })}
            />
          </div>
          <div>
            <label className="block text-sm mb-1">MaxConcurrentTrades</label>
            <input
              type="number"
              className="w-full border rounded-md px-3 py-2"
              {...register('riskPolicy.maxConcurrentTrades', { valueAsNumber: true })}
            />
          </div>
          <div>
            <label className="block text-sm mb-1">MinRR</label>
            <input
              type="number"
              step="0.1"
              className="w-full border rounded-md px-3 py-2"
              {...register('riskPolicy.minRR', { valueAsNumber: true })}
            />
          </div>
          <div>
            <label className="block text-sm mb-1">ATRMultiplierForSL</label>
            <input
              type="number"
              step="0.1"
              className="w-full border rounded-md px-3 py-2"
              {...register('riskPolicy.atrMultiplierForSL', { valueAsNumber: true })}
            />
          </div>
        </div>
      </section>

      <section className="space-y-3">
        <h2 className="font-medium">Trading Schedule</h2>
        <div>
          <label className="block text-sm mb-1">Timezone</label>
          <input
            className="w-full border rounded-md px-3 py-2"
            {...register('schedule.timezone')}
          />
        </div>
        <div className="flex gap-4 text-sm">
          <label className="inline-flex items-center gap-2">
            <input type="checkbox" {...register('schedule.sessions.tokyo')} /> Tokyo
          </label>
          <label className="inline-flex items-center gap-2">
            <input type="checkbox" {...register('schedule.sessions.london')} /> London
          </label>
          <label className="inline-flex items-center gap-2">
            <input type="checkbox" {...register('schedule.sessions.newyork')} /> New York
          </label>
        </div>
      </section>

      <section className="space-y-3">
        <h2 className="font-medium">News Filter</h2>
        <label className="inline-flex items-center gap-2 text-sm">
          <input type="checkbox" {...register('newsFilter.highImpactOnly')} /> High-impact only
        </label>
      </section>

      <div>
        <button className="rounded-md bg-primary text-primary-foreground px-4 py-2">Save</button>
      </div>
    </form>
  );
}
