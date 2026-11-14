import { Link } from "react-router-dom";
import { SkeletonLines } from "../ui/Skeleton";
import Icon from "../ui/Icon";

/*
 * One practice module on the dashboard. The same structure for every module: an icon and a
 * title, a headline number, the latest history, and one action at the foot of the card.
 */
export default function FeatureCard({ title, description, stat, statLabel, items, emptyText, to, cta, loading, icon, status }) {
  return (
    <article className="flex flex-col rounded-2xl border border-line bg-surface transition-shadow duration-300 hover:shadow-[0_16px_40px_-24px_rgba(13,17,23,0.4)]">
      <div className="flex items-start justify-between gap-3 p-6 pb-5">
        <div className="flex min-w-0 items-start gap-3">
          {icon && (
            <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-helix-teal/10 text-helix-teal">
              <Icon name={icon} className="h-5 w-5" />
            </span>
          )}
          <div className="min-w-0">
            <p className="font-display text-lg font-medium">{title}</p>
            <p className="mt-1 text-sm leading-relaxed text-ink-soft">{description}</p>
          </div>
        </div>
        {status && (
          <span className="shrink-0 rounded-full border border-line px-2.5 py-0.5 font-mono text-[10px] uppercase tracking-widest text-ink-soft">
            {status}
          </span>
        )}
      </div>

      <div className="mx-6 border-y border-line py-4">
        <p className="font-display text-3xl font-medium tracking-tight">{loading ? "…" : stat ?? "–"}</p>
        {statLabel && <p className="mt-1 font-mono text-[11px] uppercase tracking-widest text-ink-soft">{statLabel}</p>}
      </div>

      <div className="flex-1 px-6 py-4">
        <p className="mb-2 font-mono text-[11px] uppercase tracking-widest text-ink-soft">Recent history</p>
        {loading ? (
          <SkeletonLines lines={3} />
        ) : items.length === 0 ? (
          <p className="text-sm text-ink-soft">{emptyText}</p>
        ) : (
          <ul className="divide-y divide-line text-sm">
            {items.slice(0, 3).map((item) => (
              <li key={item.key} className="flex justify-between gap-3 py-2">
                <span className="font-mono text-xs text-ink-soft">{item.when}</span>
                <span className="truncate">{item.label}</span>
                <span className={`font-mono text-xs ${item.tone ?? "text-ink"}`}>{item.value}</span>
              </li>
            ))}
          </ul>
        )}
      </div>

      <div className="p-6 pt-2">
        <Link
          to={to}
          className="flex w-full items-center justify-center gap-2 rounded-full bg-ink px-4 py-2.5 font-display text-sm font-medium text-paper transition-colors duration-300 hover:bg-helix-teal"
        >
          {cta}
          <Icon name="arrow" className="h-4 w-4" />
        </Link>
      </div>
    </article>
  );
}
