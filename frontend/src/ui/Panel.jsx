/*
 * The standard content card: an optional eyebrow, title, description and action in a header,
 * then the body. Every section of the app uses this so the layout reads as one system.
 */
export default function Panel({ eyebrow, title, description, action, children, className = "", label }) {
  return (
    <section aria-label={label || title || eyebrow} className={`rounded-2xl border border-line bg-surface ${className}`}>
      {(eyebrow || title || action) && (
        <header className="flex flex-wrap items-start justify-between gap-4 border-b border-line px-6 py-4">
          <div className="min-w-0">
            {eyebrow && <p className="font-mono text-[11px] uppercase tracking-widest text-ink-soft">{eyebrow}</p>}
            {title && <h2 className="mt-1 font-display text-lg font-medium text-ink">{title}</h2>}
            {description && <p className="mt-1 text-sm leading-relaxed text-ink-soft">{description}</p>}
          </div>
          {action && <div className="shrink-0">{action}</div>}
        </header>
      )}
      <div className="p-6">{children}</div>
    </section>
  );
}
