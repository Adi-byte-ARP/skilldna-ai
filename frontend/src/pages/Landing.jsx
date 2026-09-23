import { useRef, useLayoutEffect } from "react";
import { Link } from "react-router-dom";
import { gsap, ScrollTrigger } from "../lib/gsapSetup";
import Helix from "../components/Helix";
import SequenceBackground from "../components/SequenceBackground";

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

  useLayoutEffect(() => {
    const ctx = gsap.context(() => {
      // Hero entrance: nav fades down, headline lines stagger up, helix scales in
      const heroTl = gsap.timeline({ defaults: { ease: "power3.out" } });
      heroTl
        .from("[data-nav]", { y: -16, opacity: 0, duration: 0.5 })
        .from(
          "[data-hero-line]",
          { y: 46, opacity: 0, duration: 0.9, stagger: 0.09 },
          "-=0.2"
        )
        .from("[data-hero-sub]", { y: 16, opacity: 0, duration: 0.6 }, "-=0.5")
        .from("[data-hero-cta]", { y: 12, opacity: 0, duration: 0.5, stagger: 0.08 }, "-=0.4")
        .from(
          "[data-hero-helix]",
          { opacity: 0, scale: 0.85, duration: 1, ease: "power2.out" },
          "-=0.9"
        )
        .from("[data-hero-legend]", { opacity: 0, duration: 0.5 }, "-=0.3");

      // Gentle parallax float on the hero helix, independent of scroll
      gsap.to("[data-hero-helix]", {
        y: -14,
        duration: 3.2,
        ease: "sine.inOut",
        repeat: -1,
        yoyo: true,
      });

      // Divider strip: numbers/labels drift in from the left as they enter view
      gsap.from("[data-strip-item]", {
        scrollTrigger: { trigger: "[data-strip]", start: "top 90%" },
        x: -20,
        opacity: 0,
        stagger: 0.08,
        duration: 0.6,
        ease: "power2.out",
      });

      // How-it-works: each step slides in, and a connecting sequence line
      // draws itself alongside — literal "sequencing" motion tied to scroll
      gsap.from("[data-steps-eyebrow], [data-steps-heading]", {
        scrollTrigger: { trigger: "[data-steps-heading]", start: "top 85%" },
        y: 24,
        opacity: 0,
        duration: 0.7,
        stagger: 0.1,
        ease: "power3.out",
      });

      gsap.utils.toArray("[data-step-card]").forEach((card, i) => {
        gsap.from(card, {
          scrollTrigger: { trigger: card, start: "top 88%" },
          x: i % 2 === 0 ? -40 : 40,
          opacity: 0,
          duration: 0.7,
          ease: "power3.out",
        });
      });

      const seqLine = document.querySelector("[data-sequence-line]");
      if (seqLine) {
        const length = seqLine.getTotalLength();
        gsap.set(seqLine, { strokeDasharray: length, strokeDashoffset: length });
        gsap.to(seqLine, {
          strokeDashoffset: 0,
          ease: "none",
          scrollTrigger: {
            trigger: "[data-steps-section]",
            start: "top 70%",
            end: "bottom 60%",
            scrub: 0.6,
          },
        });
      }

      // Scoring explainer: text reveal + helix scale-in + count-up stats
      gsap.from("[data-explainer-text] > *", {
        scrollTrigger: { trigger: "[data-explainer-text]", start: "top 80%" },
        y: 26,
        opacity: 0,
        duration: 0.7,
        stagger: 0.12,
        ease: "power3.out",
      });

      gsap.from("[data-explainer-helix]", {
        scrollTrigger: { trigger: "[data-explainer-helix]", start: "top 85%" },
        opacity: 0,
        scale: 0.8,
        duration: 0.9,
        ease: "back.out(1.4)",
      });

      gsap.utils.toArray("[data-count]").forEach((el) => {
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

      // CTA section
      gsap.from("[data-cta] > *", {
        scrollTrigger: { trigger: "[data-cta]", start: "top 85%" },
        y: 28,
        opacity: 0,
        duration: 0.8,
        stagger: 0.1,
        ease: "power3.out",
      });

      // Magnetic-ish hover lift on primary buttons
      gsap.utils.toArray("[data-magnetic]").forEach((btn) => {
        const onEnter = () => gsap.to(btn, { scale: 1.045, duration: 0.25, ease: "power2.out" });
        const onLeave = () => gsap.to(btn, { scale: 1, duration: 0.35, ease: "power2.out" });
        btn.addEventListener("mouseenter", onEnter);
        btn.addEventListener("mouseleave", onLeave);
      });
    }, root);

    return () => ctx.revert();
  }, []);

  return (
    <div ref={root} className="bg-paper text-ink font-body min-h-screen overflow-x-hidden">
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

      <section className="relative max-w-6xl mx-auto px-6 md:px-10 pt-8 md:pt-16 pb-24 grid md:grid-cols-2 gap-12 items-center">
        <SequenceBackground seed={7} cols={11} rows={6} className="-z-10" />
        <div className="overflow-hidden">
          <p data-hero-line className="font-mono text-xs uppercase tracking-[0.2em] text-helix-teal mb-5">
            Resume · GitHub · LinkedIn · Certificates
          </p>
          <h1 className="font-display text-5xl md:text-6xl font-medium leading-[1.05] tracking-tight mb-6">
            <span data-hero-line className="block">Your skills,</span>
            <span data-hero-line className="block italic font-normal">verified</span>
            <span data-hero-line className="block">not just claimed.</span>
          </h1>
          <p data-hero-sub className="text-ink-soft text-lg leading-relaxed mb-8 max-w-md">
            Most resume tools read one document and take your word for it.
            SkillDNA AI cross-checks what you say against what you've actually
            built — and gives every skill a confidence score to prove it.
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
            <a
              href="#how-it-works"
              data-hero-cta
              className="font-display text-sm text-ink-soft hover:text-ink underline underline-offset-4 decoration-line"
            >
              See how it works
            </a>
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

      <section id="how-it-works" data-steps-section className="max-w-6xl mx-auto px-6 md:px-10 py-24 relative">
        <p data-steps-eyebrow className="font-mono text-xs uppercase tracking-[0.2em] text-helix-teal mb-3">
          The pipeline
        </p>
        <h2 data-steps-heading className="font-display text-3xl md:text-4xl font-medium tracking-tight mb-14 max-w-xl">
          Four sources go in. One honest score comes out.
        </h2>

        <div className="relative grid md:grid-cols-2 gap-x-10 gap-y-12">
          <svg
            className="hidden md:block absolute -left-6 top-2 bottom-2 w-3 pointer-events-none"
            viewBox="0 0 12 500"
            preserveAspectRatio="none"
            aria-hidden="true"
          >
            <path
              data-sequence-line
              d="M 6 0 L 6 500"
              stroke="var(--color-helix-teal)"
              strokeWidth="2"
              fill="none"
            />
          </svg>

          {steps.map((s) => (
            <div key={s.n} data-step-card className="flex gap-5">
              <span className="font-mono text-sm text-helix-teal pt-1">{s.n}</span>
              <div>
                <h3 className="font-display text-xl font-medium mb-2">{s.title}</h3>
                <p className="text-ink-soft leading-relaxed">{s.body}</p>
              </div>
            </div>
          ))}
        </div>
      </section>

      <section className="bg-ink text-paper py-24 overflow-hidden">
        <div className="max-w-6xl mx-auto px-6 md:px-10 grid md:grid-cols-5 gap-12 items-center">
          <div data-explainer-text className="md:col-span-3">
            <p className="font-mono text-xs uppercase tracking-[0.2em] text-helix-teal mb-3">
              Why this is different
            </p>
            <h2 className="font-display text-3xl md:text-4xl font-medium tracking-tight mb-6 leading-tight">
              Saying "expert in Python" on a resume is free.
              <br />
              <span className="text-helix-teal">Proving it isn't.</span>
            </h2>
            <p className="text-paper/70 leading-relaxed mb-6 max-w-lg">
              Every skill starts as a claim. It only becomes a strength once
              it shows up somewhere else — a GitHub repo, a certificate, a
              LinkedIn endorsement. Each independent source you add raises
              the confidence score for that skill. One source, modest score.
              Three sources agreeing, high score.
            </p>
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
  );
}
