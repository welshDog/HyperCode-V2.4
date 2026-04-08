import { render, screen, waitFor } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { BroskiWalletWidget } from "../components/BroskiWalletWidget";
import * as api from "@/lib/api";

vi.mock("@/lib/api", () => ({
  fetchBroskiWallet: vi.fn(),
}));

describe("BroskiWalletWidget", () => {
  beforeEach(() => {
    vi.resetAllMocks();
  });

  it("renders a loading skeleton initially", async () => {
    (api.fetchBroskiWallet as any).mockReturnValue(new Promise(() => {}));
    render(<BroskiWalletWidget />);
    expect(screen.getByText("BROski$ Wallet")).toBeTruthy();
  });

  it("renders wallet data (coins, level badge, XP progress)", async () => {
    (api.fetchBroskiWallet as any).mockResolvedValue({
      id: 1,
      user_id: 1,
      coins: 123,
      xp: 250,
      level: 3,
      level_name: "BROski Agent",
      created_at: new Date().toISOString(),
      updated_at: null,
    });

    render(<BroskiWalletWidget />);

    await waitFor(() => {
      expect(screen.getByTestId("coins-value").textContent).toBe("123");
    });

    expect(screen.getByTestId("level-badge").textContent).toContain("LVL 3");
    expect(screen.getByTestId("xp-label").textContent).toContain("250 / 500");
    expect(screen.getByTestId("xp-percent").textContent).toBe("0%");
    expect(screen.getByTestId("xp-progress-bar")).toBeTruthy();
  });

  it("renders error UI when fetch fails and allows retry", async () => {
    (api.fetchBroskiWallet as any).mockRejectedValueOnce(new Error("boom"));
    (api.fetchBroskiWallet as any).mockResolvedValueOnce({
      id: 1,
      user_id: 1,
      coins: 10,
      xp: 10,
      level: 1,
      level_name: "BROski Recruit",
      created_at: new Date().toISOString(),
      updated_at: null,
    });

    render(<BroskiWalletWidget />);

    await waitFor(() => {
      expect(screen.getByText("boom")).toBeTruthy();
    });

    screen.getByRole("button", { name: "Retry" }).click();

    await waitFor(() => {
      expect(screen.getByTestId("coins-value").textContent).toBe("10");
    });
  });
});
