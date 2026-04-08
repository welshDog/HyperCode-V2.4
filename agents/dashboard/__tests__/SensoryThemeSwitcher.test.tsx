import { render, screen, act } from "@testing-library/react";
import { describe, it, expect, beforeEach, vi } from "vitest";
import { SensoryThemeProvider } from "@/app/themes/SensoryThemeProvider";
import { SensoryThemeSwitcher } from "@/app/themes/SensoryThemeSwitcher";

describe("SensoryThemeSwitcher", () => {
  beforeEach(() => {
    localStorage.clear();
    document.documentElement.removeAttribute("data-hc-theme");
    Object.defineProperty(window, "matchMedia", {
      writable: true,
      value: vi.fn().mockImplementation((query: string) => ({
        matches: false,
        media: query,
        onchange: null,
        addListener: vi.fn(),
        removeListener: vi.fn(),
        addEventListener: vi.fn(),
        removeEventListener: vi.fn(),
        dispatchEvent: vi.fn(),
      })),
    });
  });

  it("renders theme buttons with aria-pressed", async () => {
    render(
      <SensoryThemeProvider>
        <SensoryThemeSwitcher />
      </SensoryThemeProvider>
    );

    expect(screen.getByRole("button", { name: /CALM/i })).toBeTruthy();
    expect(screen.getByRole("button", { name: /FOCUS/i })).toBeTruthy();
    expect(screen.getByRole("button", { name: /ENERGISE/i })).toBeTruthy();
  });

  it("updates document theme attribute and persists selection", async () => {
    render(
      <SensoryThemeProvider>
        <SensoryThemeSwitcher />
      </SensoryThemeProvider>
    );

    const calm = screen.getByRole("button", { name: /CALM/i });

    await act(async () => {
      calm.click();
    });

    expect(calm.getAttribute("aria-pressed")).toBe("true");
    expect(document.documentElement.getAttribute("data-hc-theme")).toBe("calm");
    expect(localStorage.getItem("hc-sensory-theme")).toBe("calm");
  });
});

