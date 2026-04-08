import { render, screen, waitFor, act } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { MetricsPanel } from "../components/MetricsPanel";
import * as api from "@/lib/api";

// Mock the API module
vi.mock("@/lib/api", () => ({
  fetchTasks: vi.fn(),
  fetchSystemHealth: vi.fn(),
}));

describe("MetricsPanel", () => {
  beforeEach(() => {
    vi.resetAllMocks();
  });

  it("renders with initial default states", async () => {
    // Mock promises that don't resolve immediately to check initial state
    (api.fetchTasks as any).mockReturnValue(new Promise(() => {}));
    (api.fetchSystemHealth as any).mockReturnValue(new Promise(() => {}));

    render(<MetricsPanel />);

    // Check Infrastructure section headers
    expect(screen.getByText("Infrastructure")).toBeTruthy();
    
    // Check default "unknown" statuses
    const unknownElements = screen.getAllByText("unknown");
    expect(unknownElements.length).toBeGreaterThan(0);

    // Check Task Velocity section
    expect(screen.getByText("Task Velocity")).toBeTruthy();
    expect(screen.getByText("/ 0 tasks")).toBeTruthy(); // Initial total is 0

    // Check Compliance section
    expect(screen.getByText("Fediversity Ready")).toBeTruthy();
  });

  it("updates with fetched data correctly (Happy Path)", async () => {
    // Mock successful API responses
    const mockTasks = [
      { id: 1, status: "completed" },
      { id: 2, status: "done" }, // treated as completed
      { id: 3, status: "pending" },
      { id: 4, status: "in_progress" },
    ];

    const mockHealth = {
      redis: { status: "healthy" },
      postgres: { status: "healthy" },
      minio: { status: "healthy" },
      tempo: { status: "healthy" },
    };

    (api.fetchTasks as any).mockResolvedValue(mockTasks);
    (api.fetchSystemHealth as any).mockResolvedValue(mockHealth);

    render(<MetricsPanel />);

    // Wait for data to load
    await waitFor(() => {
      // 2 completed tasks out of 4 total
      expect(screen.getByText("2")).toBeTruthy(); 
      expect(screen.getByText("/ 4 tasks")).toBeTruthy();
    });

    // Check pending count (4 total - 2 completed = 2 pending)
    expect(screen.getByText("2 tasks pending in queue")).toBeTruthy();

    // Check health statuses
    const healthyElements = screen.getAllByText("healthy");
    expect(healthyElements).toHaveLength(4); // redis, postgres, minio, tempo
    
    // Check color classes (emerald-500 for healthy)
    healthyElements.forEach(el => {
      expect(el.className).toContain("text-emerald-500");
    });
  });

  it("handles degraded and down system health statuses", async () => {
    const mockTasks: any[] = [];
    const mockHealth = {
      redis: { status: "degraded" },
      postgres: { status: "down" },
      minio: { status: "unknown" }, // Test default/unknown path
      tempo: { status: "healthy" },
    };

    (api.fetchTasks as any).mockResolvedValue(mockTasks);
    (api.fetchSystemHealth as any).mockResolvedValue(mockHealth);

    render(<MetricsPanel />);

    await waitFor(() => {
      expect(screen.getByText("degraded")).toBeTruthy();
      expect(screen.getByText("down")).toBeTruthy();
    });

    const degradedEl = screen.getByText("degraded");
    expect(degradedEl.className).toContain("text-yellow-500");

    const downEl = screen.getByText("down");
    expect(downEl.className).toContain("text-red-500");
    
    // Check unknown status style
    const unknownEl = screen.getAllByText("unknown")[0];
    expect(unknownEl.className).toContain("text-zinc-500");
  });

  it("handles empty or failed API responses gracefully", async () => {
    // Simulate empty/failed response (api.ts usually returns [] or mock obj on error, 
    // but here we test what happens if it returns empty/null as if the catch block returned default)
    
    (api.fetchTasks as any).mockResolvedValue([]);
    (api.fetchSystemHealth as any).mockResolvedValue({});

    render(<MetricsPanel />);

    await waitFor(() => {
      // Should show 0 tasks
      expect(screen.getByText("0")).toBeTruthy();
      expect(screen.getByText("/ 0 tasks")).toBeTruthy();
    });

    // Since health data is missing keys, it should default to "unknown" based on component logic:
    // healthData["redis"]?.status || "unknown"
    const unknownElements = screen.getAllByText("unknown");
    expect(unknownElements.length).toBeGreaterThanOrEqual(4); // All 4 services
  });

  it("renders the Compliance section correctly", async () => {
    // This section is static but important to verify
    (api.fetchTasks as any).mockResolvedValue([]);
    (api.fetchSystemHealth as any).mockResolvedValue({});
    
    render(<MetricsPanel />);

    // Wait for effect to settle to avoid "act" warning
    await waitFor(() => {
      expect(screen.getByText("AGPL-3.0 License Enforced")).toBeTruthy();
    });
    
    expect(screen.getByText("WCAG 2.2 AAA Accessibility")).toBeTruthy();
    expect(screen.getByText("Local-First Data Sovereignty")).toBeTruthy();
  });
});
