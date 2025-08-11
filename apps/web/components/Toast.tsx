'use client';
import { createContext, useCallback, useContext, useMemo, useState } from 'react';

type Toast = { id: number; kind: 'success' | 'error' | 'info'; message: string };

const ToastCtx = createContext<{ add(t: Omit<Toast, 'id'>): void } | null>(null);

export function ToastProvider({ children }: { children: React.ReactNode }) {
  const [toasts, setToasts] = useState<Toast[]>([]);
  const add = useCallback((t: Omit<Toast, 'id'>) => {
    const id = Date.now();
    setToasts((list) => [...list, { id, ...t }]);
    setTimeout(() => setToasts((list) => list.filter((x) => x.id !== id)), 3000);
  }, []);
  const value = useMemo(() => ({ add }), [add]);
  return (
    <ToastCtx.Provider value={value}>
      {children}
      <div className="fixed bottom-4 right-4 space-y-2 z-50">
        {toasts.map((t) => (
          <div
            key={t.id}
            className={`rounded-md px-3 py-2 text-sm shadow border bg-white ${
              t.kind === 'success'
                ? 'border-green-300'
                : t.kind === 'error'
                  ? 'border-red-300'
                  : 'border-gray-300'
            }`}
          >
            {t.message}
          </div>
        ))}
      </div>
    </ToastCtx.Provider>
  );
}

export function useToast() {
  const ctx = useContext(ToastCtx);
  if (!ctx) throw new Error('ToastProvider missing');
  return ctx;
}
