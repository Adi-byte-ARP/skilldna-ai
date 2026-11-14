const TONES = {
  neutral: "border-line text-ink-soft",
  teal: "border-helix-teal/50 text-helix-teal",
  coral: "border-signal-coral/50 text-signal-coral",
  violet: "border-helix-violet/50 text-helix-violet",
};

/** A small status label. */
export default function Badge({ tone = "neutral", className = "", children }) {
  return (
    <span className={`inline-block whitespace-nowrap rounded-full border px-2.5 py-0.5 font-mono text-[11px] ${TONES[tone]} ${className}`}>
      {children}
    </span>
  );
}
