import { normalizeGoal } from "./index";

describe("normalizeGoal", () => {
  it("trims whitespace", () => {
    expect(normalizeGoal("  hello  ")).toBe("hello");
  });
});

