## AIVO Monorepo

Run in 3 steps:

1. Install deps

```
pnpm install
```

2. Build everything

```
pnpm turbo build
```

3. Start dev servers (in separate terminals)

```
pnpm --filter @aivo/web dev
pnpm --filter @aivo/admin dev
```

Docker services:

```
docker compose up --build
```

