import { describe, it, expect } from "vitest";
import { isSpeechPattern, WINDOW_SIZE, MIN_LEVEL } from "../lib/useSpeechMonitor";
import { isMobileDevice } from "../lib/device";

describe("speech detection", () => {
  it("ignores silence and a steady tone", () => {
    const silence = Array(WINDOW_SIZE).fill(0.001);
    const steadyTone = Array(WINDOW_SIZE).fill(0.2);
    expect(isSpeechPattern(silence)).toBe(false);
    expect(isSpeechPattern(steadyTone)).toBe(false);
  });

  it("recognises talking, whose level rises and falls from syllable to syllable", () => {
    const talking = Array.from({ length: WINDOW_SIZE }, (_, i) => (i % 3 === 0 ? 0.25 : 0.04));
    expect(isSpeechPattern(talking)).toBe(true);
  });

  it("needs a full window before deciding", () => {
    expect(isSpeechPattern([0.3, 0.02, 0.3])).toBe(false);
    expect(MIN_LEVEL).toBeGreaterThan(0);
  });
});

describe("device check", () => {
  const desktop = { userAgent: "Mozilla/5.0 (X11; Linux x86_64) Chrome/125" };
  const android = { userAgent: "Mozilla/5.0 (Linux; Android 14; Pixel 8) Mobile Safari" };
  const iphone = { userAgent: "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X)" };
  const noTouchPointer = () => ({ matchMedia: () => ({ matches: false }) });
  const touchOnly = () => ({ matchMedia: (q) => ({ matches: q.includes("coarse") }) });

  it("refuses phones and tablets by their browser", () => {
    expect(isMobileDevice(android, noTouchPointer())).toBe(true);
    expect(isMobileDevice(iphone, noTouchPointer())).toBe(true);
  });

  it("allows a laptop or desktop", () => {
    expect(isMobileDevice(desktop, noTouchPointer())).toBe(false);
  });

  it("refuses a device whose only pointer is a touch screen, even with a desktop browser", () => {
    expect(isMobileDevice(desktop, touchOnly())).toBe(true);
  });
});
