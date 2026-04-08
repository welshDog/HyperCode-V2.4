import { describe, it, expect } from "vitest";
import { diffAgentStatusAnnouncements, type AgentSnapshot } from "@/lib/a11y";

describe("diffAgentStatusAnnouncements", () => {
  it("emits assertive message when an agent enters error", () => {
    const prev = new Map<string | number, AgentSnapshot>([
      [1, { id: 1, name: "Coder", status: "online" }],
    ]);
    const next: AgentSnapshot[] = [{ id: 1, name: "Coder", status: "error" }];
    const res = diffAgentStatusAnnouncements(prev, next);
    expect(res.assertive[0]).toMatch(/Coder status error/);
  });

  it("emits polite message when an agent recovers from error", () => {
    const prev = new Map<string | number, AgentSnapshot>([
      [1, { id: 1, name: "Coder", status: "error" }],
    ]);
    const next: AgentSnapshot[] = [{ id: 1, name: "Coder", status: "online" }];
    const res = diffAgentStatusAnnouncements(prev, next);
    expect(res.polite[0]).toMatch(/Coder recovered/);
  });
});

