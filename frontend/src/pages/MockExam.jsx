import { useCallback, useEffect, useRef, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { api } from "../lib/api";
import AppHeader from "../layout/AppHeader";
import Appear from "../components/Appear";
import HistoryPanel from "../components/HistoryPanel";
import AIInterview from "../components/AIInterview";
import PageHeader from "../ui/PageHeader";
import { isMobileDevice } from "../lib/device";
import useSpeechMonitor from "../lib/useSpeechMonitor";
import Button from "../ui/Button";
import Card from "../ui/Card";
import RichText from "../ui/RichText";

/*
 * Proctored mock exam. Phases:
 *   setup  -> pick kind and role, accept the rules
 *   camera -> camera must be on before the exam can start
 *   exam   -> fullscreen enforced; every violation is reported to the server
 *   result -> score, feedback and the violation log
 *
 * What the browser can and cannot enforce: fullscreen, tab and focus changes,
 * copy/paste and the right-click menu, blocked shortcuts, and the camera track
 * are all detected here and reported. The server decides termination (3rd
 * violation) and the deadline, so the browser cannot extend a session.
 * A browser cannot see a second device or a person in the room.
 */

const BLOCKED_KEYS = new Set(["c", "v", "x", "u", "s", "p"]);
export const TEST_SECONDS_PER_QUESTION = 60;

const FORMATS = [
  { value: "test", tag: "Proctored", title: "Mock test", desc: "Multiple choice, 60 seconds per question. No going back once you move on." },
  { value: "interview", tag: "Conversational", title: "AI interview", desc: "An AI interviewer asks, follows up on gaps, and ends with a report. 90 seconds per answer." },
];

const RULES = [
  "Use a laptop or desktop. Phones and tablets cannot take the proctored test.",
  "The test runs in fullscreen. Leaving it is recorded.",
  "Tab switches, clicks outside the window, copy, paste and blocked shortcuts are recorded.",
  "Your camera must stay on. Turning it off is recorded.",
  "Your microphone listens for talking or reading aloud. No audio is recorded or sent; only the fact that talking was heard.",
  "Each question has its own clock. When it runs out, the question is recorded and the test moves on.",
  "Once you move on, you cannot go back.",
  "Two violations end the session immediately and it is scored.",
  "Enough other signals, such as repeated talking, also end it. The result lists every signal.",
];
const BLUR_COALESCE_MS = 1500;

export default function MockExam() {
  const [phase, setPhase] = useState("setup");
  const [kind, setKind] = useState("test");
  const [role, setRole] = useState("Backend Engineer");
  const [options, setOptions] = useState(null);
  const [consents, setConsents] = useState({ fullscreen: false, monitored: false, alone: false });
  const [error, setError] = useState(null);
  const [busy, setBusy] = useState(false);
  const [session, setSession] = useState(null);
  // The exam's behaviour follows the session the server created, not the setup radio button.
  const mode = session?.kind || kind;
  const [qIndex, setQIndex] = useState(0);
  const [drafts, setDrafts] = useState({});
  const [picks, setPicks] = useState({});
  const [fullscreenOk, setFullscreenOk] = useState(true);
  const [now, setNow] = useState(Date.now());
  const [qLeft, setQLeft] = useState(0);

  const [sessions, setSessions] = useState({ loading: true, rows: [] });
  const navigate = useNavigate();

  // History is loaded when the setup or result screen is shown, never during the timed exam.
  useEffect(() => {
    if (phase !== "setup" && phase !== "result") return undefined;
    let cancelled = false;
    setSessions((prev) => ({ ...prev, loading: true }));
    api.mockSessions()
      .then((rows) => { if (!cancelled) setSessions({ loading: false, rows }); })
      .catch(() => { if (!cancelled) setSessions({ loading: false, rows: [] }); });
    return () => { cancelled = true; };
  }, [phase]);

  const streamRef = useRef(null);
  const videoRef = useRef(null);

  useEffect(() => {
    api.mockRoles().then(setOptions).catch(() => setError("Could not load exam options. Is the backend running?"));
  }, []);

  const stopCamera = useCallback(() => {
    streamRef.current?.getTracks().forEach((t) => t.stop());
    streamRef.current = null;
  }, []);

  const leaveFullscreen = useCallback(() => {
    if (document.fullscreenElement) document.exitFullscreen().catch(() => {});
  }, []);

  // Release the camera and fullscreen whenever the page is left.
  useEffect(() => () => { stopCamera(); leaveFullscreen(); }, [stopCamera, leaveFullscreen]);

  // The helper bubble is hidden during the exam, so nothing competes with the test.
  useEffect(() => {
    if (phase !== "exam") return undefined;
    document.body.dataset.focusMode = "exam";
    return () => { delete document.body.dataset.focusMode; };
  }, [phase]);

  // Attach the camera stream to the preview element once it exists.
  useEffect(() => {
    if (videoRef.current && streamRef.current) videoRef.current.srcObject = streamRef.current;
  });

  const consentsDone = consents.fullscreen && consents.monitored && consents.alone;

  async function enableCamera() {
    setError(null);
    if (isMobileDevice()) {
      setError("Take the mock test on a laptop or desktop. Phones and tablets cannot run the proctored test.");
      return;
    }
    try {
      streamRef.current?.getTracks().forEach((t) => t.stop());
      streamRef.current = await navigator.mediaDevices.getUserMedia({ video: true, audio: true });
      setPhase("camera");
      setTimeout(() => {
        if (videoRef.current && streamRef.current) videoRef.current.srcObject = streamRef.current;
      }, 0);
    } catch {
      setError("Camera and microphone access are required. The microphone lets the test notice talking during the exam.");
    }
  }

  async function beginExam() {
    setError(null);
    setBusy(true);
    try {
      // Must run inside the click that starts the exam, so the browser allows fullscreen.
      await document.documentElement.requestFullscreen();
    } catch {
      setBusy(false);
      setError("Fullscreen is required. Allow it and try again.");
      return;
    }
    try {
      const s = await api.mockStart(kind, role);
      setNow(Date.now());
      setSession(s);
      setQIndex(0);
      setDrafts({});
      setPicks({});
      setFullscreenOk(true);
      setPhase("exam");
    } catch (e) {
      leaveFullscreen();
      setError(e.message || "Could not start the session.");
    } finally {
      setBusy(false);
    }
  }

  // ---- monitoring: every event is sent to the server, which counts violations ----
  const sessionId = session?.id;
  const sessionStatus = session?.status;

  // Talking during the test (reading the questions aloud, or someone helping) is recorded as a signal.
  const onSpeechDetected = useCallback(() => {
    if (!sessionId) return;
    api.mockEvent(sessionId, "speech")
      .then((updated) => setSession((prev) => ({ ...prev, ...updated })))
      .catch(() => {});
  }, [sessionId]);
  useSpeechMonitor({
    stream: streamRef.current,
    enabled: phase === "exam" && sessionStatus === "active",
    onSpeech: onSpeechDetected,
  });

  useEffect(() => {
    if (phase !== "exam" || !sessionId) return;

    // One real action often fires several browser events (leaving fullscreen or
    // switching tabs also fires a window blur). A blur that arrives right after
    // another violation is the same action, so it is not counted twice.
    let lastReportAt = 0;
    const report = (type) => {
      const nowMs = Date.now();
      if (type === "window_blur" && nowMs - lastReportAt < BLUR_COALESCE_MS) return;
      lastReportAt = nowMs;
      api.mockEvent(sessionId, type)
        .then((updated) => setSession((prev) => ({ ...prev, ...updated })))
        .catch(() => {});
    };
    const onVisibility = () => { if (document.hidden) report("tab_hidden"); };
    const onBlur = () => report("window_blur");
    const onFullscreen = () => {
      if (!document.fullscreenElement) {
        setFullscreenOk(false);
        report("fullscreen_exit");
      } else {
        setFullscreenOk(true);
      }
    };
    const blockAndReport = (type) => (e) => { e.preventDefault(); report(type); };
    const onKey = (e) => {
      const key = e.key.toLowerCase();
      const modified = e.ctrlKey || e.metaKey;
      const devtools = e.key === "F12" || (modified && e.shiftKey && (key === "i" || key === "j"));
      if ((modified && BLOCKED_KEYS.has(key)) || devtools) {
        e.preventDefault();
        report("shortcut_blocked");
      }
    };
    const onUnload = (e) => { e.preventDefault(); e.returnValue = ""; };
    const onCopy = blockAndReport("copy");
    const onCut = blockAndReport("cut");
    const onPaste = blockAndReport("paste");
    const onContext = blockAndReport("context_menu");

    const track = streamRef.current?.getVideoTracks()[0];
    const onCameraEnded = () => report("camera_lost");

    document.addEventListener("visibilitychange", onVisibility);
    document.addEventListener("fullscreenchange", onFullscreen);
    document.addEventListener("copy", onCopy);
    document.addEventListener("cut", onCut);
    document.addEventListener("paste", onPaste);
    document.addEventListener("contextmenu", onContext);
    window.addEventListener("blur", onBlur);
    window.addEventListener("keydown", onKey, true);
    window.addEventListener("beforeunload", onUnload);
    track?.addEventListener("ended", onCameraEnded);

    return () => {
      document.removeEventListener("visibilitychange", onVisibility);
      document.removeEventListener("fullscreenchange", onFullscreen);
      document.removeEventListener("copy", onCopy);
      document.removeEventListener("cut", onCut);
      document.removeEventListener("paste", onPaste);
      document.removeEventListener("contextmenu", onContext);
      window.removeEventListener("blur", onBlur);
      window.removeEventListener("keydown", onKey, true);
      window.removeEventListener("beforeunload", onUnload);
      track?.removeEventListener("ended", onCameraEnded);
    };
  }, [phase, sessionId]);

  // Leave the exam screen as soon as the server says the session is over.
  useEffect(() => {
    if (phase === "exam" && sessionStatus && sessionStatus !== "active") {
      stopCamera();
      leaveFullscreen();
      setPhase("result");
    }
  }, [phase, sessionStatus, stopCamera, leaveFullscreen]);

  // ---- timers ----
  useEffect(() => {
    if (phase !== "exam") return;
    const t = setInterval(() => setNow(Date.now()), 1000);
    return () => clearInterval(t);
  }, [phase]);

  const remaining = session?.deadline_at
    ? Math.max(0, Math.floor((new Date(session.deadline_at).getTime() - now) / 1000))
    : 0;

  const questions = session?.questions || [];
  const current = questions[qIndex];
  const currentId = current?.id;
  const currentSeconds = current?.seconds || 0;

  const submitNow = useCallback(async () => {
    if (!sessionId) return;
    try {
      const s = await api.mockSubmit(sessionId);
      setSession((prev) => ({ ...prev, ...s }));
    } catch {
      /* server-side deadline still applies */
    }
  }, [sessionId]);

  // Overall time ran out on the client: ask the server to finalize.
  useEffect(() => {
    if (phase === "exam" && session?.status === "active" && remaining === 0 && session.deadline_at) {
      submitNow();
    }
  }, [phase, session, remaining, submitNow]);

  // Each question has its own clock. When it runs out the question is recorded as it stands
  // and the test moves on, so nobody can linger on a question.
  useEffect(() => {
    if (phase === "exam" && currentId) setQLeft(mode === "interview" ? currentSeconds : TEST_SECONDS_PER_QUESTION);
  }, [qIndex, phase, mode, currentId, currentSeconds]);

  useEffect(() => {
    if (phase !== "exam") return;
    const t = setInterval(() => setQLeft((v) => (v > 0 ? v - 1 : 0)), 1000);
    return () => clearInterval(t);
  }, [phase, mode, qIndex]);

  async function saveOpenAnswer() {
    if (!sessionId || !current || current.kind !== "open") return;
    const text = drafts[current.id] ?? "";
    try {
      const s = await api.mockAnswer(sessionId, current.id, text);
      setSession((prev) => ({ ...prev, ...s }));
    } catch {
      /* shown on next state refresh */
    }
  }

  // Strict test: moving on is final. There is no way back to an earlier question.
  async function advanceTest() {
    if (qIndex >= questions.length - 1) {
      await submitNow();
    } else {
      setQIndex((i) => i + 1);
    }
  }

  async function advanceInterview() {
    await saveOpenAnswer();
    if (qIndex >= questions.length - 1) {
      await submitNow();
    } else {
      setQIndex((i) => i + 1);
    }
  }

  // Interview: when a question's time runs out, its answer is saved and the next question opens.
  useEffect(() => {
    if (phase === "exam" && qLeft === 0 && current && session?.status === "active") {
      if (mode === "interview") advanceInterview();
      else advanceTest();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [qLeft]);

  async function chooseOption(index) {
    if (!sessionId || !current) return;
    setPicks((p) => ({ ...p, [current.id]: index }));
    try {
      const s = await api.mockAnswer(sessionId, current.id, index);
      setSession((prev) => ({ ...prev, ...s }));
    } catch (e) {
      setError(e.message);
    }
  }

  function returnToFullscreen() {
    document.documentElement
      .requestFullscreen()
      .then(() => setFullscreenOk(true))
      .catch(() => setError("Could not return to fullscreen. Click the button again."));
  }

  function reset() {
    setSession(null);
    setPhase("setup");
    setConsents({ fullscreen: false, monitored: false, alone: false });
    setError(null);
  }

  // ---------------- render ----------------

  if (phase === "setup") {
    const roles = options?.roles || ["Backend Engineer"];
    return (
      <Shell title="Mock test & interview" subtitle="Strict and timed. Choose a format and a role, then read the rules.">
        <div className="grid gap-8 lg:grid-cols-[1.35fr_1fr]">
          <div className="space-y-8">
            <section className="space-y-3">
              <p className="font-mono text-xs uppercase tracking-widest text-ink-soft">1 · Format</p>
              <div className="grid gap-3 sm:grid-cols-2">
                {FORMATS.map((f) => {
                  const active = kind === f.value;
                  return (
                    <button
                      key={f.value}
                      type="button"
                      aria-pressed={active}
                      onClick={() => setKind(f.value)}
                      className={`rounded-2xl border p-5 text-left transition-colors ${
                        active ? "border-helix-teal bg-helix-teal/10" : "border-line bg-surface hover:border-helix-teal/60"}`}
                    >
                      <span className="font-mono text-[11px] uppercase tracking-widest text-helix-teal">{f.tag}</span>
                      <span className="mt-2 block font-display text-lg font-medium">{f.title}</span>
                      <span className="mt-1 block text-sm text-ink-soft">{f.desc}</span>
                    </button>
                  );
                })}
              </div>
            </section>

            <section className="space-y-3">
              <p className="font-mono text-xs uppercase tracking-widest text-ink-soft">2 · Target role</p>
              <div className="grid gap-2 sm:grid-cols-2">
                {roles.map((r) => (
                  <button
                    key={r}
                    type="button"
                    aria-pressed={role === r}
                    onClick={() => setRole(r)}
                    className={`rounded-xl border px-4 py-3 text-left text-sm transition-colors ${
                      role === r ? "border-helix-violet bg-helix-violet/10 font-medium" : "border-line bg-surface hover:border-helix-violet/50"}`}
                  >
                    {r}
                  </button>
                ))}
              </div>
            </section>

            {kind === "interview" ? (
              <div className="fixed inset-0 z-[9999] w-screen h-screen bg-paper overflow-y-auto flex flex-col">
                <div className="flex items-center justify-between px-6 md:px-10 py-4 border-b border-line bg-surface">
                  <p className="font-display text-sm">AI Interview · {role}</p>
                  <button type="button" onClick={() => { leaveFullscreen(); setKind("test"); }} className="text-sm underline underline-offset-4 text-ink-soft">Exit interview</button>
                </div>
                <div className="flex-1 max-w-4xl mx-auto w-full px-6 md:px-10 py-8">
                  <AIInterview key={role} role={role} onExit={() => { leaveFullscreen(); setKind("test"); }}
                    onStart={() => { document.documentElement.requestFullscreen?.().catch(() => {}); }} />
                </div>
              </div>
            ) : (
              <section className="space-y-3">
                <p className="font-mono text-xs uppercase tracking-widest text-ink-soft">3 · Agree before you start</p>
                <div className="space-y-3">
                  <Consent checked={consents.fullscreen} onChange={(v) => setConsents((c) => ({ ...c, fullscreen: v }))}
                    text="I understand the test runs in fullscreen." />
                  <Consent checked={consents.monitored} onChange={(v) => setConsents((c) => ({ ...c, monitored: v }))}
                    text="I agree that these events, including talking heard by my microphone, are recorded and used for my result." />
                  <Consent checked={consents.alone} onChange={(v) => setConsents((c) => ({ ...c, alone: v }))}
                    text="I will work alone, without other people, notes, or a second device." />
                </div>
                {error && <p className="text-sm text-signal-coral">{error}</p>}
                <Button variant="primary" size="lg" disabled={!consentsDone || !options} onClick={enableCamera} className="w-full">
                  Continue to camera check
                </Button>
              </section>
            )}
          </div>

          <aside className="space-y-6">
            <Card>
              <p className="font-display text-base font-medium">The rules</p>
              <ol className="mt-4 space-y-3 text-sm">
                {RULES.map((rule, i) => (
                  <li key={rule} className="flex gap-3">
                    <span className="font-mono text-xs text-helix-teal">{String(i + 1).padStart(2, "0")}</span>
                    <span>{rule}</span>
                  </li>
                ))}
              </ol>
            </Card>
            <HistoryPanel
              title="Your sessions"
              subtitle="Past mock tests and interviews, newest first."
              loading={sessions.loading}
              empty={sessions.rows.length === 0 ? "No sessions yet. Your first result will appear here." : null}
            >
              <ul className="divide-y divide-line text-sm">
                {sessions.rows.slice(0, 20).map((row) => (
                  <li key={row.id} className="grid grid-cols-[6.5rem_1fr_auto] items-center gap-3 py-3">
                    <span className="font-mono text-xs text-ink-soft">{new Date(row.started_at).toLocaleDateString()}</span>
                    <span>
                      {row.kind === "test" ? "Mock test" : "Mock interview"} · {row.role}
                      <span className={`block text-xs ${row.violation_count ? "text-signal-coral" : "text-ink-soft"}`}>
                        {row.violation_count ? `${row.violation_count} violation${row.violation_count === 1 ? "" : "s"}` : "No violations"} · {row.status}
                      </span>
                    </span>
                    <span className="font-display text-right">{row.score != null ? `${Math.round(row.score)}/100` : "–"}</span>
                  </li>
                ))}
              </ul>
            </HistoryPanel>
          </aside>
        </div>
      </Shell>
    );
  }

  if (phase === "camera") {
    return (
      <Shell title="Camera check" subtitle="Your camera must be on for the whole session.">
        <div className="space-y-5">
          <video ref={videoRef} autoPlay muted playsInline className="w-full rounded-xl bg-ink aspect-video object-cover" />
          <p className="text-sm text-ink-soft">Make sure your face is visible and the room is well lit. Then start.</p>
          {error && <p className="text-signal-coral text-sm font-mono">{error}</p>}
          <button
            type="button"
            onClick={beginExam}
            disabled={busy}
            className="w-full font-display font-medium py-3.5 rounded-full bg-helix-teal text-paper hover:bg-ink transition-colors disabled:opacity-40"
          >
            {busy ? "Starting…" : "Start in fullscreen"}
          </button>
          <button type="button" onClick={() => { stopCamera(); setPhase("setup"); }} className="w-full text-sm text-ink-soft underline underline-offset-4">
            Cancel
          </button>
        </div>
      </Shell>
    );
  }

  if (phase === "exam" && session) {
    const warnings = session.violations?.length || 0;
    const max = session.max_violations || 3;
    const mins = String(Math.floor(remaining / 60)).padStart(2, "0");
    const secs = String(remaining % 60).padStart(2, "0");

    return (
      <div className="fixed inset-0 w-screen h-screen z-[9999] bg-paper text-ink font-body overflow-y-auto">
        <div className="flex items-center justify-between px-6 md:px-10 py-4 border-b border-line bg-surface">
          <p className="font-display text-sm">{mode === "test" ? "Mock test" : "Mock interview"} · {session.role}</p>
          <div className="flex items-center gap-5">
            <span className={`font-mono text-sm ${qLeft <= 10 ? "text-signal-coral" : ""}`}>Question: {qLeft}s</span>
            {session.integrity?.points > 0 && (
              <span className="font-mono text-xs text-signal-coral" role="status">
                Integrity {session.integrity.points}/{session.integrity.auto_submit_at}
              </span>
            )}
            <span className="font-mono text-sm">Total {mins}:{secs}</span>
            <video ref={videoRef} autoPlay muted playsInline className="w-20 h-14 rounded-lg bg-ink object-cover" />
          </div>
        </div>

        {warnings > 0 && (
          <div className="bg-signal-coral-soft border-b border-signal-coral/30 px-6 md:px-10 py-3 text-sm">
            Warning {warnings} of {max}. The next violation ends the session. Last: {session.violations[warnings - 1].label}.
          </div>
        )}

        <main className="max-w-4xl mx-auto px-6 md:px-10 py-10">
          {current && (
            <>
              <p className="font-mono text-xs uppercase tracking-widest text-ink-soft mb-3">
                Question {qIndex + 1} of {questions.length}
                {current.kind === "mcq" && current.skill ? ` · ${current.skill}` : ""}
              </p>
              <h2 className="font-display text-xl md:text-2xl font-medium mb-6"><RichText text={current.question} /></h2>

              {current.kind === "mcq" ? (
                <div className="space-y-3">
                  {current.options.map((opt, i) => {
                    const chosen = picks[current.id] === i;
                    return (
                      <button
                        key={i}
                        type="button"
                        onClick={() => chooseOption(i)}
                        className={`w-full text-left rounded-xl border px-4 py-3 bg-surface transition-colors ${chosen ? "border-helix-teal bg-helix-teal/5" : "border-line hover:border-helix-teal"}`}
                      >
                        {opt}
                      </button>
                    );
                  })}
                </div>
              ) : (
                <textarea
                  value={drafts[current.id] ?? ""}
                  onChange={(e) => setDrafts((d) => ({ ...d, [current.id]: e.target.value }))}
                  onBlur={saveOpenAnswer}
                  onPaste={(e) => e.preventDefault()}
                  rows={10}
                  placeholder="Type your answer. Speak clearly and give one concrete example."
                  className="w-full rounded-xl border border-line px-4 py-3 bg-surface focus:outline-none focus:border-helix-teal"
                />
              )}

              {error && <p className="text-signal-coral text-sm font-mono mt-4">{error}</p>}

              <div className="flex items-center justify-between mt-8">
                <p className="text-xs text-ink-soft">
                  {mode === "test" ? "Once you move on, you cannot go back." : "Your answer is recorded when you send it."}
                </p>

                {mode === "test" && qIndex < questions.length - 1 && (
                  <button type="button" onClick={advanceTest} className="font-display px-5 py-2.5 rounded-full bg-ink text-paper">
                    Lock answer and continue
                  </button>
                )}
                {mode === "test" && qIndex === questions.length - 1 && (
                  <button type="button" onClick={submitNow} className="font-display px-5 py-2.5 rounded-full bg-helix-teal text-paper">
                    Submit test
                  </button>
                )}
                {mode === "interview" && (
                  <button type="button" onClick={advanceInterview} className="font-display px-5 py-2.5 rounded-full bg-helix-teal text-paper">
                    {qIndex === questions.length - 1 ? "Submit interview" : "Next question"}
                  </button>
                )}
              </div>
            </>
          )}
        </main>

        {!fullscreenOk && (
          <div className="fixed inset-0 bg-ink/95 text-paper flex items-center justify-center p-6 z-50">
            <div className="max-w-sm text-center space-y-4">
              <p className="font-display text-xl">You left fullscreen</p>
              <p className="text-sm text-paper/70">This was recorded. Return to fullscreen to continue.</p>
              <button type="button" onClick={returnToFullscreen} className="font-display px-6 py-3 rounded-full bg-helix-teal text-paper">
                Return to fullscreen
              </button>
            </div>
          </div>
        )}
      </div>
    );
  }

  if (phase === "result" && session) {
    const r = session.result || {};
    const terminated = session.status === "terminated";
    return (
      <Shell
        title={terminated ? "Session ended" : "Result"}
        subtitle={terminated ? "The session was ended after too many violations and scored on what was answered." : "Your score and feedback."}
      >
        <div className="space-y-6">
          <div className="rounded-2xl border border-line bg-surface p-6">
            <p className="font-mono text-xs uppercase tracking-widest text-ink-soft">Score</p>
            <p className="font-display text-5xl font-medium mt-2">{r.score ?? 0}<span className="text-ink-soft text-2xl">/100</span></p>
            {mode === "test" && (
              <p className="text-sm text-ink-soft mt-2">{r.correct} of {r.total} correct</p>
            )}
            {r.note && <p className="text-xs text-ink-soft mt-3">{r.note}</p>}
          </div>

          {session.end_reason === "integrity" && (
            <div role="alert" className="rounded-2xl border border-signal-coral/50 bg-signal-coral/5 p-5 text-sm text-signal-coral">
              <p className="font-display font-medium">Submitted automatically</p>
              <p className="mt-1">The test showed signals that often come with outside help, so it was submitted at once. The score covers only what was answered.</p>
            </div>
          )}
          {session.integrity?.flags?.length > 0 && (
            <div className="rounded-2xl border border-line bg-surface p-6">
              <p className="font-display font-medium">Integrity check</p>
              <p className="mt-1 text-xs text-ink-soft">{session.integrity.points} of {session.integrity.auto_submit_at} points. Each signal is listed with the time it happened.</p>
              <ul className="mt-3 space-y-1.5 text-sm">
                {session.integrity.flags.map((f, i) => (
                  <li key={i} className="flex justify-between gap-4">
                    <span>{f.label}</span>
                    <span className="font-mono text-xs text-ink-soft">{f.at ? new Date(f.at).toLocaleTimeString() : ""}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}
          {r.feedback?.length > 0 && (
            <div className="rounded-2xl border border-line bg-surface p-6">
              <p className="font-display font-medium mb-3">Feedback</p>
              <ul className="list-disc pl-5 space-y-2 text-sm">
                {r.feedback.map((f, i) => <li key={i}>{f}</li>)}
              </ul>
            </div>
          )}

          <div className="rounded-2xl border border-line bg-surface p-6">
            <p className="font-display font-medium mb-3">Violations ({(session.violations || session.integrity?.flags || []).length})</p>
            {(session.violations || session.integrity?.flags || []).length > 0 ? (
              <ul className="space-y-2 text-sm">
                {(session.violations || session.integrity?.flags || []).map((v, i) => (
                  <li key={i} className="flex justify-between gap-4">
                    <span>{v.label || v.type}</span>
                    <span className="font-mono text-xs text-ink-soft">{v.at ? new Date(v.at).toLocaleTimeString() : ""}</span>
                  </li>
                ))}
              </ul>
            ) : (
              <p className="text-sm text-ink-soft">No violations recorded.</p>
            )}
            {session.integrity?.is_valid === false && (
              <p className="mt-3 text-sm font-medium text-signal-coral">Session integrity check failed.</p>
            )}
          </div>

          <div className="flex flex-wrap items-center gap-3 justify-between">
            <button type="button" onClick={reset} className="font-display px-5 py-2.5 rounded-full bg-ink text-paper">Take another</button>
            <div className="flex items-center gap-3">
              <Button variant="ghost" onClick={() => navigate(-1)}>Go Back</Button>
              <Link to="/app" className="text-sm underline underline-offset-4 text-ink-soft">Back to dashboard</Link>
            </div>
          </div>
        </div>
      </Shell>
    );
  }

  return <Shell title="Loading" />;
}

function Shell({ title, subtitle, children }) {
  return (
    <div className="min-h-screen bg-paper text-ink font-body">
      <AppHeader width="page" />
      <main className="max-w-4xl mx-auto px-6 md:px-10 py-10">
        {title && <div className="mb-8"><PageHeader eyebrow="Proctored practice" title={title} description={subtitle} /></div>}
        {/* Keyed by title, so each screen (setup, camera check, result) eases in on its own. */}
        <Appear key={title} y={12}>
          {children}
        </Appear>
      </main>
    </div>
  );
}

function Consent({ checked, onChange, text }) {
  return (
    <label className="flex items-start gap-3 cursor-pointer text-sm">
      <input type="checkbox" className="mt-1" checked={checked} onChange={(e) => onChange(e.target.checked)} />
      <span>{text}</span>
    </label>
  );
}
