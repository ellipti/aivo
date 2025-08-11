FROM node:20-alpine AS base
WORKDIR /app

RUN corepack enable && corepack prepare pnpm@9.6.0 --activate

COPY . .
RUN pnpm install --frozen-lockfile
RUN pnpm --filter @aivo/admin build

EXPOSE 3001
CMD ["pnpm", "--filter", "@aivo/admin", "start", "-p", "3001"]

