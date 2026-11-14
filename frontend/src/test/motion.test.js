import { describe, it, expect } from "vitest";
import { helixPoints, helixRungs, splitWords, prefersReducedMotion } from "../lib/motion";

describe("helix geometry", () => {
  const points = helixPoints({ width: 400, height: 1000, radius: 90, turns: 2, points: 50 });

  it("produces one point per requested sample, from top to bottom", () => {
    expect(points).toHaveLength(50);
    expect(points[0].y).toBe(0);
    expect(points[49].y).toBe(1000);
  });

  it("keeps both strands inside the canvas width", () => {
    for (const p of points) {
      expect(p.a).toBeGreaterThanOrEqual(200 - 90 - 1e-9);
      expect(p.a).toBeLessThanOrEqual(200 + 90 + 1e-9);
      expect(p.b).toBeGreaterThanOrEqual(200 - 90 - 1e-9);
      expect(p.b).toBeLessThanOrEqual(200 + 90 + 1e-9);
    }
  });

  it("puts the two strands on opposite sides of the axis", () => {
    for (const p of points) {
      expect(p.a + p.b).toBeCloseTo(400, 6);
    }
  });

  it("changes shape when the phase changes, which is what makes it rotate", () => {
    const later = helixPoints({ width: 400, height: 1000, radius: 90, turns: 2, points: 50, phase: 1 });
    expect(later[10].a).not.toBeCloseTo(points[10].a, 3);
  });

  it("spaces rungs evenly", () => {
    expect(helixRungs(points, 10)).toEqual([0, 10, 20, 30, 40]);
  });
});

describe("splitWords", () => {
  it("splits on any whitespace and drops empty pieces", () => {
    expect(splitWords("  one two\n three\t  ")).toEqual(["one", "two", "three"]);
  });

  it("handles empty input", () => {
    expect(splitWords("")).toEqual([]);
    expect(splitWords(undefined)).toEqual([]);
  });
});

describe("prefersReducedMotion", () => {
  it("is false when the system has no preference", () => {
    expect(prefersReducedMotion()).toBe(false);
  });

  it("is true when the system asks for less motion", () => {
    const original = window.matchMedia;
    window.matchMedia = (query) => ({ matches: query.includes("reduce"), addEventListener() {}, removeEventListener() {} });
    try {
      expect(prefersReducedMotion()).toBe(true);
    } finally {
      window.matchMedia = original;
    }
  });
});
