import { useMemo, useRef } from "react";
import { useGsap } from "../lib/motion";

/**
 * Ambient background: a sparse network of "evidence nodes" joined by thin lines.
 * Nodes pulse in a random stagger, the lines carry a slow dash flow, and the whole
 * field drifts a little as the page scrolls. All of it is GSAP.
 *
 * Deterministic (seeded): the layout is the same on every render and reload.
 */

// Tiny seeded PRNG (mulberry32) so the layout is stable.
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
      });
    }
  }

  // Sparse links to right and down neighbours, so it reads as a network, not a grid.
  const lines = [];
  for (let r = 0; r < rows; r++) {
    for (let c = 0; c < cols; c++) {
      const idx = r * cols + c;
      if (rand() <= 0.55) continue;
      if (c < cols - 1) lines.push([nodes[idx], nodes[idx + 1]]);
      if (r < rows - 1 && rand() > 0.5) lines.push([nodes[idx], nodes[idx + cols]]);
    }
  }
  return { nodes, lines };
}

export default function SequenceBackground({ seed = 7, cols = 11, rows = 6, className = "" }) {
  const scope = useRef(null);
  const { nodes, lines } = useMemo(() => generateField({ cols, rows, seed }), [cols, rows, seed]);

  useGsap(scope, ({ reduce, gsap }) => {
    if (reduce) return undefined;
    const dots = gsap.utils.toArray("[data-node]", scope.current);
    const links = gsap.utils.toArray("[data-link]", scope.current);

    // Nodes breathe in a random order, like signal arriving at different points.
    gsap.to(dots, {
      scale: 1.5,
      transformOrigin: "50% 50%",
      duration: 2.8,
      repeat: -1,
      yoyo: true,
      ease: "sine.inOut",
      stagger: { each: 0.14, from: "random", repeat: -1 },
    });

    // The dash pattern is 1.2 on, 1.6 off (period 2.8), so offsetting by one period loops seamlessly.
    gsap.to(links, { strokeDashoffset: -2.8, duration: 5, repeat: -1, ease: "none" });

    // The field drifts slower than the page, which adds depth.
    gsap.to(scope.current, {
      y: () => -window.innerHeight * 0.12,
      ease: "none",
      scrollTrigger: { trigger: scope.current.parentElement, start: "top bottom", end: "bottom top", scrub: 0.6 },
    });
    return undefined;
  });

  return (
    <div ref={scope} aria-hidden="true" className={`pointer-events-none absolute inset-0 overflow-hidden ${className}`}>
      <svg viewBox="0 0 100 100" preserveAspectRatio="none" className="w-full h-full">
        {lines.map(([a, b], i) => (
          <line
            key={i}
            data-link
            x1={a.x}
            y1={a.y}
            x2={b.x}
            y2={b.y}
            stroke="var(--color-ink)"
            strokeOpacity={0.05}
            strokeWidth="0.12"
            strokeDasharray="1.2 1.6"
          />
        ))}
        {nodes.map((n) => (
          <circle
            key={n.id}
            data-node
            cx={n.x}
            cy={n.y}
            r={n.verified ? 0.42 : 0.28}
            fill={n.verified ? "var(--color-helix-teal)" : "var(--color-helix-violet)"}
            fillOpacity={n.verified ? 0.35 : 0.2}
          />
        ))}
      </svg>
    </div>
  );
}
