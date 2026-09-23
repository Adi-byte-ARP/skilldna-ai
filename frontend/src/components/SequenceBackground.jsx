import { useMemo, useRef, useLayoutEffect } from "react";
import { gsap } from "../lib/gsapSetup";

/**
 * Ambient background: a sparse network of "evidence nodes" connected by thin
 * lines, pulsing and slowly drifting. Deliberately extends the same visual
 * language already used in Helix.jsx (nodePulse/rungSpark keyframes) rather
 * than introducing a new style -- this should read as part of the same
 * design system, not a bolted-on decoration.
 *
 * Deterministic (seeded), not Math.random() on every render, so the layout
 * doesn't jitter between renders/reloads. Pure CSS keyframe animation for
 * the pulse/drift, so it's covered for free by the app's existing
 * `prefers-reduced-motion` rule in index.css -- only the initial GSAP
 * fade-in needs its own explicit check.
 */

// Tiny seeded PRNG (mulberry32) so the "organic" jitter is stable across renders.
function seededRandom(seed) {
  return function () {
    seed |= 0;
    seed = (seed + 0x6d2b79f5) | 0;
    let t = Math.imul(seed ^ (seed >>> 15), 1 | seed);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

function generateField({ cols, rows, seed, jitter = 0.38 }) {
  const rand = seededRandom(seed);
  const nodes = [];
  for (let r = 0; r < rows; r++) {
    for (let c = 0; c < cols; c++) {
      const baseX = ((c + 0.5) / cols) * 100;
      const baseY = ((r + 0.5) / rows) * 100;
      nodes.push({
        id: `${r}-${c}`,
        x: baseX + (rand() - 0.5) * jitter * (100 / cols),
        y: baseY + (rand() - 0.5) * jitter * (100 / rows),
        verified: rand() > 0.62,
        delay: rand() * 3,
      });
    }
  }

  // Connect each node to its grid-neighbor to the right and below, but only
  // keep a subset so the network reads as sparse/organic, not a rigid mesh.
  const lines = [];
  for (let r = 0; r < rows; r++) {
    for (let c = 0; c < cols; c++) {
      const idx = r * cols + c;
      const keep = rand() > 0.55;
      if (!keep) continue;
      if (c < cols - 1) lines.push([nodes[idx], nodes[idx + 1]]);
      if (r < rows - 1 && rand() > 0.5) lines.push([nodes[idx], nodes[idx + cols]]);
    }
  }

  return { nodes, lines };
}

export default function SequenceBackground({ seed = 7, cols = 11, rows = 6, className = "" }) {
  const rootRef = useRef(null);
  const { nodes, lines } = useMemo(() => generateField({ cols, rows, seed }), [cols, rows, seed]);

  useLayoutEffect(() => {
    const prefersReduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    if (prefersReduced) {
      gsap.set(rootRef.current, { opacity: 1 });
      return;
    }
    const ctx = gsap.context(() => {
      gsap.from(rootRef.current, { opacity: 0, duration: 1.6, ease: "power2.out" });
    }, rootRef);
    return () => ctx.revert();
  }, []);

  return (
    <div
      ref={rootRef}
      aria-hidden="true"
      className={`pointer-events-none absolute inset-0 overflow-hidden ${className}`}
    >
      <svg
        viewBox="0 0 100 100"
        preserveAspectRatio="none"
        className="w-full h-full"
      >
        {lines.map(([a, b], i) => (
          <line
            key={i}
            x1={a.x}
            y1={a.y}
            x2={b.x}
            y2={b.y}
            stroke="var(--color-ink)"
            strokeOpacity={0.05}
            strokeWidth="0.12"
            strokeDasharray="1.2 1.6"
            style={{
              animation: `flowDash ${14 + (i % 5) * 2}s linear infinite`,
            }}
          />
        ))}
        {nodes.map((n) => (
          <circle
            key={n.id}
            cx={n.x}
            cy={n.y}
            r={n.verified ? 0.42 : 0.28}
            fill={n.verified ? "var(--color-helix-teal)" : "var(--color-helix-violet)"}
            fillOpacity={n.verified ? 0.35 : 0.2}
            style={{
              animation: `nodePulse ${3 + (n.delay % 2)}s ease-in-out ${n.delay}s infinite`,
              transformOrigin: `${n.x}px ${n.y}px`,
              transformBox: "fill-box",
            }}
          />
        ))}
      </svg>
    </div>
  );
}
