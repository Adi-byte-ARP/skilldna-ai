import { useLayoutEffect } from "react";
import { gsap, ScrollTrigger } from "./gsapSetup";

export { gsap, ScrollTrigger };

/** True when the user asked the system for less motion. */
export function prefersReducedMotion() {
  return typeof window !== "undefined" && !!window.matchMedia?.("(prefers-reduced-motion: reduce)").matches;
}

/**
 * Run GSAP setup inside a scoped context and undo it all on unmount or when `deps` change.
 *
 * setup({ reduce, gsap, ScrollTrigger }) may return a cleanup function for anything
 * that is not a GSAP tween (for example a ticker callback or a matchMedia handle).
 * With reduced motion on, setup still runs, so it can show final states, but it
 * should not start continuous or scroll-driven motion.
 */
export function useGsap(scopeRef, setup, deps = []) {
  useLayoutEffect(() => {
    const scope = scopeRef.current;
    if (!scope) return undefined;
    let cleanup;
    const ctx = gsap.context(() => {
      cleanup = setup({ reduce: prefersReducedMotion(), gsap, ScrollTrigger });
    }, scope);
    return () => {
      if (typeof cleanup === "function") cleanup();
      ctx.revert();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps);
}

/** Split text into words, keeping spaces out of the result. */
export function splitWords(text) {
  return (text || "").split(/\s+/).filter(Boolean);
}

/**
 * Geometry for a double helix drawn as two sine strands with rungs between them.
 * Pure and deterministic, so it can be tested without a browser.
 *
 * Each point has a height `y`, an angle `theta` and the two strand x positions.
 * Rungs are placed every `rungEvery` points. `phase` rotates the helix around its axis.
 */
export function helixPoints({ width, height, radius, turns, points, phase = 0 }) {
  const cx = width / 2;
  const out = [];
  for (let i = 0; i < points; i++) {
    const t = i / (points - 1);
    const y = t * height;
    const theta = t * turns * Math.PI * 2 + phase;
    out.push({
      y,
      theta,
      a: cx + radius * Math.cos(theta),
      b: cx + radius * Math.cos(theta + Math.PI),
      depthA: Math.sin(theta),
    });
  }
  return out;
}

export function helixRungs(points, every) {
  const rungs = [];
  for (let i = 0; i < points.length; i += every) rungs.push(i);
  return rungs;
}
