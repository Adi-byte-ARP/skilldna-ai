import { useEffect, useRef, useState } from "react";
import { api } from "../lib/api";
import Panel from "../ui/Panel";
import Button from "../ui/Button";
import Badge from "../ui/Badge";
import { SkeletonLines } from "../ui/Skeleton";
import RichText from "../ui/RichText";
import { plainText } from "../lib/plainText";

/*
 * The AI interview, as three stages: check your set-up, answer one question at a time, then read
 * a scorecard. Answers can be spoken (with a live transcript) or typed. The server records browser
 * signals while the interview runs and ends it automatically if they add up.
 */
const ANSWER_SECONDS = 90;
const SpeechRecognitionApi = typeof window !== "undefined" ? window.SpeechRecognition || window.webkitSpeechRecognition : null;

const toneText = (s) => (s >= 70 ? "text-helix-teal" : s >= 45 ? "text-helix-violet" : "text-signal-coral");
const toneBar = (s) => (s >= 70 ? "bg-helix-teal" : s >= 45 ? "bg-helix-violet" : "bg-signal-coral");

function ScoreRing({ value }) {
  const radius = 46;
  const circumference = 2 * Math.PI * radius;
  const clamped = Math.max(0, Math.min(100, value));
  return (
    <svg viewBox="0 0 120 120" className="h-36 w-36 shrink-0" role="img" aria-label={`Overall score ${Math.round(clamped)} out of 100`}>
      <circle cx="60" cy="60" r={radius} fill="none" stroke="currentColor" strokeOpacity="0.12" strokeWidth="10" className="text-ink" />
      <circle cx="60" cy="60" r={radius} fill="none" stroke="currentColor" strokeWidth="10" strokeLinecap="round"
        strokeDasharray={circumference} strokeDashoffset={circumference * (1 - clamped / 100)}
        transform="rotate(-90 60 60)" className={toneText(clamped)} />
      <text x="60" y="68" textAnchor="middle" className="fill-current font-display text-[28px] text-ink">{Math.round(clamped)}</text>
    </svg>
  );
}

function Step({ index, title, detail, done }) {
  return (
    <li className="flex items-start gap-3">
      <span className={`mt-0.5 flex h-6 w-6 shrink-0 items-center justify-center rounded-full font-mono text-xs ${done ? "bg-helix-teal text-paper" : "border border-line text-ink-soft"}`}>
        {done ? "✓" : index}
      </span>
      <div>
        <p className="font-display text-sm font-medium">{title}</p>
        <p className="text-xs leading-relaxed text-ink-soft">{detail}</p>
      </div>
    </li>
  );
}

