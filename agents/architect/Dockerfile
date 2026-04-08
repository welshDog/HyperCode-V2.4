# agents/architect/Dockerfile
# NestJS TypeScript agent — multi-stage build for lean production image.

# ── Stage 1: Build ─────────────────────────────────────────────────────────
FROM node:20-alpine AS builder

WORKDIR /build

# Install deps first (cached layer)
COPY package.json package-lock.json ./
RUN npm ci

# Copy source and compile TypeScript → dist/
COPY tsconfig*.json ./
COPY src/ src/
RUN npm run build

# ── Stage 2: Runtime ───────────────────────────────────────────────────────
FROM node:20-alpine AS runtime

RUN apk add --no-cache curl

WORKDIR /app

# Copy only production deps + compiled output
COPY package.json package-lock.json ./
RUN npm ci --omit=dev

COPY --from=builder /build/dist ./dist

ENV PORT=8080 \
    NODE_ENV=production

EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=10s --retries=3 --start-period=10s \
    CMD curl -f http://localhost:8080/health || exit 1

CMD ["node", "dist/main"]
