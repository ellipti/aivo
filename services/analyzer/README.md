# Analyzer Service

## Endpoints

- `GET /health` → `{ status, openai }`
- `POST /analyze` → structured decision JSON
- `GET /calendar?symbols=XAUUSD,EURUSD&lookaheadHours=48` → high-impact events

## Environment

- `OPENAI_API_KEY`
- `MODEL` (default `gpt-5-thinking`)
- `RESPONSE_TOKENS` (default `800`)
- `TEMPERATURE` (default `0.2`)
- `MIN_RR` (default `1.5`)
- `TE_API_CLIENT`, `TE_API_SECRET` for TradingEconomics

## Notes

- OpenAI Responses API docs: https://platform.openai.com/docs/guides/reasoning
- TradingEconomics Calendar API docs: https://docs.tradingeconomics.com/
