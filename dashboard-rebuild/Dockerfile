FROM node:20.20.2-alpine AS builder

WORKDIR /build

# Copy package files
COPY package.json package-lock.json* ./

# Install dependencies
RUN npm ci

# Copy ALL source
COPY . .

# Build
RUN npm run build

# Runtime
FROM node:20.20.2-alpine

RUN addgroup -g 101 -S nextjs && \
    adduser -S -D -H -u 101 -h /app -s /sbin/nologin -G nextjs -g nextjs nextjs

WORKDIR /app

COPY --from=builder /build/node_modules ./node_modules
COPY --from=builder /build/.next ./.next
COPY --from=builder /build/public ./public
COPY --from=builder /build/package.json ./
COPY --from=builder /build/server.js ./

EXPOSE 3000

ENV NODE_ENV=production \
    NEXT_TELEMETRY_DISABLED=1

USER nextjs

CMD ["node", "server.js"]
