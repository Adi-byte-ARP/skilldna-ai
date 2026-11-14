import { useLayoutEffect, useRef } from "react";
import { gsap, prefersReducedMotion } from "../lib/motion";

/**
 * Fades and lifts its content in when it mounts. Give it a `key` that changes to play
 * the animation again (for example, one key per screen). Reduced motion: no animation.
 */
export default function Appear({ className = "", y = 12, duration = 0.5, children }) {
  const ref = useRef(null);
  const startY = y;
  const startDuration = duration;
  useLayoutEffect(() => {
    const el = ref.current;
    if (!el || prefersReducedMotion()) return undefined;
    // fromTo with explicit values: the tween always ends at fully visible.
    const tween = gsap.fromTo(
      el,
      { opacity: 0, y: startY },
      { opacity: 1, y: 0, duration: startDuration, ease: "power3.out" }
    );
    // If the effect is torn down early (React's development double-mount does this), a killed
    // tween would otherwise leave the content hidden at opacity 0. Clearing the inline styles
    // makes the content visible in every case.
    return () => {
      tween.kill();
      gsap.set(el, { clearProps: "opacity,transform" });
    };
    // Runs once on mount by design: the animation starts from the state at mount time.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);
  return (
    <div ref={ref} className={className}>
      {children}
    </div>
  );
}
