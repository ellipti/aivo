FROM node:20-alpine AS base
WORKDIR /app

# Install pnpm
RUN corepack enable && corepack prepare pnpm@9.6.0 --activate

# Copy monorepo
COPY . .

# Install deps (monorepo)
RUN pnpm install --frozen-lockfile

# Build only web app
RUN pnpm --filter @aivo/web build

EXPOSE 3000
CMD ["pnpm", "--filter", "@aivo/web", "start", "-p", "3000"]

