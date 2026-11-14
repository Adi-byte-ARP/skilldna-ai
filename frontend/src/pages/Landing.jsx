import { useRef } from "react";
import { Link } from "react-router-dom";
import { prefersReducedMotion, useGsap } from "../lib/motion";
import Helix from "../components/Helix";
import SequenceBackground from "../components/SequenceBackground";
import AmbientBackground from "../components/AmbientBackground";
import HelixBackdrop from "../components/HelixBackdrop";
import ScrollProgress from "../components/ScrollProgress";
import ScrubText from "../components/ScrubText";

const steps = [
  {
    n: "01",
    title: "Upload your resume",
    body: "Drop in a PDF. We read it and pull out every skill you claim — languages, frameworks, tools.",
  },
  {
    n: "02",
    title: "Connect GitHub",
    body: "We pull your public repos and see what you actually ship — primary language per repo, contribution volume.",
  },
  {
    n: "03",
    title: "Add LinkedIn & certificates",
    body: "Export your LinkedIn profile or screenshot it, and upload certificates — PDFs or images, one or several at once.",
  },
  {
    n: "04",
    title: "Get your SkillDNA score",
    body: "Every skill is cross-checked across sources. Claimed once scores modestly. Verified everywhere scores high.",
  },
];

export default function Landing() {
  const root = useRef(null);

  useGsap(root, ({ reduce, gsap }) => {
    // With reduced motion, nothing is hidden or moved: the page renders in its final state.
    if (reduce) return undefined;
    const cleanups = [];

    // Hero entrance: nav drops in, headline lines rise, helix scales in.
    const heroTl = gsap.timeline({ defaults: { ease: "power3.out" } });
    heroTl
      .from("[data-nav]", { y: -16, opacity: 0, duration: 0.5 })
      .from("[data-hero-line]", { y: 46, opacity: 0, duration: 0.9, stagger: 0.09 }, "-=0.2")
      .from("[data-hero-sub]", { y: 16, opacity: 0, duration: 0.6 }, "-=0.5")
      .from("[data-hero-cta]", { y: 12, opacity: 0, duration: 0.5, stagger: 0.08 }, "-=0.4")
      .from("[data-hero-helix]", { opacity: 0, scale: 0.85, duration: 1, ease: "power2.out" }, "-=0.9")
      .from("[data-hero-legend]", { opacity: 0, duration: 0.5 }, "-=0.3");

    // Gentle float on the hero helix, independent of scroll.
    gsap.to("[data-hero-helix]", { y: -14, duration: 3.2, ease: "sine.inOut", repeat: -1, yoyo: true });

    // Cursor glow inside the hero. Only on devices with a fine pointer (a mouse, not a finger).
    const hero = root.current.querySelector("[data-hero]");
    const glow = root.current.querySelector("[data-glow]");
    if (hero && glow && window.matchMedia("(pointer: fine)").matches) {
      gsap.set(glow, { xPercent: -50, yPercent: -50 });
      const qx = gsap.quickTo(glow, "x", { duration: 0.7, ease: "power3.out" });
      const qy = gsap.quickTo(glow, "y", { duration: 0.7, ease: "power3.out" });
      const move = (e) => {
        const r = hero.getBoundingClientRect();
        qx(e.clientX - r.left);
        qy(e.clientY - r.top);
      };
      hero.addEventListener("pointermove", move);
      cleanups.push(() => hero.removeEventListener("pointermove", move));
    }

    // Divider strip: items drift in from the left.
    gsap.from("[data-strip-item]", {
      scrollTrigger: { trigger: "[data-strip]", start: "top 90%" },
      x: -20,
      opacity: 0,
      stagger: 0.08,
      duration: 0.6,
      ease: "power2.out",
    });

    // Section heading reveal.
    gsap.from("[data-steps-eyebrow], [data-steps-heading]", {
      scrollTrigger: { trigger: "[data-steps-heading]", start: "top 85%" },
      y: 24,
      opacity: 0,
      duration: 0.7,
      stagger: 0.1,
      ease: "power3.out",
    });

    // How it works. Wide screens: the section pins and the steps light up in order
    // while the sequence line draws down, so scrolling drives the story.
    // Narrow screens: each step simply slides in as it enters view.
    const mm = gsap.matchMedia();
    mm.add("(min-width: 768px)", () => {
      const section = root.current.querySelector("[data-steps-section]");
      const cards = gsap.utils.toArray("[data-step-card]", root.current);
      const seqLine = root.current.querySelector("[data-sequence-line]");
      // No pin: the heading and steps stick (CSS) while this timeline is scrubbed over the
      // section's height. Pinning moved the layout under ScrollTrigger and left later triggers stale.
      const tl = gsap.timeline({
        scrollTrigger: { trigger: section, start: "top top", end: "bottom bottom", scrub: 0.6 },
      });
      if (seqLine) {
        const length = seqLine.getTotalLength();
        // start with the first 15% of the line already visible, so the section never looks empty
        gsap.set(seqLine, { strokeDasharray: length, strokeDashoffset: length * 0.85 });
        tl.to(seqLine, { strokeDashoffset: 0, ease: "none", duration: 1 }, 0);
      }
      cards.forEach((card, i) => {
        tl.fromTo(
          card,
          { opacity: 0.75, y: 28 },
          { opacity: 1, y: 0, duration: 0.6, ease: "power2.out" },
          i * 0.22
        );
      });
      return () => tl.kill();
    });
    mm.add("(max-width: 767px)", () => {
      gsap.utils.toArray("[data-step-card]", root.current).forEach((card, i) => {
        gsap.from(card, {
          scrollTrigger: { trigger: card, start: "top 88%" },
          x: i % 2 === 0 ? -40 : 40,
          opacity: 0,
          duration: 0.7,
          ease: "power3.out",
        });
      });
    });
    cleanups.push(() => mm.revert());

    // Scoring explainer: helix scale-in and count-up stats.
    gsap.from("[data-explainer-helix]", {
      scrollTrigger: { trigger: "[data-explainer-helix]", start: "top 85%" },
      opacity: 0,
      scale: 0.8,
      duration: 0.9,
      ease: "back.out(1.4)",
    });

    gsap.utils.toArray("[data-count]", root.current).forEach((el) => {
      const target = parseFloat(el.dataset.count);
      const obj = { val: 0 };
      gsap.to(obj, {
        val: target,
        duration: 1.4,
        ease: "power2.out",
        scrollTrigger: { trigger: el, start: "top 85%" },
        onUpdate: () => {
          el.textContent = Math.round(obj.val);
        },
      });
    });

    // Call to action.
    gsap.from("[data-cta] > *", {
      scrollTrigger: { trigger: "[data-cta]", start: "top 85%" },
      y: 28,
      opacity: 0,
      duration: 0.8,
      stagger: 0.1,
      ease: "power3.out",
    });

    // Magnetic-ish lift on primary buttons.
    gsap.utils.toArray("[data-magnetic]", root.current).forEach((btn) => {
      const onEnter = () => gsap.to(btn, { scale: 1.045, duration: 0.25, ease: "power2.out" });
      const onLeave = () => gsap.to(btn, { scale: 1, duration: 0.35, ease: "power2.out" });
      btn.addEventListener("mouseenter", onEnter);
      btn.addEventListener("mouseleave", onLeave);
      cleanups.push(() => {
        btn.removeEventListener("mouseenter", onEnter);
        btn.removeEventListener("mouseleave", onLeave);
      });
    });

    return () => cleanups.forEach((fn) => fn());
  });

  return (
    <div ref={root} className="relative bg-paper text-ink font-body min-h-screen overflow-x-clip">
      {/* Background layers, behind the content. The helix is hidden on phones. */}
      <AmbientBackground className="z-0" />
      <HelixBackdrop className="hidden md:block z-0" />
      <ScrollProgress />

      <div className="relative z-10">
        <header data-nav className="max-w-6xl mx-auto px-6 md:px-10 py-6 flex items-center justify-between">
          <div className="font-display font-semibold text-lg tracking-tight flex items-center gap-2">
            <span className="w-2.5 h-2.5 rounded-full bg-helix-teal inline-block" />
            SkillDNA<span className="text-helix-teal">.AI</span>
          </div>
          <Link
            to="/app"
            data-magnetic
            className="font-display text-sm font-medium px-5 py-2.5 rounded-full bg-ink text-paper hover:bg-helix-teal transition-colors duration-300 inline-block"
          >
            Sequence my skills →
          </Link>
        </header>

        <section data-hero className="relative max-w-6xl mx-auto px-6 md:px-10 pt-8 md:pt-16 pb-24 grid md:grid-cols-2 gap-12 items-center overflow-hidden">
          <SequenceBackground seed={7} cols={11} rows={6} className="-z-10" />
          <div
            data-glow
            aria-hidden="true"
            className="pointer-events-none absolute left-0 top-0 w-[34rem] h-[34rem] rounded-full bg-helix-teal/10 blur-3xl"
            style={{ left: "50%", top: "40%" }}
          />
          <div className="relative overflow-hidden">
            <p data-hero-line className="font-mono text-xs uppercase tracking-[0.2em] text-helix-teal mb-5">
              Resume · GitHub · LinkedIn · Certificates
            </p>
            <h1 className="font-display text-5xl md:text-6xl font-medium leading-[1.05] tracking-tight mb-6">
              <span data-hero-line className="block">Your skills,</span>
              <span data-hero-line className="block italic font-normal">verified</span>
              <span data-hero-line className="block">not just claimed.</span>
            </h1>
            <p data-hero-sub className="text-ink-soft text-lg leading-relaxed mb-8 max-w-md">
              Most resume tools read one document and take your word for it. SkillDNA AI cross-checks what you say
              against what you've actually built — and gives every skill a confidence score to prove it.
            </p>
            <div className="flex items-center gap-4">
              <Link
                to="/app"
                data-hero-cta
                data-magnetic
                className="font-display font-medium px-7 py-3.5 rounded-full bg-helix-teal text-paper hover:bg-ink transition-colors duration-300 inline-block"
              >
                Get my SkillDNA score
              </Link>
              {/* A button, not an #anchor: this app uses hash routing, so an anchor would
                  change the route and leave the page blank. This scrolls to the section instead. */}
              <button
                type="button"
                data-hero-cta
                onClick={() =>
                  document.getElementById("how-it-works")?.scrollIntoView({
                    behavior: prefersReducedMotion() ? "auto" : "smooth",
                    block: "start",
                  })
                }
                className="font-display text-sm text-ink-soft hover:text-ink underline underline-offset-4 decoration-line"
              >
                See how it works
              </button>
            </div>
          </div>

          <div className="relative flex justify-center">
            <div data-hero-helix>
              <Helix variant="hero" height={480} width={320} spin speed={0.55} />
            </div>
            <div
              data-hero-legend
              className="absolute -bottom-2 left-1/2 -translate-x-1/2 flex gap-6 font-mono text-[11px] text-ink-soft"
            >
              <span className="flex items-center gap-1.5">
                <span className="w-2 h-2 rounded-full bg-helix-violet inline-block" /> claimed
              </span>
              <span className="flex items-center gap-1.5">
                <span className="w-2 h-2 rounded-full bg-helix-teal inline-block" /> verified
              </span>
            </div>
          </div>
        </section>

        <div data-strip className="border-y border-line grain">
          <div className="max-w-6xl mx-auto px-6 md:px-10 py-4 flex flex-wrap gap-x-10 gap-y-2 justify-between font-mono text-xs text-ink-soft">
            <span data-strip-item>4 evidence sources</span>
            <span data-strip-item>1 composite score</span>
            <span data-strip-item>noisy-OR cross-validation</span>
            <span data-strip-item>built for students &amp; early-career engineers</span>
          </div>
        </div>

        <section id="how-it-works" data-steps-section className="relative max-w-6xl mx-auto px-6 md:px-10 py-24 md:min-h-[190vh]">
          <div data-steps-stick className="md:sticky md:top-24">
          <p data-steps-eyebrow className="font-mono text-xs uppercase tracking-[0.2em] text-helix-teal mb-3">
            The pipeline
          </p>
          <h2 data-steps-heading className="font-display text-3xl md:text-4xl font-medium tracking-tight mb-14 max-w-xl">
            Four sources go in. One honest score comes out.
          </h2>

          <div className="relative grid md:grid-cols-2 gap-x-10 gap-y-12">
            <svg
              className="hidden md:block absolute -left-6 top-2 w-3 h-[calc(100%-1rem)] pointer-events-none"
              viewBox="0 0 12 500"
              preserveAspectRatio="none"
              aria-hidden="true"
            >
              <path data-sequence-line d="M 6 0 L 6 500" stroke="var(--color-helix-teal)" strokeWidth="2" fill="none" />
            </svg>

            {steps.map((s) => (
              <div key={s.n} data-step-card className="flex gap-5 rounded-2xl">
                <span className="font-mono text-sm text-helix-teal pt-1">{s.n}</span>
                <div>
                  <h3 className="font-display text-xl font-medium mb-2">{s.title}</h3>
                  <p className="text-ink-soft leading-relaxed">{s.body}</p>
                </div>
              </div>
            ))}
          </div>
          </div>
        </section>

        <section className="bg-ink text-paper py-24 overflow-hidden">
          <div className="max-w-6xl mx-auto px-6 md:px-10 grid md:grid-cols-5 gap-12 items-center">
            <div data-explainer-text className="md:col-span-3">
              <p className="font-mono text-xs uppercase tracking-[0.2em] text-helix-teal mb-3">Why this is different</p>
              <h2 className="font-display text-3xl md:text-4xl font-medium tracking-tight mb-6 leading-tight">
                Saying "expert in Python" on a resume is free.
                <br />
                <span className="text-helix-teal">Proving it isn't.</span>
              </h2>
              <ScrubText
                className="text-paper/70 leading-relaxed mb-6 max-w-lg"
                text="Every skill starts as a claim. It only becomes a strength once it shows up somewhere else — a GitHub repo, a certificate, a LinkedIn endorsement. Each independent source you add raises the confidence score for that skill. One source, modest score. Three sources agreeing, high score."
              />
              <div className="flex gap-8 font-mono text-sm">
                <div>
                  <p className="text-3xl font-display text-helix-violet mb-1">
                    <span data-count="1">0</span> source
                  </p>
                  <p className="text-paper/50">
                    ~<span data-count="55">0</span> / 100
                  </p>
                </div>
                <div>
                  <p className="text-3xl font-display text-helix-teal mb-1">
                    <span data-count="3">0</span> sources
                  </p>
                  <p className="text-paper/50">
                    ~<span data-count="90">0</span> / 100
                  </p>
                </div>
              </div>
            </div>
            <div data-explainer-helix className="md:col-span-2 flex justify-center">
              <Helix variant="hero" height={340} width={220} spin speed={0.4} />
            </div>
          </div>
        </section>

        <section data-cta className="max-w-6xl mx-auto px-6 md:px-10 py-28 text-center">
          <h2 className="font-display text-4xl md:text-5xl font-medium tracking-tight mb-6">
            Find out what your evidence
            <br />
            actually says about you.
          </h2>
          <Link
            to="/app"
            data-magnetic
            className="inline-block font-display font-medium px-8 py-4 rounded-full bg-helix-teal text-paper hover:bg-ink transition-colors duration-300"
          >
            Sequence my skills →
          </Link>
        </section>

        <footer className="border-t border-line py-8">
          <div className="max-w-6xl mx-auto px-6 md:px-10 flex flex-col md:flex-row justify-between gap-3 font-mono text-xs text-ink-soft">
            <span>SkillDNA AI — Basaveshwar Engineering College Bagalkote, DISE, 22UIS717P</span>
            <span>Built with FastAPI, React, GSAP &amp; Tesseract OCR</span>
          </div>
        </footer>
      </div>
    </div>
  );
}
