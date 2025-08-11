'use client';
import { useState } from 'react';
import { z } from 'zod';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { DecisionCard } from '../../components/DecisionCard';
import { useToast } from '../../components/Toast';

const Schema = z.object({
  symbol: z.string().min(3),
  timeframe: z.enum(['M1', 'M5', 'M15', 'M30', 'H1', 'H4', 'D1']),
  useTechnicals: z.boolean().optional(),
  useNews: z.boolean().optional(),
});
type Values = z.infer<typeof Schema>;

// keep types lightweight; DecisionCard dictates rendering

export default function AnalyzePage() {
  const [decision, setDecision] = useState<any | null>(null);
  const [orderResult, setOrderResult] = useState<any | null>(null);
  const { add } = useToast();
  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<Values>({
    resolver: zodResolver(Schema),
    defaultValues: { symbol: 'XAUUSD', timeframe: 'H1', useTechnicals: true, useNews: true },
  });

  const onSubmit = async (v: Values) => {
    const payload: any = { symbol: v.symbol, timeframe: v.timeframe };
    if (v.useTechnicals) payload.technical = { ema: 1, rsi: 50 };
    if (v.useNews) payload.fundamentals = { events: [] };
    const res = await fetch('/api/analyze', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    if (!res.ok) {
      add({ kind: 'error', message: 'Analyze failed' });
      return;
    }
    const json = await res.json();
    setDecision(json);
    add({ kind: 'success', message: 'Analyze complete' });
  };

  const execute = async () => {
    const side = String(decision?.decision || 'WAIT').toUpperCase();
    const payload: any = {
      instrument: 'XAUUSD',
      units: 1000,
      side,
      entryType: 'market',
    };
    const headers: any = {
      'Content-Type': 'application/json',
      'Idempotency-Key': globalThis.crypto?.randomUUID?.() || `${Date.now()}-${Math.random()}`,
    };
    const res = await fetch('/api/orders/place', {
      method: 'POST',
      headers,
      body: JSON.stringify(payload),
    });
    const json = await res.json().catch(() => ({}));
    setOrderResult(json);
    if (!res.ok) {
      add({ kind: 'error', message: `Broker error: ${JSON.stringify(json)}` });
      return;
    }
    add({ kind: 'success', message: 'Order executed' });
  };

  return (
    <main className="container mx-auto px-4 py-10 space-y-8">
      <h1 className="text-2xl font-semibold">Analyze</h1>
      <form onSubmit={handleSubmit(onSubmit)} className="space-y-4 max-w-2xl">
        <div className="grid md:grid-cols-4 gap-4">
          <div className="md:col-span-2">
            <label className="block text-sm mb-1">Symbol</label>
            <input className="w-full border rounded-md px-3 py-2" {...register('symbol')} />
            {errors.symbol && <p className="text-sm text-red-500">{errors.symbol.message}</p>}
          </div>
          <div>
            <label className="block text-sm mb-1">Timeframe</label>
            <select className="w-full border rounded-md px-3 py-2" {...register('timeframe')}>
              {['M1', 'M5', 'M15', 'M30', 'H1', 'H4', 'D1'].map((t) => (
                <option key={t} value={t}>
                  {t}
                </option>
              ))}
            </select>
          </div>
          <div className="flex items-end gap-3">
            <label className="inline-flex items-center gap-2 text-sm">
              <input type="checkbox" {...register('useTechnicals')} /> Use Technicals
            </label>
            <label className="inline-flex items-center gap-2 text-sm">
              <input type="checkbox" {...register('useNews')} /> Use News Filter
            </label>
          </div>
        </div>
        <button
          disabled={isSubmitting}
          className="rounded-md bg-primary text-primary-foreground px-4 py-2"
        >
          Run GPT Analyze
        </button>
      </form>

      {decision && <DecisionCard data={decision} onExecute={execute} />}
      {orderResult && (
        <div className="rounded-md border p-4 text-sm">
          <div>Ticket: {orderResult.order ?? orderResult.deal ?? '-'}</div>
          <div>Retcode: {orderResult.retcode ?? '-'}</div>
          <div>Comment: {orderResult.comment ?? '-'}</div>
        </div>
      )}
    </main>
  );
}
