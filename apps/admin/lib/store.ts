import { Settings } from '../src/types';

export type InMemoryUser = {
  id: string;
  username: string;
  role: 'admin' | 'user';
  status: 'active' | 'disabled';
  createdAt: string;
};

export type InMemoryOrder = {
  id: string;
  time: string;
  symbol: string;
  side: 'BUY' | 'SELL';
  units: number;
  broker: 'oanda' | 'mt5';
  entry: number;
  stopLoss?: number;
  takeProfit?: number;
  pnl?: number;
  status: 'open' | 'closed' | 'rejected';
};

export type InMemorySignal = {
  id: string;
  time: string;
  symbol: 'XAUUSD' | 'EURUSD' | 'GBPUSD' | 'US500' | 'DXY';
  timeframe: 'M1' | 'M5' | 'M15' | 'M30' | 'H1' | 'H4' | 'D1';
  decision: 'BUY' | 'SELL' | 'WAIT';
  entry?: number;
  stopLoss?: number;
  takeProfit?: number;
  confidence: number;
  rationale: string;
  risks: string[];
  tags: string[];
};

let users: InMemoryUser[] = [
  {
    id: '1',
    username: 'admin',
    role: 'admin',
    status: 'active',
    createdAt: new Date().toISOString(),
  },
  {
    id: '2',
    username: 'user1',
    role: 'user',
    status: 'active',
    createdAt: new Date().toISOString(),
  },
];

let orders: InMemoryOrder[] = Array.from({ length: 12 }).map((_, i) => ({
  id: String(i + 1),
  time: new Date(Date.now() - i * 3600_000).toISOString(),
  symbol: i % 2 ? 'EURUSD' : 'XAUUSD',
  side: i % 2 ? 'BUY' : 'SELL',
  units: 1000 + i * 100,
  broker: i % 3 ? 'oanda' : 'mt5',
  entry: 1.1 + i * 0.001,
  stopLoss: 1.09,
  takeProfit: 1.12,
  pnl: i % 2 ? 12.3 : -5.4,
  status: i % 4 === 0 ? 'rejected' : i % 3 === 0 ? 'open' : 'closed',
}));

const symbols = ['XAUUSD', 'EURUSD', 'GBPUSD', 'US500', 'DXY'] as const;
const timeframes = ['M15', 'M30', 'H1', 'H4', 'D1'] as const;
const decisions = ['BUY', 'SELL', 'WAIT'] as const;

let signals: InMemorySignal[] = Array.from({ length: 15 }).map((_, i) => ({
  id: String(i + 1),
  time: new Date(Date.now() - i * 1800_000).toISOString(),
  symbol: symbols[i % symbols.length]!,
  timeframe: timeframes[i % timeframes.length]!,
  decision: decisions[i % decisions.length]!,
  entry: 1.1234,
  stopLoss: 1.12,
  takeProfit: 1.13,
  confidence: Math.min(0.95, 0.5 + i * 0.02),
  rationale: 'Model rationale placeholder',
  risks: ['Volatility', 'News'],
  tags: ['trend', 'breakout'],
}));

let settings: Settings = {
  broker: { MODE: 'oanda', OANDA_ENV: 'practice', OANDA_ACCOUNT_ID: '••••••' },
  risk: { maxRiskPct: 1, minRR: 1.5, atrMultiplier: 1.5 },
  schedule: {
    sessions: { tokyo: true, london: true, newyork: true },
    timezone: 'Asia/Ulaanbaatar',
  },
  news: { highImpactOnly: true },
};

export const store = {
  users,
  setUsers(next: InMemoryUser[]) {
    users = next;
    this.users = users;
  },
  orders,
  setOrders(next: InMemoryOrder[]) {
    orders = next;
    this.orders = orders;
  },
  signals,
  setSignals(next: InMemorySignal[]) {
    signals = next;
    this.signals = signals;
  },
  settings,
  setSettings(next: Settings) {
    settings = next;
    this.settings = settings;
  },
};
