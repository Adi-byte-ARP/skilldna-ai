import { useRef } from "react";
import { useGsap } from "../lib/motion";

/** A thin bar at the top of the viewport that fills as the page is scrolled. */
export default function ScrollProgress() {
  const bar = useRef(null);

  useGsap(bar, ({ reduce, gsap }) => {
    if (reduce) return undefined;
    gsap.fromTo(
      bar.current,
      { scaleX: 0 },
      {
        scaleX: 1,
        ease: "none",
        scrollTrigger: { trigger: document.documentElement, start: "top top", end: "bottom bottom", scrub: 0.2 },
      }
    );
    return undefined;
  });

  return (
    <div aria-hidden="true" className="pointer-events-none fixed inset-x-0 top-0 z-50 h-[2px]">
      <div ref={bar} data-scroll-progress className="h-full origin-left bg-helix-teal" style={{ transform: "scaleX(0)" }} />
    </div>
  );
}
