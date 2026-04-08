package e2e

import (
    "net/http"
    "testing"
    "time"
    "sync"
    "bytes"
    "io/ioutil"
)

func TestRoundTripLatencyUnderLoad(t *testing.T) {
    base := "http://localhost:8000/agents"
    // Discover Coder ID
    resp, err := http.Get(base + "/")
    if err != nil { t.Fatalf("list agents: %v", err) }
    body, _ := ioutil.ReadAll(resp.Body)
    resp.Body.Close()
    // naive parse: look for "Coder" and "id":"..."
    var id string
    s := string(body)
    pos := -1
    if idx := IndexOf(s, "\"name\":\"Coder\""); idx >= 0 { pos = idx }
    if pos < 0 { t.Fatalf("Coder not found") }
    // find id
    idStart := IndexOf(s[pos:], "\"id\":\"")
    if idStart < 0 { t.Fatalf("id not found") }
    idStart += pos + len("\"id\":\"")
    idEnd := IndexOfFrom(s, idStart, "\"")
    id = s[idStart:idEnd]

    // Run 100 concurrent requests
    n := 100
    wg := sync.WaitGroup{}
    wg.Add(n)
    deadlines := make(chan time.Duration, n)
    for i := 0; i < n; i++ {
        go func() {
            defer wg.Done()
            start := time.Now()
            payload := []byte(`{"prompt":"time.now()"}`)
            r, err := http.Post(base+"/"+id+"/send", "application/json", bytes.NewBuffer(payload))
            if err != nil { t.Logf("post err: %v", err); return }
            ioutil.ReadAll(r.Body)
            r.Body.Close()
            deadlines <- time.Since(start)
        }()
    }
    wg.Wait()
    close(deadlines)
    // assert latency < 5s
    for d := range deadlines {
        if d > 5*time.Second { t.Fatalf("latency exceeded: %v", d) }
    }
}

func IndexOf(s, sub string) int {
    return IndexOfFrom(s, 0, sub)
}
func IndexOfFrom(s string, from int, sub string) int {
    for i := from; i+len(sub) <= len(s); i++ {
        if s[i:i+len(sub)] == sub { return i }
    }
    return -1
}

