import { describe, it, expect } from "vitest";
import { computeCognitiveLoad } from "@/lib/cognitiveLoad";

describe("computeCognitiveLoad", () => {
  it("returns low when system is calm", () => {
    const res = computeCognitiveLoad({
      connected: true,
      pendingTasks: 0,
      errorAgents: 0,
      totalAgents: 5,
      recentErrorLogs: 0,
    });
    expect(res.band).toBe("low");
    expect(res.score).toBe(0);
  });

  it("returns overload when errors and backlog stack up", () => {
    const res = computeCognitiveLoad({
      connected: false,
      pendingTasks: 12,
      errorAgents: 2,
      totalAgents: 5,
      recentErrorLogs: 10,
    });
    expect(res.score).toBeGreaterThanOrEqual(80);
    expect(res.band).toBe("overload");
  });
});

