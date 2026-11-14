import { useEffect, useState } from "react";
import { api } from "../lib/api";
import Button from "../ui/Button";
import Card from "../ui/Card";
import { SkeletonLines } from "../ui/Skeleton";
import RichText from "../ui/RichText";

/**
 * The test that opens the next phase. Questions come from the server without answers,
 * and the server grades them. A pass (60% or more) unlocks the next phase.
 */
export default function PhaseTest({ index, role, mode = "gap", onPassed }) {
  const [data, setData] = useState(null);
  const [answers, setAnswers] = useState({});
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    let cancelled = false;
    api.planPhaseTest(index, role, mode)
      .then((d) => { if (!cancelled) setData(d); })
      .catch((e) => { if (!cancelled) setError(e.message || "The test could not be loaded."); });
    return () => { cancelled = true; };
  }, [index, role, mode]);

  async function submit() {
    setBusy(true);
    setError(null);
    try {
      const r = await api.planPhaseSubmit(index, role, answers, mode);
      setResult(r);
      if (r.passed) onPassed?.(r);
    } catch (e) {
      setError(e.message || "Could not submit the test.");
    } finally {
      setBusy(false);
    }
  }

  if (error && !data) return <p className="text-sm text-signal-coral">{error}</p>;
  if (!data) return <SkeletonLines lines={4} />;

  const allAnswered = data.questions.every((q) => answers[q.id] !== undefined);

  return (
    <Card className="space-y-5" aria-label={`Phase ${index + 1} test`}>
      <div>
        <p className="font-display text-lg font-medium">Phase {index + 1} test</p>
        <p className="mt-1 text-sm text-ink-soft">
          Answer all {data.questions.length} questions. You need {data.pass_score}% to unlock the next phase.
          You can retake it.
        </p>
      </div>

      {data.questions.map((q, qi) => (
        <fieldset key={q.id} className="space-y-2">
          <legend className="text-sm font-medium">
            {qi + 1}. <RichText text={q.question} />
          </legend>
          {q.options.map((opt, oi) => (
            <label
              key={oi}
              className={`flex cursor-pointer items-center gap-3 rounded-xl border px-4 py-2.5 text-sm transition-colors ${
                answers[q.id] === oi ? "border-helix-teal bg-helix-teal/10" : "border-line hover:border-helix-teal/60"
              }`}
            >
              <input
                type="radio"
                name={`phase-${index}-${q.id}`}
                checked={answers[q.id] === oi}
                onChange={() => setAnswers((a) => ({ ...a, [q.id]: oi }))}
                disabled={!!result?.passed}
              />
              {opt}
            </label>
          ))}
        </fieldset>
      ))}

      {error && <p className="text-sm text-signal-coral">{error}</p>}

      {result && (
        <div
          role="status"
          className={`rounded-xl border px-4 py-3 text-sm ${result.passed ? "border-helix-teal/50 text-helix-teal" : "border-signal-coral/50 text-signal-coral"}`}
        >
          {result.passed
            ? `Passed with ${result.score}%. ${result.unlocked_next ? "The next phase is now open." : ""}`
            : `You scored ${result.score}%. You need ${data.pass_score}% to pass. Review the notes and try again.`}
        </div>
      )}

      {!result?.passed && (
        <Button variant="primary" onClick={submit} disabled={!allAnswered || busy}>
          {busy ? "Marking…" : "Submit test"}
        </Button>
      )}
    </Card>
  );
}
