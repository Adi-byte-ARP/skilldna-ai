import { useEffect, useLayoutEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../lib/api";
import AppHeader from "../layout/AppHeader";
import { useToast } from "../ui/useToast";
import { SkeletonLines } from "../ui/Skeleton";
import { gsap, ScrollTrigger, prefersReducedMotion, useGsap } from "../lib/motion";
import Card from "../ui/Card";
import AmbientBackground from "../components/AmbientBackground";
import Appear from "../components/Appear";
import HistoryPanel from "../components/HistoryPanel";
import PhaseTest from "../components/PhaseTest";
import { LearnCard, SkillsToImproveCard } from "../components/PlanCards";
import PageHeader from "../ui/PageHeader";
import Badge from "../ui/Badge";
import ScrollProgress from "../components/ScrollProgress";
import Icon from "../ui/Icon";

const DEFAULT_ROLE = "Full-Stack Developer";

const PHASE_BADGE = {
  locked: { tone: "neutral", label: "Locked" },
  in_progress: { tone: "violet", label: "In progress" },
  test_ready: { tone: "teal", label: "Test ready" },
  passed: { tone: "teal", label: "Passed" },
};

export default function Plan() {
  const page = useRef(null);
  const toast = useToast();
  const barRef = useRef(null);
  const [roles, setRoles] = useState([DEFAULT_ROLE]);
  const [role, setRole] = useState(DEFAULT_ROLE);
  const [plan, setPlan] = useState(null);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(false);
  const [open, setOpen] = useState({});
  // "gap" is the plan built from the user's evidence; "scratch" is the full roadmap for a role from zero.
  const [mode, setMode] = useState("gap");
  const [learnRole, setLearnRole] = useState(DEFAULT_ROLE);
  const [history, setHistory] = useState({ loading: true, rows: [] });

  // Snapshot history. It refreshes whenever the plan changes, because each view records a snapshot.
  useEffect(() => {
    let cancelled = false;
    api.planHistory()
      .then((rows) => { if (!cancelled) setHistory({ loading: false, rows }); })
      .catch(() => { if (!cancelled) setHistory({ loading: false, rows: [] }); });
    return () => { cancelled = true; };
  }, [plan?.progress?.done, role]);

  useEffect(() => {
    api.mockRoles().then((r) => setRoles(r.roles)).catch(() => {});
    // The plan follows the user's role: the target they chose, or the role their evidence fits best.
    api.profileGet().then((p) => { if (p?.effective_role) setRole(p.effective_role); }).catch(() => {});
  }, []);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);
    api.planGet(role, mode)
      .then((p) => { if (!cancelled) setPlan(p); })
      .catch((e) => { if (!cancelled) setError(e.message || "Could not build your plan."); })
      .finally(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
  }, [role, mode]);

  async function toggleTask(item, task) {
    const next = !task.done;
    // optimistic update, then confirm with the server
    setPlan((p) => updateTask(p, task.key, next));
    try {
      await api.planToggleTask(task.key, next, role, mode);
      const fresh = await api.planGet(role, mode);
      setPlan(fresh);
    } catch (e) {
      setPlan((p) => updateTask(p, task.key, !next));
      toast.show(e.message || "Could not save that task. It has been unticked.", "error");
    }
  }

  const toggleOpen = (key) => setOpen((o) => ({ ...o, [key]: !o[key] }));

  // Entrance for the header block, once.
  useGsap(page, ({ reduce }) => {
    if (reduce) return undefined;
    gsap.from("[data-plan-header]", { y: 14, opacity: 0, duration: 0.6, ease: "power3.out" });
    return undefined;
  });

  // Progress bar: glide to the new percentage whenever a task is ticked.
  useLayoutEffect(() => {
    const bar = barRef.current;
    if (!bar || !plan) return undefined;
    const target = `${plan.progress.percent}%`;
    if (prefersReducedMotion()) {
      bar.style.width = target;
      return undefined;
    }
    const tween = gsap.to(bar, { width: target, duration: 0.8, ease: "power3.out" });
    return () => tween.kill();
  }, [plan]);

  // Skill cards reveal as they scroll into view. Re-run only when the set of skills changes,
  // not on every tick, so ticking a task never replays the reveal.
  const itemsKey = plan ? plan.items.map((it) => it.key).join("|") : "";
  useGsap(page, ({ reduce }) => {
    if (reduce || !itemsKey) return undefined;
    const cards = gsap.utils.toArray("[data-plan-card]", page.current);
    ScrollTrigger.batch(cards, {
      start: "top 92%",
      once: true,
      onEnter: (batch) => gsap.from(batch, { y: 26, opacity: 0, duration: 0.7, stagger: 0.1, ease: "power3.out" }),
    });
    return undefined;
  }, [itemsKey]);

  return (
    <div ref={page} className="relative min-h-screen bg-paper text-ink font-body overflow-hidden">
      <AmbientBackground className="z-0 opacity-60" />
      <ScrollProgress />
      <div className="relative z-10">
      <AppHeader width="page" />

      <main className="max-w-4xl mx-auto px-6 md:px-10 py-10 space-y-8">
        <PageHeader
          eyebrow="Improve plan"
          title={mode === "scratch" ? "Your full roadmap" : "Your skill-gap roadmap"}
          description={mode === "scratch"
            ? "Every skill for the role, from zero, with notes, videos and a test at the end of each phase."
            : "The skills your target role needs that your evidence does not yet show, in the order to learn them."}
        >
          <label htmlFor="plan-role" className="font-mono text-xs uppercase tracking-widest text-ink-soft">Target role</label>
            <select
              id="plan-role"
              value={role}
              onChange={(e) => setRole(e.target.value)}
              className="rounded-xl border border-line px-4 py-2 bg-surface"
            >
              {roles.map((r) => <option key={r} value={r}>{r}</option>)}
            </select>
        </PageHeader>

        {error && <p className="text-signal-coral text-sm font-mono">{error}</p>}
        {loading && !plan && <SkeletonLines lines={5} />}

        <div className="grid items-start gap-4 md:grid-cols-2">
          {mode === "gap" && plan && (
            <SkillsToImproveCard
              improve={[...plan.improve]
                .map((it) => ({ ...it, locked: !!plan.items.find((p) => p.key === it.key)?.locked }))
                .sort((a, b) => Number(a.locked) - Number(b.locked))}
              onOpen={(key) => {
              setOpen((o) => ({ ...o, [key]: true }));
              requestAnimationFrame(() => document.getElementById(`skill-${key}`)?.scrollIntoView({ behavior: "smooth", block: "center" }));
            }} />
          )}
          <LearnCard
            roles={roles}
            value={learnRole}
            onChange={setLearnRole}
            onBuild={() => { setRole(learnRole); setMode("scratch"); }}
            mode={mode}
            currentRole={role}
            onBack={() => setMode("gap")}
          />
        </div>

        {plan && (
          <>
            {plan.mode === "scratch" && (
              <div role="status" className="rounded-2xl border border-helix-violet/40 bg-helix-violet/5 px-5 py-4 text-sm">
                <span className="font-medium">Learning from scratch: {plan.role}.</span>{" "}
                Every skill for this role is a step, including ones you already show. Your progress here is kept apart from your gap plan.
              </div>
            )}
            <section data-plan-header className="rounded-2xl border border-line bg-surface p-6 space-y-4">
              <div className="flex flex-wrap items-baseline gap-x-6 gap-y-2">
                <p className="font-display text-4xl font-medium">{Math.round(plan.overall_score)}<span className="text-ink-soft text-xl">/100</span></p>
                <p className="text-sm text-ink-soft">{plan.tier}</p>
                <p className="text-sm text-ink-soft">{plan.gap_count} gaps · about {plan.total_hours_estimate} hours</p>
              </div>
              <p className="text-sm leading-relaxed">{plan.summary}</p>
              {plan.strengths_to_leverage?.length > 0 && (
                <div className="flex flex-wrap gap-2">
                  <span className="text-xs text-ink-soft mr-1 self-center">Strengths:</span>
                  {plan.strengths_to_leverage.map((s) => (
                    <span key={s} className="font-mono text-xs px-3 py-1 rounded-full bg-helix-teal/10 text-helix-teal">{s}</span>
                  ))}
                </div>
              )}
              <div>
                <div className="flex justify-between text-xs text-ink-soft mb-1">
                  <span>Task progress</span>
                  <span>{plan.progress.done} of {plan.progress.total} ({plan.progress.percent}%)</span>
                </div>
                <div className="h-2 rounded-full bg-line overflow-hidden">
                  <div ref={barRef} className="h-full bg-helix-teal" style={{ width: "0%" }} />
                </div>
              </div>
            </section>

            {plan.no_gaps && (
              <p className="text-sm text-ink-soft">Your profile already covers every skill for this role. Use the daily challenge and mock interviews to keep sharp.</p>
            )}

            {plan.phases.map((phase, pi) => {
              const phaseItems = plan.items.filter((it) => phase.items.includes(it.key));
              const badge = PHASE_BADGE[phase.status] || PHASE_BADGE.in_progress;
              const isLearning = phaseItems.length > 0;
              return (
                <section key={phase.name} className="space-y-4" data-phase-status={phase.status}>
                  <div className="flex flex-wrap items-start justify-between gap-3">
                    <div>
                      <h2 className="font-display text-lg font-medium">{phase.name}</h2>
                      <p className="text-sm text-ink-soft">{phase.goal}</p>
                    </div>
                    {isLearning && (
                      <div className="flex items-center gap-2">
                        <Badge tone={badge.tone}>{badge.label}</Badge>
                        <span className="font-mono text-[11px] text-ink-soft">{phase.tasks_done}/{phase.tasks_total} tasks</span>
                      </div>
                    )}
                  </div>
                  {isLearning && phase.status === "locked" && (
                    <Card tone="coral" className="flex items-start gap-3">
                      <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-signal-coral/10 text-signal-coral"><Icon name="lock" className="h-4 w-4" /></span>
                      <div className="text-sm">
                        <p className="font-medium">This phase is locked</p>
                        <p className="mt-1 text-ink-soft">{phase.locked_reason}</p>
                      </div>
                    </Card>
                  )}
                  {isLearning && phase.test && phase.test.passed && (
                    <p className="text-sm text-helix-teal">✓ Phase test passed ({Math.round(phase.test.best_score)}%)</p>
                  )}
                  {pi === plan.phases.length - 1 && (
                    <div className="rounded-xl border border-dashed border-line p-4 text-sm">
                      <Link to="/app/mock" className="text-helix-teal underline underline-offset-4">Start a mock test or interview</Link>
                      {" · "}
                      <Link to="/app/daily" className="text-helix-teal underline underline-offset-4">Today's daily challenge</Link>
                    </div>
                  )}
                  {isLearning && phase.status !== "locked" && phaseItems.map((item) => (
                    <SkillCard
                      key={item.key}
                      item={item}
                      open={!!open[item.key]}
                      onToggleOpen={() => toggleOpen(item.key)}
                      onToggleTask={(task) => toggleTask(item, task)}
                    />
                  ))}
                  {isLearning && phase.test && phase.test.available && (
                    <PhaseTest index={pi} role={role} mode={mode} onPassed={() => api.planGet(role, mode).then(setPlan)} />
                  )}
                </section>
              );
            })}
          </>
        )}
        <HistoryPanel
          title="Plan history"
          subtitle="One snapshot per role per day. Progress shows how many tasks you had ticked off."
          loading={history.loading}
          empty={history.rows.length === 0 ? "No history yet. Your first snapshot is saved when you open the plan." : null}
        >
          <ul className="divide-y divide-line text-sm">
            {history.rows.slice(0, 30).map((row) => (
              <li key={`${row.day}-${row.role}`} className="py-3 grid grid-cols-[6rem_1fr_auto] items-center gap-4">
                <span className="font-mono text-xs text-ink-soft">{row.day}</span>
                <span>
                  {row.role}
                  <span className="block text-xs text-ink-soft">{row.tasks_done} of {row.tasks_total} tasks · {row.gap_count} gaps</span>
                </span>
                <span className="text-right">
                  <span className="block font-display">{Math.round(row.overall_score)}/100</span>
                  <span className="block font-mono text-xs text-helix-teal">{Math.round(row.progress_percent)}% done</span>
                </span>
              </li>
            ))}
          </ul>
        </HistoryPanel>
      </main>
      </div>
    </div>
  );
}

