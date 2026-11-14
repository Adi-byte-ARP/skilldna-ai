import Card from "../ui/Card";
import Badge from "../ui/Badge";
import Button from "../ui/Button";
import Icon from "../ui/Icon";

const PRIORITY_TONE = { High: "coral", Medium: "violet" };

/** The skills the user should work on first, ranked, with why and what to do next. */
export function SkillsToImproveCard({ improve, onOpen }) {
  const items = improve || [];
  return (
    <Card as="section" className="flex flex-col gap-4" aria-label="Skills to improve">
      <div>
        <p className="font-mono text-[11px] uppercase tracking-widest text-helix-teal">From your evidence</p>
        <p className="mt-1 font-display text-lg font-medium">Skills to improve</p>
        <p className="mt-1 text-xs text-ink-soft">
          {items.length === 0
            ? "Nothing to improve for this role yet."
            : `${items.length} skill${items.length === 1 ? "" : "s"} for this role, most urgent first.`}
        </p>
      </div>
      <ol className="space-y-3">
        {items.slice(0, 6).map((item) => (
          <li key={item.key} className="rounded-xl border border-line bg-paper-dim/40 p-3">
            <div className="flex items-center justify-between gap-2">
              <span className="font-display text-sm font-medium">{item.skill}</span>
              <Badge tone={PRIORITY_TONE[item.priority] || "neutral"}>{item.priority}</Badge>
            </div>
            {item.score != null && (
              <p className="mt-1 font-mono text-[11px] text-ink-soft">{Math.round(item.score)}/100 shown</p>
            )}
            <p className="mt-1 text-xs text-ink-soft">{item.reason}</p>
            {item.next_task && (
              <p className="mt-2 text-xs"><span className="text-helix-teal">Next:</span> {item.next_task}</p>
            )}
            {item.locked ? (
              <p className="mt-2 flex items-center gap-1.5 text-xs text-ink-soft">
                <Icon name="lock" className="h-3.5 w-3.5 text-ink-soft" /> Opens when the earlier phases are passed.
              </p>
            ) : (
              <button type="button" onClick={() => onOpen(item.key)}
                className="mt-2 text-xs font-medium text-helix-teal underline underline-offset-4">
                Open this skill
              </button>
            )}
          </li>
        ))}
      </ol>
    </Card>
  );
}

/** Pick any role and get the full roadmap from zero, separate from the evidence-based plan. */
export function LearnCard({ roles, value, onChange, onBuild, mode, onBack, currentRole }) {
  return (
    <Card as="section" className="flex flex-col gap-4" aria-label="Learn a role from scratch">
      <div>
        <p className="font-mono text-[11px] uppercase tracking-widest text-helix-violet">Start from zero</p>
        <p className="mt-1 font-display text-lg font-medium">Learn a role</p>
        <p className="mt-1 text-xs text-ink-soft">
          The full roadmap for a role, from scratch: every skill, its phases, notes, videos and tests.
          Your existing evidence is not used, and progress is kept separate from your gap plan.
        </p>
      </div>
      {mode === "scratch" ? (
        <div className="space-y-3">
          <p className="text-sm">Showing the full roadmap for <span className="font-medium">{currentRole}</span>.</p>
          <Button variant="ghost" size="sm" onClick={onBack}>Back to my gap plan</Button>
        </div>
      ) : (
        <div className="flex flex-wrap items-center gap-3">
          <label htmlFor="learn-role" className="sr-only">Role to learn</label>
          <select id="learn-role" value={value} onChange={(e) => onChange(e.target.value)}
            className="min-w-0 flex-1 rounded-xl border border-line bg-surface px-3 py-2 text-sm">
            {roles.map((r) => <option key={r} value={r}>{r}</option>)}
          </select>
          <Button variant="ink" size="sm" onClick={onBuild}>Build full roadmap</Button>
        </div>
      )}
    </Card>
  );
}
