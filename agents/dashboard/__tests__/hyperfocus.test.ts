import { describe, it, expect } from "vitest";
import { initialHyperfocusState, tickHyperfocus } from "@/lib/hyperfocus";

describe("hyperfocus timer state machine", () => {
  it("does not tick when paused", () => {
    const s = initialHyperfocusState("micro");
    const res = tickHyperfocus(s);
    expect(res.type).toBe("tick");
    expect(res.state.secondsRemaining).toBe(s.secondsRemaining);
  });

  it("transitions from focus to break with announcement", () => {
    const s0 = { ...initialHyperfocusState("micro"), running: true, secondsRemaining: 1 };
    const res = tickHyperfocus(s0);
    expect(res.type).toBe("transition");
    if (res.type === "transition") {
      expect(res.nextPhase).toBe("break");
      expect(res.announcement).toMatch(/Focus complete/i);
      expect(res.state.secondsRemaining).toBeGreaterThan(0);
    }
  });

  it("completes after final break", () => {
    const s0 = { ...initialHyperfocusState("micro"), running: true, phase: "break" as const, cycle: 3, secondsRemaining: 1 };
    const res = tickHyperfocus(s0);
    expect(res.type).toBe("complete");
    if (res.type === "complete") {
      expect(res.state.running).toBe(false);
      expect(res.announcement).toMatch(/Session complete/i);
    }
  });
});

