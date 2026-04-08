FROM golang:1.21-alpine AS builder

WORKDIR /app

# Download dependencies first for better caching
COPY go.mod go.sum* ./
RUN go mod download

COPY . .
RUN go build -ldflags="-w -s" -o /roundtrip-worker

FROM alpine:3.19

RUN apk add --no-cache ca-certificates

COPY --from=builder /roundtrip-worker /usr/local/bin/roundtrip-worker

EXPOSE 9100

ENTRYPOINT ["/usr/local/bin/roundtrip-worker"]
