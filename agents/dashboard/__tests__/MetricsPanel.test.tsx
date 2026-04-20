import { render, screen, waitFor } from "@testing-library/react"
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest"
import { MetricsPanel } from "../components/MetricsPanel"

describe("MetricsPanel", () => {
  beforeEach(() => {
    vi.resetAllMocks()
  })

  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it("renders a skeleton while loading", () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockReturnValue(new Promise(() => {}))
    )

    render(<MetricsPanel />)
    expect(screen.getByTestId("metrics-panel")).toBeTruthy()
  })

  it("renders queue depths and alert counts", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: true,
        status: 200,
        json: async () => ({
          requestsPerMin: 120,
          avgResponseMs: 42,
          healsToday: 7,
          errorRatePct: 0.5,
          activeAgents: 25,
          redisQueueDepth: 3,
          celeryQueueDepths: {
            "hypercode-high": 1,
            "hypercode-normal": 4,
            "hypercode-low": 0,
            "main-queue": 0,
          },
          dlqDepth: 2,
          alertFiring: 3,
          alertPending: 1,
          alertTopFiring: [
            { alertname: "CeleryDLQFlooding", severity: "critical", summary: "DLQ is growing fast" },
            { alertname: "DBPoolExhausted", severity: "warning", summary: "DB pool at capacity" },
            { alertname: "RedisLatencyHigh", severity: "info", summary: "Redis p99 latency high" },
          ],
          collectedAt: "2026-04-20T00:00:00Z",
        }),
      })
    )

    render(<MetricsPanel />)

    await waitFor(() => {
      expect(screen.getByText("Ops Pulse")).toBeTruthy()
      expect(screen.getByText("Queues")).toBeTruthy()
      expect(screen.getByText("Redis Backlog")).toBeTruthy()
    })

    expect(screen.getAllByText(/FIRING/i).length).toBeGreaterThan(0)
    expect(screen.getAllByText(/PENDING/i).length).toBeGreaterThan(0)
    expect(screen.getAllByText(/DLQ/i).length).toBeGreaterThan(0)
    expect(screen.getByText("High")).toBeTruthy()
    expect(screen.getByText("Normal")).toBeTruthy()
    expect(screen.getByText("CeleryDLQFlooding")).toBeTruthy()
    expect(screen.getByText("DBPoolExhausted")).toBeTruthy()
  })

  it("shows an error state when metrics fetch fails", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: false,
        status: 503,
        json: async () => ({}),
      })
    )

    render(<MetricsPanel />)

    await waitFor(() => {
      expect(screen.getByText("Metrics unavailable")).toBeTruthy()
    })
  })
})
