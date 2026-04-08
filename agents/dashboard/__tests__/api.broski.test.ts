import { describe, it, expect, vi, beforeEach } from "vitest";
import { fetchBroskiWallet } from "../lib/api";

describe("fetchBroskiWallet (integration)", () => {
  beforeEach(() => {
    vi.unstubAllGlobals();
    localStorage.clear();
  });

  it("calls /api/v1/broski/wallet with Authorization header from localStorage", async () => {
    localStorage.setItem("token", "t123");

    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({
        id: 1,
        user_id: 1,
        coins: 1,
        xp: 1,
        level: 1,
        level_name: "BROski Recruit",
        created_at: new Date().toISOString(),
        updated_at: null,
      }),
    });
    vi.stubGlobal("fetch", fetchMock as any);

    await fetchBroskiWallet();

    const [url, init] = fetchMock.mock.calls[0];
    expect(String(url)).toContain("/api/v1/broski/wallet");
    expect((init.headers as Headers).get("Authorization")).toBe("Bearer t123");
  });

  it("throws when backend returns non-OK response", async () => {
    const fetchMock = vi.fn().mockResolvedValue({ ok: false, status: 401 });
    vi.stubGlobal("fetch", fetchMock as any);
    await expect(fetchBroskiWallet()).rejects.toThrow("Failed to fetch wallet");
  });
});

