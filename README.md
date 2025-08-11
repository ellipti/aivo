## AIVO Monorepo

Brand: AIVO AI TRADE

### Quickstart

1. Install and build

```
pnpm i && pnpm turbo build
```

2. Run via Docker

```
docker compose up --build
```

Apps

- Web: http://localhost:3000
- Admin: http://localhost:3001
- Analyzer API: http://localhost:7001
- Executor API: http://localhost:7002

### Environment

- Analyzer (services/analyzer/.env.example):
  - `OPENAI_API_KEY=...`
  - `MODEL=gpt-5-thinking` (Responses-capable)
  - `RESPONSE_TOKENS=800`, `TEMPERATURE=0.2`
  - `TE_API_CLIENT`, `TE_API_SECRET` (TradingEconomics)

- Executor (services/executor/.env.example):
  - `EXEC_MODE=oanda`
  - `OANDA_API_KEY=...`, `OANDA_ACCOUNT_ID=...`, `OANDA_ENV=practice|live`
  - `TZ_SCHEDULE=Asia/Ulaanbaatar`, `SCHEDULE_START=09:00`, `SCHEDULE_END=17:00`

- Web/Admin (apps/\*/.env.local.example):
  - `NEXT_PUBLIC_API_ANALYZER_URL=http://localhost:7001`
  - `NEXT_PUBLIC_API_EXECUTOR_URL=http://localhost:7002`

### Troubleshooting

- Node build fails with ESLint option errors: this repo disables ESLint during production builds via `next.config.mjs` for initial scaffolding.
- OpenAI errors: ensure `OPENAI_API_KEY` is set and the selected `MODEL` supports the Responses API.
- OANDA errors: double-check `OANDA_API_KEY`, `OANDA_ACCOUNT_ID`, and account environment.
- Calendar 401: set `TE_API_CLIENT` and `TE_API_SECRET` in analyzer.
- Windows PowerShell: avoid `&&` chaining; run commands separately.
