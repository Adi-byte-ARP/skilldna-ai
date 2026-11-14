import { useRef } from "react";
import { useGsap } from "../lib/motion";

/*
 * Slow, soft colour fields that drift behind the content. Each field has its own
 * loop length and path, so the motion never visibly repeats. Positioned inside a
 * relative parent and clipped to it. Reduced motion: static fields.
 */

const FIELDS = [
  { color: "var(--color-helix-teal)", size: 46, x: "8%", y: "12%", dx: 140, dy: 90, duration: 17 },
  { color: "var(--color-helix-violet)", size: 40, x: "70%", y: "22%", dx: -120, dy: 110, duration: 21 },
  { color: "var(--color-signal-coral)", size: 30, x: "45%", y: "70%", dx: 90, dy: -80, duration: 25 },
];

export default function AmbientBackground({ className = "" }) {
  const scope = useRef(null);

  useGsap(scope, ({ reduce, gsap }) => {
    if (reduce) return undefined;
    const blobs = gsap.utils.toArray("[data-aurora]", scope.current);
    blobs.forEach((blob, i) => {
      const f = FIELDS[i];
      // Centre with GSAP's percent properties. A CSS transform would be overwritten by the tween.
      gsap.set(blob, { xPercent: -50, yPercent: -50 });
      gsap.fromTo(
        blob,
        { x: 0, y: 0, scale: 1 },
        {
          x: f.dx,
          y: f.dy,
          scale: 1.18,
          duration: f.duration,
          repeat: -1,
          yoyo: true,
          ease: "sine.inOut",
        }
      );
    });
    return undefined;
  });

  return (
    <div ref={scope} aria-hidden="true" className={`pointer-events-none absolute inset-0 overflow-hidden ${className}`}>
      {FIELDS.map((f, i) => (
        <div
          key={i}
          data-aurora
          className="absolute rounded-full opacity-[0.22] blur-[90px] will-change-transform"
          style={{
            width: `${f.size}vmax`,
            height: `${f.size}vmax`,
            left: f.x,
            top: f.y,
            background: f.color,
          }}
        />
      ))}
    </div>
  );
}
