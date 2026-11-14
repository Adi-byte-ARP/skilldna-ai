import { useRef } from "react";
import { useGsap, helixPoints, helixRungs } from "../lib/motion";

/*
 * A large, faint double helix fixed to the right edge of the page.
 *   - It rotates continuously (GSAP ticker), so it reads as a 3D helix, not a flat wave.
 *   - It drifts upward as the page scrolls (ScrollTrigger scrub), so it feels anchored to the content.
 *   - Reduced motion: one still frame, no rotation, no scroll drift.
 * Decorative only: aria-hidden and pointer-events: none.
 */

const W = 400;
const H = 1400;
const RADIUS = 92;
const TURNS = 2.4;
const POINTS = 110;
const RUNG_EVERY = 9;
const SPIN_RAD_PER_SECOND = 0.35;

function pathFrom(points, key) {
  return points
    .map((p, i) => `${i === 0 ? "M" : "L"}${p[key].toFixed(1)} ${p.y.toFixed(1)}`)
    .join(" ");
}

export default function HelixBackdrop({ className = "" }) {
  const scope = useRef(null);
  const strandA = useRef(null);
  const strandB = useRef(null);
  const rungRefs = useRef([]);

  function draw(phase) {
    const points = helixPoints({ width: W, height: H, radius: RADIUS, turns: TURNS, points: POINTS, phase });
    strandA.current?.setAttribute("d", pathFrom(points, "a"));
    strandB.current?.setAttribute("d", pathFrom(points, "b"));
    helixRungs(points, RUNG_EVERY).forEach((index, k) => {
      const line = rungRefs.current[k];
      if (!line) return;
      const p = points[index];
      line.setAttribute("x1", p.a.toFixed(1));
      line.setAttribute("x2", p.b.toFixed(1));
      line.setAttribute("y1", p.y.toFixed(1));
      line.setAttribute("y2", p.y.toFixed(1));
      line.setAttribute("opacity", (0.25 + 0.55 * Math.abs(p.depthA)).toFixed(2));
    });
  }

  useGsap(scope, ({ reduce, gsap }) => {
    if (reduce) {
      draw(0.6);
      return undefined;
    }
    const tick = () => draw(gsap.ticker.time * SPIN_RAD_PER_SECOND);
    gsap.ticker.add(tick);

    gsap.fromTo(
      scope.current,
      { y: 0 },
      {
        y: () => -window.innerHeight * 0.55,
        ease: "none",
        scrollTrigger: { trigger: document.body, start: "top top", end: "bottom bottom", scrub: 0.8 },
      }
    );

    return () => gsap.ticker.remove(tick);
  });

  const rungCount = helixRungs(helixPoints({ width: W, height: H, radius: RADIUS, turns: TURNS, points: POINTS }), RUNG_EVERY).length;

  return (
    <div
      ref={scope}
      aria-hidden="true"
      className={`pointer-events-none fixed top-0 right-[-6vw] h-screen w-[min(560px,70vw)] opacity-[0.22] will-change-transform ${className}`}
    >
      <svg viewBox={`0 0 ${W} ${H}`} preserveAspectRatio="xMidYMid meet" className="w-full h-full">
        {Array.from({ length: rungCount }, (_, k) => (
          <line
            key={k}
            ref={(el) => (rungRefs.current[k] = el)}
            stroke="var(--color-helix-violet)"
            strokeWidth="1.4"
            strokeLinecap="round"
          />
        ))}
        <path ref={strandA} fill="none" stroke="var(--color-helix-teal)" strokeWidth="2.2" strokeLinecap="round" />
        <path ref={strandB} fill="none" stroke="var(--color-helix-violet)" strokeWidth="2.2" strokeLinecap="round" />
      </svg>
    </div>
  );
}
