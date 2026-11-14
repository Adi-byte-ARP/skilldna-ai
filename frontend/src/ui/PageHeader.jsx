/*
 * The heading block at the top of every signed-in page: an eyebrow naming the area, the page title,
 * an optional line of description, and any controls (such as the role picker) below them.
 */
export default function PageHeader({ eyebrow, title, description, children }) {
  return (
    <header className="space-y-3 border-b border-line pb-6">
      {eyebrow && <p className="font-mono text-[11px] uppercase tracking-[0.2em] text-helix-teal">{eyebrow}</p>}
      <h1 className="font-display text-2xl font-medium tracking-tight md:text-3xl">{title}</h1>
      {description && <p className="max-w-2xl text-sm leading-relaxed text-ink-soft">{description}</p>}
      {children && <div className="flex flex-wrap items-center gap-3 pt-1">{children}</div>}
    </header>
  );
}
