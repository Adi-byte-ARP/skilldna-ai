/*
 * Question text marks code with backticks, as in: What does `'abc'.upper()` return?
 * This shows those segments as inline code instead of printing the backticks.
 */
export default function RichText({ text }) {
  const parts = String(text ?? "").split(/`([^`]+)`/);
  return parts.map((part, i) =>
    i % 2 === 1 ? (
      <code key={i} className="rounded-md bg-paper-dim px-1.5 py-0.5 font-mono text-[0.9em] text-ink">{part}</code>
    ) : (
      part
    ),
  );
}
