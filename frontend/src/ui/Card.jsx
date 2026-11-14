/** A surface with the app's border and radius. `tone` tints it for status or emphasis. */
const TONES = {
  default: "border-line bg-surface",
  teal: "border-helix-teal/40 bg-helix-teal-soft/30",
  coral: "border-signal-coral/40 bg-signal-coral-soft/40",
  violet: "border-helix-violet/40 bg-helix-violet-soft/30",
};

export default function Card({ tone = "default", as: Tag = "section", className = "", children, ...rest }) {
  return (
    <Tag className={`rounded-2xl border p-6 ${TONES[tone]} ${className}`} {...rest}>
      {children}
    </Tag>
  );
}
