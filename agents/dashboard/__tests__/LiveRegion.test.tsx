import { render, screen } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import { LiveRegion } from "@/components/a11y/LiveRegion";

describe("LiveRegion", () => {
  it("renders polite announcements as role=status", () => {
    render(<LiveRegion message="API connected" politeness="polite" atomic relevant="additions text" />);
    const el = screen.getByRole("status");
    expect(el.getAttribute("aria-live")).toBe("polite");
    expect(el.getAttribute("aria-atomic")).toBe("true");
    expect(el.getAttribute("aria-relevant")).toBe("additions text");
  });

  it("renders assertive announcements as role=alert", () => {
    render(<LiveRegion message="Agent error" politeness="assertive" atomic relevant="additions text" />);
    const el = screen.getByRole("alert");
    expect(el.getAttribute("aria-live")).toBe("assertive");
  });
});

