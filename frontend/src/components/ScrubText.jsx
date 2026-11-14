import { useRef } from "react";
import { useGsap, splitWords } from "../lib/motion";

/**
 * A paragraph whose words light up one by one as the reader scrolls through it.
 * The words are rendered by React (not split in the DOM), so React keeps full control.
 * Reduced motion: every word is fully visible from the start.
 */
export default function ScrubText({ text, className = "" }) {
  const ref = useRef(null);
  const words = splitWords(text);

  useGsap(ref, ({ reduce, gsap }) => {
    if (reduce) return undefined;
    // Opacity rather than colour: it is cheap to animate and reads the same in every browser.
    // Words start faint and reach full strength, so the paragraph's own colour still applies.
    const items = gsap.utils.toArray("[data-word]", ref.current);
    gsap.fromTo(
      items,
      { opacity: 0.2 },
      {
        opacity: 1,
        stagger: 0.1,
        ease: "none",
        scrollTrigger: { trigger: ref.current, start: "top 85%", end: "bottom 50%", scrub: true },
      }
    );
    return undefined;
  }, [text]);

  return (
    <p ref={ref} className={className}>
      {words.map((w, i) => (
        <span key={`${i}-${w}`} data-word className="inline-block mr-[0.28em]">
          {w}
        </span>
      ))}
    </p>
  );
}
