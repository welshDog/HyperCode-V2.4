FROM golang:1.22-alpine AS builder
WORKDIR /app
COPY go.mod main.go ./
RUN go build -o quantum-compiler .

FROM alpine:3.20
RUN apk --no-cache add ca-certificates
WORKDIR /root/
COPY --from=builder /app/quantum-compiler .
EXPOSE 8081
CMD ["./quantum-compiler"]
