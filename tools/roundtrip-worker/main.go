package main

import (
    "bytes"
    "context"
    "encoding/json"
    "fmt"
    "log"
    "net/http"
    "os"
    "time"

    prom "github.com/prometheus/client_golang/prometheus"
    promhttp "github.com/prometheus/client_golang/prometheus/promhttp"
    "go.opentelemetry.io/otel"
    "go.opentelemetry.io/otel/attribute"
    "go.opentelemetry.io/otel/exporters/otlp/otlptrace/otlptracehttp"
    "go.opentelemetry.io/otel/sdk/resource"
    sdktrace "go.opentelemetry.io/otel/sdk/trace"
)

var (
    rtHistogram = prom.NewHistogram(prom.HistogramOpts{
        Name:    "roundtrip_latency_seconds",
        Help:    "Roundtrip latency to Ollama",
        Buckets: prom.LinearBuckets(0.1, 0.5, 20),
    })
)

func initTelemetry() func(context.Context) error {
    exp, err := otlptracehttp.New(context.Background(), otlptracehttp.WithInsecure(), otlptracehttp.WithEndpoint("jaeger:4318"))
    if err != nil { log.Printf("otel exporter init error: %v", err) }
    res := resource.NewWithAttributes("", attribute.String("service.name", "roundtrip-worker"))
    tp := sdktrace.NewTracerProvider(sdktrace.WithBatcher(exp), sdktrace.WithResource(res))
    otel.SetTracerProvider(tp)
    return tp.Shutdown
}

func generate(prompt string) (string, error) {
    t := otel.Tracer("roundtrip")
    ctx, span := t.Start(context.Background(), "generate")
    defer span.End()
    url := "http://ollama:11434/api/generate"
    body := map[string]any{"model": "qwen2.5-coder:7b", "prompt": prompt, "stream": false}
    b, _ := json.Marshal(body)
    t0 := time.Now()
    req, _ := http.NewRequestWithContext(ctx, http.MethodPost, url, bytes.NewReader(b))
    req.Header.Set("Content-Type", "application/json")
    client := &http.Client{ Timeout: 30 * time.Second }
    resp, err := client.Do(req)
    if err != nil { span.SetAttributes(attribute.String("error", err.Error())); return "", err }
    defer resp.Body.Close()
    var out struct{ Response string `json:"response"` }
    if err := json.NewDecoder(resp.Body).Decode(&out); err != nil { return "", err }
    rtHistogram.Observe(time.Since(t0).Seconds())
    return out.Response, nil
}

func main() {
    prom.MustRegister(rtHistogram)
    mux := http.NewServeMux()
    mux.Handle("/metrics", promhttp.Handler())
    go http.ListenAndServe(":9100", mux)
    shutdown := initTelemetry()
    defer func(){ _ = shutdown(context.Background()) }()
    prompt := os.Getenv("PROMPT")
    if prompt == "" { prompt = "Write hello world in Python" }
    out, err := generate(prompt)
    if err != nil || out == "" { log.Fatalf("roundtrip failed: %v", err) }
    fmt.Println(out)
}
