# Build context: monorepo root (.)
# This Dockerfile is referenced via: apps/web/Dockerfile
# Build command: docker build -f apps/web/Dockerfile .
# Docker Compose: context: . / dockerfile: apps/web/Dockerfile
#
# pnpm workspace layout expected in context root:
#   pnpm-lock.yaml        ← monorepo lock file
#   pnpm-workspace.yaml   ← workspace manifest
#   package.json          ← root package.json
#   apps/web/package.json ← web package.json

FROM node:22-alpine AS base
# Enable corepack for pnpm support (node:22 ships with corepack built-in)
RUN corepack enable

# ── Stage: deps ──────────────────────────────────────────────
# Install workspace dependencies needed for build (includes devDeps)
FROM base AS deps
RUN apk add --no-cache libc6-compat
WORKDIR /app

# Copy only the files needed for dependency resolution
# This layer is cached unless lock file or package manifests change
COPY pnpm-lock.yaml pnpm-workspace.yaml package.json ./
COPY apps/web/package.json ./apps/web/

# Install web workspace deps only (pnpm puts them in root node_modules via symlinks)
RUN pnpm install --frozen-lockfile --filter web

# ── Stage: builder ───────────────────────────────────────────
FROM base AS builder
WORKDIR /app

# pnpm workspace layout: root node_modules holds the .pnpm virtual store,
# apps/web/node_modules holds per-workspace symlinks (e.g. .bin/next → root .pnpm store)
# Both are required for binaries like `next` to be found during build
COPY --from=deps /app/node_modules ./node_modules
COPY --from=deps /app/apps/web/node_modules ./apps/web/node_modules
# Copy full source (Dockerfile.dockerignore excludes node_modules so these won't be overwritten)
COPY . .

ENV NEXT_TELEMETRY_DISABLED=1
ENV NODE_OPTIONS="--max-old-space-size=2048"
ENV SENTRY_SKIP_SOURCE_MAP_UPLOAD=true

ARG CACHE_BUST=1

RUN pnpm --filter web run build

# ── Stage: runner ────────────────────────────────────────────
FROM base AS runner
WORKDIR /app

ENV NODE_ENV=production
ENV NEXT_TELEMETRY_DISABLED=1

RUN addgroup --system --gid 1001 nodejs
RUN adduser --system --uid 1001 nextjs

COPY --from=builder /app/apps/web/public ./public

RUN mkdir .next
RUN chown nextjs:nodejs .next

# Next.js standalone output (configured in next.config.ts via output: 'standalone')
COPY --from=builder --chown=nextjs:nodejs /app/apps/web/.next/standalone ./
COPY --from=builder --chown=nextjs:nodejs /app/apps/web/.next/static ./.next/static

USER nextjs

EXPOSE 3000
ENV PORT=3000
ENV HOSTNAME="0.0.0.0"
ENV API_INTERNAL_URL="http://api:8001"

CMD ["node", "server.js"]
