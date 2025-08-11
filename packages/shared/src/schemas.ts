import { z } from 'zod';

export const SignalSchema = z.object({
  id: z.string(),
  time: z.string(),
  symbol: z.enum(['XAUUSD', 'EURUSD', 'GBPUSD', 'US500', 'DXY']),
  timeframe: z.enum(['M1', 'M5', 'M15', 'M30', 'H1', 'H4', 'D1']),
  decision: z.enum(['BUY', 'SELL', 'WAIT']),
  entry: z.number().optional(),
  stopLoss: z.number().optional(),
  takeProfit: z.number().optional(),
  confidence: z.number().min(0).max(1),
  rationale: z.string(),
  risks: z.array(z.string()),
  tags: z.array(z.string()),
});

export const OrderSchema = z.object({
  id: z.string(),
  time: z.string(),
  symbol: z.string(),
  side: z.enum(['BUY', 'SELL']),
  units: z.number(),
  broker: z.enum(['oanda', 'mt5']),
  entry: z.number(),
  stopLoss: z.number().optional(),
  takeProfit: z.number().optional(),
  pnl: z.number().optional(),
  status: z.enum(['open', 'closed', 'rejected']),
});

export const UserSchema = z.object({
  id: z.string(),
  username: z.string(),
  role: z.enum(['admin', 'user']),
  status: z.enum(['active', 'disabled']),
  createdAt: z.string(),
});

export const SettingsSchema = z.object({
  broker: z.object({
    MODE: z.enum(['oanda', 'mt5']),
    OANDA_ENV: z.enum(['practice', 'live']),
    OANDA_ACCOUNT_ID: z.string().optional(),
  }),
  risk: z.object({
    maxRiskPct: z.number(),
    minRR: z.number(),
    atrMultiplier: z.number(),
  }),
  schedule: z.object({
    sessions: z.object({ tokyo: z.boolean(), london: z.boolean(), newyork: z.boolean() }),
    timezone: z.literal('Asia/Ulaanbaatar'),
  }),
  news: z.object({ highImpactOnly: z.boolean() }),
});

export type Signal = z.infer<typeof SignalSchema>;
export type Order = z.infer<typeof OrderSchema>;
export type User = z.infer<typeof UserSchema>;
export type Settings = z.infer<typeof SettingsSchema>;
