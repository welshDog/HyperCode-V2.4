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

# apk upgrade pulls patched Alpine libs (openssl/libcrypto3/libssl3) newer than the base tag
RUN apk upgrade --no-cache && apk add --no-cache curl

# Create non-root user — security hardening
RUN addgroup -S appgroup && adduser -S appuser -G appgroup

WORKDIR /app

# Copy only production deps + compiled output
COPY package.json package-lock.json ./
RUN npm ci --omit=dev

# The runtime only executes `node dist/main`. npm/npx/corepack/yarn ship their own
# bundled copies of tar, glob, minimatch, sigstore, pacote... that are not our
# dependencies but show up as CVEs in image scans. Remove them from the final image.
RUN rm -rf /usr/local/lib/node_modules/npm /usr/local/lib/node_modules/corepack \
           /usr/local/bin/npm /usr/local/bin/npx /usr/local/bin/corepack \
           /opt/yarn-* /usr/local/bin/yarn /usr/local/bin/yarnpkg

COPY --from=builder /build/dist ./dist

RUN chown -R appuser:appgroup /app

ENV PORT=8080 \
    NODE_ENV=production

USER appuser

EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=10s --retries=3 --start-period=10s \
    CMD curl -f http://localhost:8080/health || exit 1

CMD ["node", "dist/main"]
