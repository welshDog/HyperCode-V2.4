package main

import (
    "sync"
    "testing"
    "time"
)

func TestConcurrentRoundtripLatency(t *testing.T) {
    if testing.Short() { t.Skip("short") }
    n := 100
    var wg sync.WaitGroup
    errs := 0
    max := time.Duration(0)
    for i := 0; i < n; i++ {
        wg.Add(1)
        go func(k int){
            defer wg.Done()
            t0 := time.Now()
            out, err := generate("test")
            dt := time.Since(t0)
            if dt > max { max = dt }
            if err != nil || out == "" { errs++ }
        }(i)
    }
    wg.Wait()
    if errs > 0 { t.Fatalf("errors: %d", errs) }
    if max > 5*time.Second { t.Fatalf("latency exceeded: %s", max) }
}

