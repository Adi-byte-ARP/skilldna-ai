/** What a page shows when there is nothing yet, with a clear next step. */
export default function EmptyState({ title, body, action }) {
  return (
    <div className="rounded-2xl border border-dashed border-line bg-surface/60 px-6 py-10 text-center">
      <p className="font-display text-lg font-medium">{title}</p>
      {body && <p className="mx-auto mt-2 max-w-md text-sm text-ink-soft">{body}</p>}
      {action && <div className="mt-5">{action}</div>}
    </div>
  );
}
