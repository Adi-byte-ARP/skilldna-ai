import PageHeader from "../ui/PageHeader";
import { useCallback, useEffect, useLayoutEffect, useRef, useState } from "react";
import { api } from "../lib/api";
import AppHeader from "../layout/AppHeader";
import { gsap, prefersReducedMotion, useGsap } from "../lib/motion";
import AmbientBackground from "../components/AmbientBackground";
import Appear from "../components/Appear";
import HistoryPanel from "../components/HistoryPanel";
import { useToast } from "../ui/useToast";
import RichText from "../ui/RichText";

const DEFAULT_ROLE = "Full-Stack Developer";

export default function Daily() {
  const [roles, setRoles] = useState([DEFAULT_ROLE]);
  const [role, setRole] = useState(DEFAULT_ROLE);
  const [today, setToday] = useState(null);
  const [history, setHistory] = useState(null);
  const [emailOptIn, setEmailOptIn] = useState(false);
  const [choice, setChoice] = useState(null);
  const [text, setText] = useState("");
  const [submittedText, setSubmittedText] = useState("");
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);
  const [busy, setBusy] = useState(false);
  const [notifyPermission, setNotifyPermission] = useState(
    typeof Notification !== "undefined" ? Notification.permission : "unsupported"
  );

  // Roles are shared and cached by the API client, so this costs no extra request on most visits.
  useEffect(() => {
    api.mockRoles().then((r) => setRoles(r.roles)).catch(() => {});
  }, []);

  // One request loads the question, the streak, and the reminder state together.
  useEffect(() => {
    let cancelled = false;
    setError(null);
    setChoice(null);
    setText("");
    api.dailyToday(role, new Date().getHours())
      .then((t) => {
        if (cancelled) return;
        setToday(t);
        setResult(t.result);
        setEmailOptIn(!!t.email_opt_in);
      })
      .catch((e) => { if (!cancelled) setError(e.message || "Could not load today's challenge."); });
    return () => { cancelled = true; };
  }, [role]);

  // History loads once on the page, and again only after an answer is saved.
  const loadHistory = useCallback(() => {
    api.dailyHistory().then(setHistory).catch(() => {});
  }, []);
  useEffect(() => { loadHistory(); }, [loadHistory]);

  // Browser notification, at most once a day, when the question is still open in the evening.
  useEffect(() => {
    if (!today?.remind_now || today.answered || typeof Notification === "undefined") return;
    const key = `skilldna-reminder-${new Date().toISOString().slice(0, 10)}`;
    if (Notification.permission === "granted" && !localStorage.getItem(key)) {
      new Notification("SkillDNA daily challenge", { body: "Today's question is still open." });
      localStorage.setItem(key, "1");
    }
  }, [today?.remind_now, today?.answered]);

  async function submit() {
    if (!today || busy) return;
    const payload = today.challenge.kind === "text" ? { answer_text: text } : { answer_index: choice };
    if (today.challenge.kind === "text" ? !text.trim() : choice === null) return;
    setBusy(true);
    setError(null);
    setSubmittedText(text);
    try {
      const r = await api.dailyAnswer(today.challenge.id, payload.answer_index ?? null, role,
        payload.answer_text);
      setResult({
        correct: r.correct,
        your_index: r.your_index,
        correct_index: r.correct_index,
        accepted: r.accepted,
        hits: r.hits,
        needed: r.needed,
        explanation: r.explanation,
        points: r.points,
      });
      setToday((t) => ({ ...t, answered: true, remind_now: false, streak: r.streak, total_points: t.total_points + r.points }));
      loadHistory();
    } catch (e) {
      setError(e.message || "Could not save your answer.");
      toast.show(e.message || "Could not save your answer.", "error");
    } finally {
      setBusy(false);
    }
  }

  async function toggleEmail(on) {
    setEmailOptIn(on);
    try {
      const r = await api.remindersSet(on);
      setEmailOptIn(r.email_opt_in);
    } catch (e) {
      setEmailOptIn(!on);
      setError(e.message || "Could not change reminder settings.");
    }
  }

  async function enableBrowserReminders() {
    if (typeof Notification === "undefined") return;
    const permission = await Notification.requestPermission();
    setNotifyPermission(permission);
  }

  const isText = today?.challenge?.kind === "text";
  const page = useRef(null);
  const toast = useToast();

  // Options arrive one after another when a new question loads.
  const questionKey = today?.challenge?.id;
  useGsap(page, ({ reduce }) => {
    if (reduce || !questionKey) return undefined;
    gsap.from("[data-option]", { y: 10, opacity: 0, duration: 0.45, stagger: 0.06, ease: "power2.out" });
    return undefined;
  }, [questionKey]);

  return (
    <div ref={page} className="relative min-h-screen bg-paper text-ink font-body overflow-hidden">
      <AmbientBackground className="z-0 opacity-60" />
      <div className="relative z-10">
      <AppHeader width="narrow" />

      <main className="max-w-3xl mx-auto px-6 md:px-10 py-10 space-y-8">
        <PageHeader
          eyebrow="Daily challenge"
          title="One question a day"
          description="Most days cover your skill gaps. Every third day explores a skill outside them. Some questions are multiple choice, and some ask you to type a short answer."
        >
          <label htmlFor="daily-role" className="font-mono text-xs uppercase tracking-widest text-ink-soft">Target role</label>
            <select id="daily-role" value={role} onChange={(e) => setRole(e.target.value)} className="rounded-xl border border-line px-4 py-2 bg-surface">
              {roles.map((r) => <option key={r} value={r}>{r}</option>)}
            </select>
        </PageHeader>

        {today?.remind_now && !today.answered && (
          <Appear className="rounded-xl border border-helix-teal/40 bg-helix-teal/5 px-5 py-4 text-sm">
            Today's question is still open. It takes about a minute.
          </Appear>
        )}

        {today && (
          <div className="grid grid-cols-3 gap-4">
            <Stat label="Streak">
              <Count value={today.streak} format={(n) => `${Math.round(n)} day${Math.round(n) === 1 ? "" : "s"}`} />
            </Stat>
            <Stat label="Points">
              <Count value={today.total_points} />
            </Stat>
            <Stat label="Today">{today.explore ? "Explore" : "Focus"}</Stat>
          </div>
        )}

        {error && <p className="text-signal-coral text-sm font-mono">{error}</p>}

        {today && (
          <section className="rounded-2xl border border-line bg-surface p-6 space-y-5">
            <p className="font-mono text-xs uppercase tracking-widest text-ink-soft">
              {today.date} · {today.challenge.skill}{today.explore ? " · exploration" : ""}{isText ? " · type your answer" : ""}
            </p>
            <h2 className="font-display text-xl font-medium"><RichText text={today.challenge.question} /></h2>

            {isText ? (
              <textarea
                aria-label="Your answer"
                value={result ? submittedText : text}
                onChange={(e) => setText(e.target.value)}
                disabled={!!result}
                rows={3}
                maxLength={500}
                placeholder="Type a short answer"
                className="w-full rounded-xl border border-line px-4 py-3 bg-surface focus:outline-none focus:border-helix-teal disabled:opacity-70"
              />
            ) : (
              <div className="space-y-3">
                {today.challenge.options.map((opt, i) => {
                  let style = "border-line hover:border-helix-teal";
                  if (result) {
                    if (i === result.correct_index) style = "border-helix-teal bg-helix-teal/10";
                    else if (i === result.your_index) style = "border-signal-coral bg-signal-coral/10";
                    else style = "border-line opacity-60";
                  } else if (choice === i) {
                    style = "border-helix-teal bg-helix-teal/5";
                  }
                  return (
                    <button
                      key={i}
                      data-option
                      type="button"
                      disabled={!!result}
                      onClick={() => setChoice(i)}
                      className={`w-full text-left rounded-xl border px-4 py-3 bg-surface transition-colors ${style}`}
                    >
                      {opt}
                    </button>
                  );
                })}
              </div>
            )}

            {!result && (
              <button
                type="button"
                onClick={submit}
                disabled={busy || (isText ? !text.trim() : choice === null)}
                className="font-display px-6 py-3 rounded-full bg-helix-teal text-paper disabled:opacity-40"
              >
                {busy ? "Saving…" : "Submit answer"}
              </button>
            )}

            {result && (
              <Appear y={10} className="rounded-xl bg-paper border border-line p-4 space-y-2">
                <p className={`font-display font-medium ${result.correct ? "text-helix-teal" : "text-signal-coral"}`}>
                  {result.correct ? `Correct · +${result.points} points` : "Not this time"}
                </p>
                {isText && result.accepted && (
                  <p className="text-xs text-ink-soft">
                    Accepted answers include: {result.accepted.join(", ")}. You needed {result.needed}.
                  </p>
                )}
                <p className="text-sm">{result.explanation}</p>
                <p className="text-xs text-ink-soft">Come back tomorrow for the next challenge.</p>
              </Appear>
            )}
          </section>
        )}

        <section className="rounded-2xl border border-line bg-surface p-6 space-y-4">
          <p className="font-display font-medium">Reminders</p>
          <label className="flex items-start gap-3 text-sm cursor-pointer">
            <input type="checkbox" className="mt-1" checked={emailOptIn} onChange={(e) => toggleEmail(e.target.checked)} />
            <span>Email me an evening reminder on days I have not answered yet. Off unless you turn it on.</span>
          </label>
          {notifyPermission === "default" && (
            <button type="button" onClick={enableBrowserReminders} className="text-sm text-helix-teal underline underline-offset-4">
              Allow browser notifications
            </button>
          )}
          {notifyPermission === "granted" && <p className="text-xs text-ink-soft">Browser notifications are on.</p>}
          {notifyPermission === "denied" && <p className="text-xs text-ink-soft">Browser notifications are blocked in your browser settings.</p>}
        </section>

        <HistoryPanel
          title="Last 30 days"
          subtitle={history ? `Streak ${history.streak} · ${history.total_points} points in total` : undefined}
          loading={!history}
          empty={history && history.days.length === 0 ? "No answers yet. Answer today's question to start your history." : null}
        >
          <ul className="divide-y divide-line text-sm">
            {history?.days.map((d) => (
              <li key={`${d.day}-${d.skill}`} className="py-2 flex justify-between gap-4">
                <span className="font-mono text-xs text-ink-soft">{d.day}</span>
                <span>{d.skill}</span>
                <span className={d.correct ? "text-helix-teal" : "text-signal-coral"}>{d.correct ? `+${d.points}` : "missed"}</span>
              </li>
            ))}
          </ul>
        </HistoryPanel>
      </main>
      </div>
    </div>
  );
}

function Stat({ label, children }) {
  return (
    <div className="rounded-2xl border border-line bg-surface p-4">
      <p className="font-mono text-xs uppercase tracking-widest text-ink-soft">{label}</p>
      <p className="font-display text-xl font-medium mt-1">{children}</p>
    </div>
  );
}

/**
 * A number that counts to its new value when it changes. The first render shows the
 * value straight away. Reduced motion: no counting.
 */
function Count({ value, format = (n) => String(Math.round(n)) }) {
  const ref = useRef(null);
  const shown = useRef(value);
  useLayoutEffect(() => {
    const el = ref.current;
    if (!el) return undefined;
    if (prefersReducedMotion() || shown.current === value) {
      el.textContent = format(value);
      shown.current = value;
      return undefined;
    }
    const obj = { v: shown.current };
    const tween = gsap.to(obj, {
      v: value,
      duration: 0.8,
      ease: "power2.out",
      onUpdate: () => {
        shown.current = obj.v;
        el.textContent = format(obj.v);
      },
    });
    return () => tween.kill();
    // format is a stable inline helper per render; the count depends only on value.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [value]);
  return <span ref={ref}>{format(value)}</span>;
}