export default function AIInterview({ role, onExit, onStart }) {
  const [stage, setStage] = useState("precheck");
  const [session, setSession] = useState(null);
  const [answer, setAnswer] = useState("");
  const [busy, setBusy] = useState(false);
  const [starting, setStarting] = useState(false);
  const [error, setError] = useState(null);
  const [report, setReport] = useState(null);
  const [autoNotice, setAutoNotice] = useState(null);
  const [integrity, setIntegrity] = useState({ points: 0, flags: [] });
  const [transcript, setTranscript] = useState([]);
  const [feedback, setFeedback] = useState(null);
  const [secondsLeft, setSecondsLeft] = useState(ANSWER_SECONDS);
  const [listening, setListening] = useState(false);
  const [mic, setMic] = useState({ state: "checking", level: 0 });

  const shownAt = useRef(Date.now());
  const answerRef = useRef("");
  const recognition = useRef(null);
  const baseText = useRef("");
  const submitRef = useRef(null);

  const current = session?.current_question;
  const total = session?.target_turns || 5;
  const done = session?.turns?.length ?? 0;
  const progress = Math.min(100, Math.round((done / total) * 100));
  useEffect(() => { answerRef.current = answer; }, [answer]);

  // Stage 1: a live microphone meter, so the candidate can see that the microphone works.
  useEffect(() => {
    if (stage !== "precheck") return undefined;
    let stream = null;
    let context = null;
    let frame = 0;
    let cancelled = false;
    const media = typeof navigator !== "undefined" ? navigator.mediaDevices : null;
    if (!media?.getUserMedia) {
      setMic({ state: "unavailable", level: 0 });
      return undefined;
    }
    media.getUserMedia({ audio: true }).then((s) => {
      if (cancelled) { s.getTracks().forEach((t) => t.stop()); return; }
      stream = s;
      const Ctx = window.AudioContext || window.webkitAudioContext;
      setMic({ state: "ready", level: 0 });
      if (!Ctx) return;
      context = new Ctx();
      const analyser = context.createAnalyser();
      analyser.fftSize = 512;
      context.createMediaStreamSource(s).connect(analyser);
      const buffer = new Uint8Array(analyser.frequencyBinCount);
      const tick = () => {
        analyser.getByteTimeDomainData(buffer);
        let peak = 0;
        for (const v of buffer) peak = Math.max(peak, Math.abs(v - 128));
        setMic({ state: "ready", level: Math.min(100, Math.round((peak / 128) * 100)) });
        frame = requestAnimationFrame(tick);
      };
      tick();
    }).catch(() => { if (!cancelled) setMic({ state: "denied", level: 0 }); });
    return () => {
      cancelled = true;
      cancelAnimationFrame(frame);
      stream?.getTracks().forEach((t) => t.stop());
      context?.close?.();
    };
  }, [stage]);

  // Browser signals during the interview. Leaving the tab, leaving the window, and paste/copy/cut
  // attempts are reported; the server decides whether they end the interview.
  function signal(type) {
    if (!session || report) return;
    api.interviewEvent?.(session.id, type)
      .then((r) => {
        setIntegrity({ points: r.integrity.points, flags: r.integrity.flags });
        if (r.auto_submitted) finishAutomatically(r);
      })
      .catch(() => {});
  }

  useEffect(() => {
    if (stage !== "room" || !session || report) return undefined;
    const onVisibility = () => { if (document.hidden) signal("tab_hidden"); };
    const onBlur = () => signal("window_blur");
    document.addEventListener("visibilitychange", onVisibility);
    window.addEventListener("blur", onBlur);
    return () => {
      document.removeEventListener("visibilitychange", onVisibility);
      window.removeEventListener("blur", onBlur);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [stage, session, report]);

  // The clock for each answer. It starts when the question appears and sends the answer at zero.
  useEffect(() => {
    if (stage !== "room" || !current || report) return undefined;
    setSecondsLeft(ANSWER_SECONDS);
    shownAt.current = Date.now();
    const id = setInterval(() => setSecondsLeft((s) => s - 1), 1000);
    return () => clearInterval(id);
  }, [stage, current?.question, report]); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    if (stage === "room" && current && !report && !busy && secondsLeft <= 0) {
      submitRef.current?.(answerRef.current.trim() || "(no answer given in time)");
    }
  }, [secondsLeft, stage, current, report, busy]);

  function speak(text) {
    if (typeof window === "undefined" || !window.speechSynthesis || !text) return;
    window.speechSynthesis.cancel();
    window.speechSynthesis.speak(new SpeechSynthesisUtterance(text));
  }

  function toggleVoice() {
    if (listening) {
      recognition.current?.stop();
      setListening(false);
      return;
    }
    if (!SpeechRecognitionApi) {
      setError("Voice answers need Chrome or Edge. You can type your answer instead.");
      return;
    }
    const rec = new SpeechRecognitionApi();
    rec.continuous = true;
    rec.interimResults = true;
    rec.lang = navigator.language || "en-IN";
    baseText.current = answerRef.current ? `${answerRef.current.trimEnd()} ` : "";
    rec.onresult = (event) => {
      let finalText = "";
      let interim = "";
      for (let i = 0; i < event.results.length; i += 1) {
        const piece = event.results[i][0].transcript;
        if (event.results[i].isFinal) finalText += piece;
        else interim += piece;
      }
      setAnswer(baseText.current + finalText + interim);
    };
    rec.onerror = () => setListening(false);
    rec.onend = () => setListening(false);
    recognition.current = rec;
    rec.start();
    setListening(true);
  }

  async function start() {
    setStarting(true);
    setError(null);
    try {
      onStart?.();
      const s = await api.interviewStart(role);
      setSession(s);
      setIntegrity(s.integrity || { points: 0, flags: [] });
      setTranscript([{ who: "ai", text: s.current_question?.question }]);
      setStage("room");
    } catch (e) {
      setError(e.message || "Could not start the interview.");
    } finally {
      setStarting(false);
    }
  }

  function finishAutomatically(r) {
    setAutoNotice(r.integrity.flags.map((f) => f.label).join(", ") || "Signals of outside help");
    setReport(r.report || null);
    setStage("report");
    setSession((prev) => ({ ...prev, ...r }));
  }

  async function submitAnswer(text) {
    if (!session || busy || report) return;
    setBusy(true);
    setError(null);
    recognition.current?.stop();
    setListening(false);
    const seconds = (Date.now() - shownAt.current) / 1000;
    const spoken = text.trim();
    try {
      const r = await api.interviewAnswer(session.id, spoken, seconds);
      setIntegrity({ points: r.integrity.points, flags: r.integrity.flags });
      const lastScore = r.turns?.length ? r.turns[r.turns.length - 1].score : null;
      setFeedback(r.feedback ? { text: r.feedback, score: lastScore } : null);
      setTranscript((t) => [
        ...t,
        { who: "you", text: spoken },
        ...(r.feedback ? [{ who: "feedback", text: r.feedback }] : []),
        ...(!r.done && r.current_question ? [{ who: "ai", text: r.current_question.question }] : []),
      ]);
      setAnswer("");
      if (r.done) {
        if (r.auto_submitted) setAutoNotice(r.integrity.flags.map((f) => f.label).join(", ") || "Signals of outside help");
        setReport(r.report);
        setStage("report");
      }
      setSession((prev) => ({ ...prev, ...r }));
    } catch (e) {
      setError(e.message || "Could not send your answer.");
    } finally {
      setBusy(false);
    }
  }
  submitRef.current = (text) => submitAnswer(text);

  function restart() {
    setSession(null);
    setReport(null);
    setAutoNotice(null);
    setIntegrity({ points: 0, flags: [] });
    setTranscript([]);
    setFeedback(null);
    setAnswer("");
    setStage("precheck");
  }

  const guard = (e) => { e.preventDefault(); signal("paste"); };

  if (stage === "precheck") {
    const micOk = mic.state === "ready";
    return (
      <Panel eyebrow="Before you begin" title={`${role} interview`}
        description="Five questions, one at a time. Answer by voice or by typing. Each answer has 90 seconds.">
        <div className="grid gap-6 md:grid-cols-[1fr_1fr]">
          <ol className="space-y-4">
            <Step index={1} title="Check your microphone" done={micOk}
              detail={mic.state === "denied" ? "Access was refused. Allow the microphone in your browser, or type your answers."
                : mic.state === "unavailable" ? "This browser cannot use the microphone here. Type your answers."
                : "Speak and watch the meter move. It should rise and fall with your voice."} />
            <Step index={2} title="Voice or typing" done={Boolean(SpeechRecognitionApi)}
              detail={SpeechRecognitionApi ? "Speak your answer and it appears as text. You can edit it before sending."
                : "Voice answers need Chrome or Edge. Typing works everywhere."} />
            <Step index={3} title="Stay in this window" done={false}
              detail="Leaving the tab, clicking away, or pasting an answer is recorded. Enough of these ends the interview automatically." />
          </ol>
          <div className="space-y-3 rounded-xl border border-line bg-paper-dim/50 p-5">
            <p className="font-mono text-[11px] uppercase tracking-widest text-ink-soft">Microphone level</p>
            <div className="h-3 overflow-hidden rounded-full bg-line" role="meter" aria-label="Microphone level"
              aria-valuemin={0} aria-valuemax={100} aria-valuenow={mic.level}>
              <div className="h-full rounded-full bg-helix-teal transition-[width] duration-100" style={{ width: `${mic.level}%` }} />
            </div>
            {mic.state === "checking" && <SkeletonLines lines={2} />}
          </div>
        </div>
        {error && <p role="alert" className="mt-5 text-sm text-signal-coral">{error}</p>}
        <div className="mt-8 flex items-center justify-between gap-4 border-t border-line pt-6">
          <p className="text-xs text-ink-soft">You can stop at any point. The report is still produced from the answers given.</p>
          <Button variant="ink" onClick={start} disabled={starting}>{starting ? "Starting…" : "Start interview"}</Button>
        </div>
      </Panel>
    );
  }

  if (stage === "report") {
    if (!report) {
      return (
        <Panel eyebrow="Interview report" title="Interview submitted">
          {autoNotice && <p role="alert" className="text-sm text-signal-coral">Submitted automatically: {autoNotice}.</p>}
        </Panel>
      );
    }
    return (
      <div className="space-y-6">
        {autoNotice && (
          <div role="alert" className="rounded-2xl border border-signal-coral/50 bg-signal-coral/5 px-5 py-4 text-sm text-signal-coral">
            <span className="font-display font-medium">Submitted automatically.</span> This interview showed signals that often come with outside help:
            <span className="mt-1 block font-medium">{autoNotice}.</span>
            The scores below cover only the answers given.
          </div>
        )}
        <Panel eyebrow="Interview report" title={`${role}`}>
          <div className="flex flex-col items-center gap-6 md:flex-row md:items-center">
            <ScoreRing value={report.overall} />
            <div className="min-w-0">
              <p className="font-display text-xl leading-snug">{report.verdict}</p>
              <p className="mt-2 text-sm text-ink-soft">{report.turns} answer{report.turns === 1 ? "" : "s"}, scored by the {report.engine} engine.</p>
            </div>
          </div>
        </Panel>

        {report.dimensions?.length > 0 && (
          <Panel eyebrow="Scorecard" title="How your answers were built">
            <ul className="space-y-5">
              {report.dimensions.map((d) => (
                <li key={d.name}>
                  <div className="flex items-baseline justify-between gap-4">
                    <span className="font-display text-sm font-medium">{d.name}</span>
                    <span className={`font-mono text-sm tabular-nums ${toneText(d.score)}`}>{Math.round(d.score)}</span>
                  </div>
                  <div className="mt-2 h-2 overflow-hidden rounded-full bg-line">
                    <div className={`h-full rounded-full ${toneBar(d.score)} transition-[width] duration-700`} style={{ width: `${d.score}%` }} />
                  </div>
                  {d.advice && <p className="mt-2 text-xs leading-relaxed text-ink-soft">{d.advice}</p>}
                </li>
              ))}
            </ul>
          </Panel>
        )}

        <div className="grid gap-6 md:grid-cols-2">
          <Panel eyebrow="Keep" title="Strengths">
            {report.strengths?.length ? (
              <div className="flex flex-wrap gap-2">{report.strengths.map((s) => <Badge key={s} tone="teal">{s}</Badge>)}</div>
            ) : <p className="text-sm text-ink-soft">No skill was answered strongly yet.</p>}
          </Panel>
          <Panel eyebrow="Work on" title="Gaps">
            {report.gaps?.length ? (
              <div className="flex flex-wrap gap-2">{report.gaps.map((s) => <Badge key={s} tone="coral">{s}</Badge>)}</div>
            ) : <p className="text-sm text-ink-soft">No clear gap in the questions asked.</p>}
          </Panel>
        </div>

        <div className="flex flex-wrap items-center gap-3">
          <a href="#/app/plan" className="rounded-full bg-ink px-5 py-2.5 font-display text-sm font-medium text-paper transition-colors hover:bg-helix-teal">
            Practise in your plan
          </a>
          <Button variant="ghost" onClick={restart}>Take another interview</Button>
        </div>
      </div>
    );
  }

  // Stage 2: the interview room.
  const mmss = `${Math.floor(Math.max(0, secondsLeft) / 60)}:${String(Math.max(0, secondsLeft) % 60).padStart(2, "0")}`;
  return (
    <div className="grid gap-6 lg:grid-cols-[1fr_280px]">
      <div className="space-y-6">
        <Panel
          eyebrow={`Question ${Math.min(done + 1, total)} of ${total}`}
          action={<span className={`font-mono text-sm tabular-nums ${secondsLeft <= 15 ? "text-signal-coral" : "text-ink-soft"}`} aria-live="off">{mmss}</span>}
        >
          <div className="space-y-5">
            <div className="h-1 overflow-hidden rounded-full bg-line">
              <div className={`h-full transition-[width] duration-1000 ease-linear ${secondsLeft <= 15 ? "bg-signal-coral" : "bg-helix-teal"}`}
                style={{ width: `${Math.max(0, (secondsLeft / ANSWER_SECONDS) * 100)}%` }} />
            </div>
            {current ? (
              <>
                <div className="flex flex-wrap items-center gap-2">
                  <Badge tone="violet">{current.skill || "Introduction"}</Badge>
                  <button type="button" onClick={() => speak(plainText(current.question))}
                    className="rounded-full border border-line px-3 py-1 font-mono text-xs text-ink-soft transition-colors hover:text-ink">
                    Read aloud
                  </button>
                </div>
                <p className="font-display text-xl leading-snug"><RichText text={current.question} /></p>
              </>
            ) : <SkeletonLines lines={2} />}

            <div>
              <label htmlFor="interview-answer" className="sr-only">Your answer</label>
              <textarea
                id="interview-answer"
                aria-label="Your answer"
                rows={6}
                value={answer}
                onChange={(e) => setAnswer(e.target.value)}
                onPaste={guard}
                onCopy={(e) => { e.preventDefault(); signal("copy"); }}
                onCut={(e) => { e.preventDefault(); signal("cut"); }}
                disabled={busy}
                placeholder="Speak or type your answer. Describe what you did, why, and what happened."
                className="w-full resize-y rounded-xl border border-line bg-surface p-4 text-sm leading-relaxed focus:border-helix-teal focus:outline-none"
              />
            </div>

            <div className="flex flex-wrap items-center justify-between gap-3">
              <button type="button" onClick={toggleVoice} disabled={busy}
                className={`flex items-center gap-2 rounded-full border px-4 py-2 font-display text-sm transition-colors ${listening ? "border-signal-coral text-signal-coral" : "border-line text-ink hover:border-helix-teal"}`}>
                <span className={`h-2 w-2 rounded-full ${listening ? "animate-pulse bg-signal-coral" : "bg-ink-soft"}`} aria-hidden="true" />
                {listening ? "Stop recording" : "Speak answer"}
              </button>
              <Button variant="ink" onClick={() => submitAnswer(answer)} disabled={busy || !answer.trim()}>
                {busy ? "Sending…" : "Send answer"}
              </Button>
            </div>

            {error && <p role="alert" className="text-sm text-signal-coral">{error}</p>}
            {feedback && (
              <div className="rounded-xl border border-helix-teal/30 bg-helix-teal/5 p-4">
                <p className="font-mono text-[11px] uppercase tracking-widest text-helix-teal">
                  Feedback{feedback.score != null ? ` · ${Math.round(feedback.score)}/100` : ""}
                </p>
                <p className="mt-1 text-sm leading-relaxed">{feedback.text}</p>
              </div>
            )}
          </div>
        </Panel>
      </div>

      <aside className="space-y-6">
        <Panel eyebrow="Progress" title={`${done} of ${total} answered`}>
          <div className="h-2 overflow-hidden rounded-full bg-line">
            <div className="h-full rounded-full bg-helix-violet transition-[width] duration-500" style={{ width: `${progress}%` }} />
          </div>
          {integrity.points > 0 && (
            <p role="status" className="mt-4 text-xs leading-relaxed text-signal-coral">
              Integrity {integrity.points}/5. {integrity.flags.map((f) => f.label).join(" · ")}. The interview ends automatically at 5.
            </p>
          )}
        </Panel>
        <Panel eyebrow="Transcript" title="This interview" label="Transcript">
          <ol className="max-h-[420px] space-y-3 overflow-y-auto pr-1 text-xs leading-relaxed">
            {transcript.map((item, i) => (
              <li key={i} className={item.who === "you" ? "text-ink" : item.who === "feedback" ? "text-helix-teal" : "text-ink-soft"}>
                <span className="font-mono text-[10px] uppercase tracking-widest">
                  {item.who === "ai" ? "Interviewer" : item.who === "you" ? "You" : "Feedback"}
                </span>
                <p className="mt-0.5">{item.text}</p>
              </li>
            ))}
          </ol>
        </Panel>
      </aside>
    </div>
  );
}
