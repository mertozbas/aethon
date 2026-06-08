import { describe, it, expect } from "vitest";
import { interpolateTranslation } from "./context";

describe("interpolateTranslation", () => {
  it("replaces template variables", () => {
    expect(interpolateTranslation("共 {count} 条", { count: 2 })).toBe("共 2 条");
  });

  it("keeps unknown variables unchanged", () => {
    expect(interpolateTranslation("{count} / {total}", { count: 2 })).toBe("2 / {total}");
  });
});
