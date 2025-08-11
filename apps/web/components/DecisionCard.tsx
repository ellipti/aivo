'use client';
import { useState } from 'react';

type Decision = {
  decision: 'BUY' | 'SELL' | 'WAIT';
  entry?: number | null;
  stopLoss?: number | null;
  takeProfit?: number | null;
  confidence: number;
  rationale: string;
  risks: string[];
  tags: string[];
};

export function DecisionCard({ data, onExecute }: { data: Decision; onExecute(): void }) {
  const [open, setOpen] = useState(false);
  const badge =
    data.decision === 'BUY'
      ? 'bg-green-600'
      : data.decision === 'SELL'
        ? 'bg-red-600'
        : 'bg-gray-500';
  return (
    <div className="rounded-lg border p-4 space-y-3">
      <div className="flex items-center gap-3">
        <span className={`text-white text-xs px-2 py-1 rounded ${badge}`}>{data.decision}</span>
        <div className="text-sm text-muted-foreground">Decision</div>
      </div>
      <div className="grid grid-cols-3 gap-4 text-sm">
        <div>Entry: {data.entry ?? '--'}</div>
        <div>SL: {data.stopLoss ?? '--'}</div>
        <div>TP: {data.takeProfit ?? '--'}</div>
      </div>
      <div className="w-full bg-gray-200 rounded h-2">
        <div
          className="bg-blue-600 h-2 rounded"
          style={{ width: `${Math.round(data.confidence * 100)}%` }}
        />
      </div>
      <button onClick={() => setOpen((v) => !v)} className="text-sm underline">
        {open ? 'Hide' : 'Show'} rationale
      </button>
      {open && (
        <pre className="text-xs whitespace-pre-wrap bg-muted/40 p-3 rounded">{data.rationale}</pre>
      )}
      <div className="flex gap-2">
        <button onClick={onExecute} className="rounded-md border px-3 py-2">
          Execute Trade
        </button>
        <button className="rounded-md border px-3 py-2">Discard</button>
      </div>
    </div>
  );
}