function SkillCard({ item, open, onToggleOpen, onToggleTask }) {
  const statusLabel = item.status === "missing" ? "Not shown yet" : `Weak · ${item.current_score}`;
  const doneCount = item.tasks.filter((t) => t.done).length;
  return (
    <article id={`skill-${item.key}`} data-plan-card className="rounded-2xl border border-line bg-surface scroll-mt-24">
      <button type="button" onClick={onToggleOpen} aria-expanded={open} className="w-full text-left p-5 flex flex-wrap items-center gap-3 justify-between">
        <div>
          <p className="font-display font-medium">{item.skill}</p>
          <p className="text-xs text-ink-soft mt-1">{item.why}</p>
        </div>
        <div className="flex items-center gap-3 text-xs font-mono">
          <span className={`px-2.5 py-1 rounded-full ${item.status === "missing" ? "bg-signal-coral/10 text-signal-coral" : "bg-helix-violet/10 text-helix-violet"}`}>{statusLabel}</span>
          <span className="text-ink-soft">{doneCount}/{item.tasks.length} tasks · {item.hours_estimate}h</span>
          <span aria-hidden>{open ? "−" : "+"}</span>
        </div>
      </button>

      {open && (
        <Appear y={-8} duration={0.4} className="px-5 pb-6 space-y-5 border-t border-line pt-5">
          <div>
            <p className="font-mono text-xs uppercase tracking-widest text-ink-soft mb-2">Objectives</p>
            <ul className="list-disc pl-5 text-sm space-y-1">
              {item.objectives.map((o) => <li key={o}>{o}</li>)}
            </ul>
          </div>

          {item.notes?.length > 0 && (
            <div className="rounded-xl border border-line bg-paper-dim/60 p-4">
              <p className="font-mono text-xs uppercase tracking-widest text-ink-soft mb-2">Study notes</p>
              <ul className="list-disc space-y-1.5 pl-5 text-sm leading-relaxed">
                {item.notes.map((note) => <li key={note}>{note}</li>)}
              </ul>
            </div>
          )}

          <div>
            <p className="font-mono text-xs uppercase tracking-widest text-ink-soft mb-2">Weekly tasks</p>
            <ul className="space-y-2">
              {item.tasks.map((task) => (
                <li key={task.key}>
                  <label className="flex items-start gap-3 text-sm cursor-pointer">
                    <input type="checkbox" className="mt-1" checked={task.done} onChange={() => onToggleTask(task)} />
                    <span className={task.done ? "line-through text-ink-soft" : ""}>{task.text}</span>
                  </label>
                  {task.videos?.length > 0 && (
                    <div className="ml-7 mt-1 flex flex-wrap gap-x-4 gap-y-1 text-xs">
                      {task.videos.map((v) => (
                        <a key={v.url} href={v.url} target="_blank" rel="noopener noreferrer"
                          className="text-helix-teal underline underline-offset-4">▶ {v.title}</a>
                      ))}
                    </div>
                  )}
                </li>
              ))}
            </ul>
          </div>

          <div>
            <p className="font-mono text-xs uppercase tracking-widest text-ink-soft mb-2">Project</p>
            <p className="text-sm">{item.project}</p>
          </div>

          <div>
            <p className="font-mono text-xs uppercase tracking-widest text-ink-soft mb-2">Resources</p>
            <ul className="space-y-1 text-sm">
              {item.resources.map((r) => (
                <li key={r.url}>
                  <a href={r.url} target="_blank" rel="noopener noreferrer" className="text-helix-teal underline underline-offset-4">{r.name}</a>
                </li>
              ))}
            </ul>
          </div>

          <p className="text-sm text-ink-soft"><span className="font-medium text-ink">How you will know:</span> {item.check}</p>

          {item.progress && (
            <div className="rounded-xl bg-paper border border-line p-4 space-y-2 text-sm">
              <p className="font-mono text-xs uppercase tracking-widest text-ink-soft">Your progress on {item.skill}</p>
              <p>
                Score: {item.progress.baseline_score ?? "–"} at start
                {item.progress.current_score != null && <> → {item.progress.current_score} now</>}
                {item.progress.score_change != null && (
                  <span className={item.progress.score_change > 0 ? "text-helix-teal" : "text-ink-soft"}>
                    {" "}({item.progress.score_change > 0 ? "+" : ""}{item.progress.score_change})
                  </span>
                )}
              </p>
              <p>Tasks ticked: {item.progress.tasks_done} of {item.progress.tasks_total}</p>
              <p>
                Daily challenges on this skill (30 days): {item.progress.daily_correct} correct of {item.progress.daily_attempts} answered
              </p>
              <p className="text-ink-soft">{item.progress.message}</p>
            </div>
          )}
        </Appear>
      )}
    </article>
  );
}

function updateTask(plan, key, done) {
  if (!plan) return plan;
  const items = plan.items.map((it) => {
    const tasks = it.tasks.map((t) => (t.key === key ? { ...t, done } : t));
    return { ...it, tasks };
  });
  const total = items.reduce((n, it) => n + it.tasks.length, 0);
  const doneCount = items.reduce((n, it) => n + it.tasks.filter((t) => t.done).length, 0);
  return {
    ...plan,
    items,
    progress: { done: doneCount, total, percent: total ? Math.round((1000 * doneCount) / total) / 10 : 0 },
  };
}
