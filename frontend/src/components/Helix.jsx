import { useMemo, useRef, useEffect } from "react";
import { gsap } from "../lib/gsapSetup";

/**
 * The signature visual for SkillDNA AI.
 *
 * Two intertwined strands: the LEFT strand is what a person *claims*
 * (resume, LinkedIn), the RIGHT strand is *verified evidence* (GitHub,
 * certificates). Where a rung lights up teal, a skill has been confirmed
 * by more than one source — that's the literal mechanic of the scoring
 * engine's noisy-OR combination, not decoration.
 *
 * When `spin` is true, the helix genuinely rotates — the phase offset is
 * driven every frame by GSAP's ticker and written straight to the SVG
 * attributes via refs (bypassing React re-render), so it stays smooth
 * even with 10+ nodes animating at once.
 *
 * variant="hero": decorative, generic labels.
 * variant="report": driven by real skill data from the backend.
 */
export default function Helix({
  variant = "hero",
  skills = [],
  height = 460,
  width = 320,
  spin = false,
  speed = 0.6,
}) {
  const rungCount = variant === "report" ? Math.max(skills.length, 1) : 9;
  const amplitude = width * 0.26;
  const centerX = width / 2;
  const turns = 2.4;

  const leftPathRef = useRef(null);
  const rightPathRef = useRef(null);
  const leftNodeRefs = useRef([]);
  const rightNodeRefs = useRef([]);
  const rungRefs = useRef([]);
  const phaseRef = useRef(0);

  const computeStrand = (phaseOffset, globalPhase) => {
    const samples = 80;
    const pts = [];
    for (let i = 0; i <= samples; i++) {
      const t = i / samples;
      const y = t * height;
      const x = centerX + amplitude * Math.sin(t * turns * 2 * Math.PI + phaseOffset + globalPhase);
      pts.push(`${x.toFixed(1)},${y.toFixed(1)}`);
    }
    return "M " + pts.join(" L ");
  };

  const rungGeometry = useMemo(() => {
    const arr = [];
    for (let i = 0; i < rungCount; i++) {
      const t = (i + 0.5) / rungCount;
      const skill = variant === "report" ? skills[i] : null;
      const verified = skill ? (skill.sources?.length || 0) >= 2 : i % 3 === 0;
      const weak = skill ? skill.score < 55 : false;
      arr.push({ t, verified, weak, idx: i });
    }
    return arr;
  }, [rungCount, skills, variant]);

  const initialLeftPath = useMemo(() => computeStrand(0, 0), [width, height, rungCount]);
  const initialRightPath = useMemo(() => computeStrand(Math.PI, 0), [width, height, rungCount]);

  useEffect(() => {
    if (!spin) return;

    const tick = () => {
      phaseRef.current += 0.012 * speed;
      const gp = phaseRef.current;

      if (leftPathRef.current) leftPathRef.current.setAttribute("d", computeStrand(0, gp));
      if (rightPathRef.current) rightPathRef.current.setAttribute("d", computeStrand(Math.PI, gp));

      rungGeometry.forEach((r, i) => {
        const phase = r.t * turns * 2 * Math.PI + gp;
        const xLeft = centerX + amplitude * Math.sin(phase);
        const xRight = centerX + amplitude * Math.sin(phase + Math.PI);
        const y = r.t * height;

        const rung = rungRefs.current[i];
        if (rung) {
          rung.setAttribute("x1", xLeft);
          rung.setAttribute("x2", xRight);
          rung.setAttribute("y1", y);
          rung.setAttribute("y2", y);
        }
        const ln = leftNodeRefs.current[i];
        if (ln) {
          ln.setAttribute("cx", xLeft);
          ln.setAttribute("cy", y);
        }
        const rn = rightNodeRefs.current[i];
        if (rn) {
          rn.setAttribute("cx", xRight);
          rn.setAttribute("cy", y);
        }
      });
    };

    gsap.ticker.add(tick);
    return () => gsap.ticker.remove(tick);
  }, [spin, speed, rungGeometry, width, height]);

  const staticRungs = useMemo(() => {
    return rungGeometry.map((r) => {
      const phase = r.t * turns * 2 * Math.PI;
      const y = r.t * height;
      return {
        ...r,
        y,
        xLeft: centerX + amplitude * Math.sin(phase),
        xRight: centerX + amplitude * Math.sin(phase + Math.PI),
      };
    });
  }, [rungGeometry, height, width]);

  return (
    <svg
      viewBox={`0 0 ${width} ${height}`}
      width="100%"
      height={height}
      role="img"
      aria-label={
        variant === "hero"
          ? "Animated illustration of a double helix representing claimed skills and verified evidence strands"
          : "Skill evidence helix showing which skills are verified by multiple sources"
      }
    >
      <defs>
        <linearGradient id="leftGrad" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor="var(--color-helix-violet)" stopOpacity="0.9" />
          <stop offset="100%" stopColor="var(--color-helix-violet)" stopOpacity="0.35" />
        </linearGradient>
        <linearGradient id="rightGrad" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor="var(--color-helix-teal)" stopOpacity="0.9" />
          <stop offset="100%" stopColor="var(--color-helix-teal)" stopOpacity="0.35" />
        </linearGradient>
      </defs>

      {staticRungs.map((r, i) => (
        <line
          key={`rung-${r.idx}`}
          ref={(el) => (rungRefs.current[i] = el)}
          x1={r.xLeft}
          y1={r.y}
          x2={r.xRight}
          y2={r.y}
          stroke={r.verified ? "var(--color-helix-teal)" : r.weak ? "var(--color-signal-coral)" : "var(--color-line)"}
          strokeWidth={r.verified ? 2.5 : 1.5}
          strokeLinecap="round"
          style={{
            animation: r.verified ? `rungSpark 2.4s ease-in-out ${r.idx * 0.15}s infinite` : "none",
            opacity: r.verified ? 1 : 0.6,
          }}
        />
      ))}

      <path
        ref={leftPathRef}
        d={initialLeftPath}
        fill="none"
        stroke="url(#leftGrad)"
        strokeWidth="3"
        strokeLinecap="round"
      />
      <path
        ref={rightPathRef}
        d={initialRightPath}
        fill="none"
        stroke="url(#rightGrad)"
        strokeWidth="3"
        strokeLinecap="round"
      />

      {staticRungs.map((r, i) => (
        <g key={`nodes-${r.idx}`}>
          <circle
            ref={(el) => (leftNodeRefs.current[i] = el)}
            cx={r.xLeft}
            cy={r.y}
            r={5}
            fill="var(--color-helix-violet)"
            style={{ animation: `nodePulse 3.2s ease-in-out ${r.idx * 0.22}s infinite` }}
          />
          <circle
            ref={(el) => (rightNodeRefs.current[i] = el)}
            cx={r.xRight}
            cy={r.y}
            r={5}
            fill="var(--color-helix-teal)"
            style={{ animation: `nodePulse 3.2s ease-in-out ${r.idx * 0.22 + 0.4}s infinite` }}
          />
        </g>
      ))}
    </svg>
  );
}
