/** A titled list of past entries, used at the bottom of each practice page. */
export default function HistoryPanel({ title, subtitle, loading, empty, children }) {
  return (
    <section className="rounded-2xl border border-line bg-surface p-6">
      <p className="font-display font-medium">{title}</p>
      {subtitle && <p className="text-xs text-ink-soft mt-1">{subtitle}</p>}
      <div className="mt-4">
        {loading ? <p className="text-sm text-ink-soft">Loading history…</p> : null}
        {!loading && empty ? <p className="text-sm text-ink-soft">{empty}</p> : null}
        {!loading && !empty ? children : null}
      </div>
    </section>
  );
}
