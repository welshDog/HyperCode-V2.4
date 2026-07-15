# Multi-stage build for Next.js Dashboard

# Stage 1: Install dependencies
FROM node:20-alpine AS deps
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci

# Stage 2: Build the application
FROM node:20-alpine AS builder
WORKDIR /app
COPY --from=deps /app/node_modules ./node_modules
COPY . .

# Set environment variables for build
ENV NEXT_TELEMETRY_DISABLED=1
ENV NODE_ENV=production
ARG NEXT_PUBLIC_HYPER_BRAIN_URL
ENV NEXT_PUBLIC_HYPER_BRAIN_URL=$NEXT_PUBLIC_HYPER_BRAIN_URL
# Optional override; the component falls back to the public Vercel URL.
ARG NEXT_PUBLIC_UNIVERSE_URL
ENV NEXT_PUBLIC_UNIVERSE_URL=$NEXT_PUBLIC_UNIVERSE_URL

# Cap the build heap. HYPERFOCUSzone has 7.8GB PHYSICAL RAM and WSL is capped at
# 4GB; an uncapped Node will happily reach for more than the VM has, and WSL kills
# the whole Docker engine when it does. That is exactly how this build died on
# 2026-07-12: `next build` reached the optimize phase at ~215s and the engine's
# pipe closed (EOF). 1.5GB is ample for this app and leaves the VM room to live.
ENV NODE_OPTIONS="--max-old-space-size=1536"

# Build Next.js app
RUN npm run build

# Stage 3: Production server
FROM node:20-alpine AS runner
WORKDIR /app

ENV NODE_ENV=production
ENV NEXT_TELEMETRY_DISABLED=1
ENV PORT=3000
ENV HOSTNAME=0.0.0.0

# Create non-root user
RUN addgroup --system --gid 1001 nodejs
RUN adduser --system --uid 1001 nextjs

# Copy necessary files
COPY --from=builder /app/public ./public
COPY --from=builder --chown=nextjs:nodejs /app/.next/standalone ./
COPY --from=builder --chown=nextjs:nodejs /app/.next/static ./.next/static

USER nextjs

EXPOSE 3000

# 90s start-period + 10s timeout: gives the Next.js server room to boot and
# compile the first /api/health request on a cold start before checks count.
# Matches the docker-compose.agents.yml override so direct `docker run` behaves
# the same as the composed service.
HEALTHCHECK --interval=30s --timeout=10s --start-period=90s --retries=3 \
  CMD node -e "require('http').get('http://localhost:'+(process.env.PORT||3000)+'/api/health', (r) => { if (r.statusCode !== 200) process.exit(1); }).on('error', () => process.exit(1))"

CMD ["node", "server.js"]
