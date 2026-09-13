// @vitest-environment node
import { describe, it, expect, vi, beforeEach } from "vitest";
import { POST } from "../app/api/skills/route";

function makeRequest(body: unknown): Request {
  return new Request("http://localhost/api/skills", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
}

describe("POST /api/skills", () => {
  beforeEach(() => {
    vi.unstubAllGlobals();
  });

  it("passes through a successful backend response", async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({
        matches: [{ name: "cve-trivy-scan", rationale: "Scans for CVEs." }],
        usedFallback: false,
        error: null,
      }),
    });
    vi.stubGlobal("fetch", fetchMock as any);

    const res = await POST(makeRequest({ goal: "check for CVEs" }));
    const body = await res.json();

    expect(res.status).toBe(200);
    expect(body.usedFallback).toBe(false);
    expect(body.matches).toEqual([{ name: "cve-trivy-scan", rationale: "Scans for CVEs." }]);
  });

  it("returns a fail-soft 200 when the backend is unreachable", async () => {
    const fetchMock = vi.fn().mockRejectedValue(new Error("fetch failed: ECONNREFUSED"));
    vi.stubGlobal("fetch", fetchMock as any);

    const res = await POST(makeRequest({ goal: "deploy a discord bot" }));
    const body = await res.json();

    expect(res.status).toBe(200);
    expect(body.usedFallback).toBe(true);
    expect(body.matches).toEqual([]);
    expect(body.error).toMatch(/not reachable/i);
  });

  it("returns a fail-soft 200 with a timeout-specific message on abort", async () => {
    const abortError = new Error("The operation was aborted");
    abortError.name = "TimeoutError";
    const fetchMock = vi.fn().mockRejectedValue(abortError);
    vi.stubGlobal("fetch", fetchMock as any);

    const res = await POST(makeRequest({ goal: "deploy a discord bot" }));
    const body = await res.json();

    expect(res.status).toBe(200);
    expect(body.usedFallback).toBe(true);
    expect(body.error).toMatch(/15s/);
  });

  it("returns a fail-soft 200 without calling fetch when goal is missing", async () => {
    const fetchMock = vi.fn();
    vi.stubGlobal("fetch", fetchMock as any);

    const res = await POST(makeRequest({}));
    const body = await res.json();

    expect(res.status).toBe(200);
    expect(body.usedFallback).toBe(true);
    expect(body.error).toBe("goal is required");
    expect(fetchMock).not.toHaveBeenCalled();
  });
});
