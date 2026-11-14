import { useEffect, useRef, useState } from "react";
import { api } from "../lib/api";

/*
 * A round help button in the bottom-right corner. Opens a small chat for questions about the app.
 * It is hidden during a timed exam (body[data-focus-mode]) so it never distracts from the test.
 */
const GREETING = { who: "bot", text: "Hi, I'm your SkillDNA assistant. Ask me anything about the app, or use a shortcut below. Shortcuts use your progress when you have allowed it in your profile." };

// One-tap actions for the signed-in user: the assistant reads the plan and scores, not documents.
const ACTIONS = [
  { label: "What's next?", action: "next" },
  { label: "Plan my week", action: "week" },
  { label: "How am I doing?", action: "progress" },
];

export default function HelpBot() {
  const [open, setOpen] = useState(false);
  const [messages, setMessages] = useState([GREETING]);
  const [text, setText] = useState("");
  const [busy, setBusy] = useState(false);
  const [suggestions, setSuggestions] = useState([]);
  const endRef = useRef(null);

  useEffect(() => {
    endRef.current?.scrollIntoView?.({ behavior: "smooth", block: "end" });
  }, [messages, open]);

  async function runAction(item) {
    if (busy) return;
    setMessages((m) => [...m, { who: "me", text: item.label }]);
    setBusy(true);
    try {
      const r = await api.assistantAction(item.action);
      const schedule = r.data?.schedule;
      setMessages((m) => [...m, { who: "bot", text: r.reply, schedule }]);
    } catch (e) {
      setMessages((m) => [...m, { who: "bot", text: e.message || "That shortcut is not available right now." }]);
    } finally {
      setBusy(false);
    }
  }

  async function send(message) {
    const clean = (message || "").trim();
    if (!clean || busy) return;
    const history = messages.filter((m) => m.who !== "bot" || m !== GREETING).map((m) => ({
      role: m.who === "me" ? "user" : "assistant",
      content: m.text,
    }));
    setMessages((m) => [...m, { who: "me", text: clean }]);
    setText("");
    setBusy(true);
    try {
      const r = await api.assistantChat(clean, history.slice(-6));
      setMessages((m) => [...m, { who: "bot", text: r.reply }]);
      setSuggestions(r.suggestions || []);
    } catch {
      setMessages((m) => [...m, { who: "bot", text: "I could not reach the helper just now. Try again in a moment." }]);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="helpbot fixed bottom-5 left-5 z-50 flex flex-col items-start gap-3 md:left-auto md:right-5">
      {open && (
        <section
          aria-label="SkillDNA helper"
          className="flex h-[460px] w-[min(340px,calc(100vw-2.5rem))] flex-col overflow-hidden rounded-2xl border border-line bg-surface shadow-2xl"
        >
          <header className="flex items-center justify-between border-b border-line bg-paper-dim/60 px-4 py-3">
            <div className="flex items-center gap-2">
              <span className="h-2 w-2 rounded-full bg-helix-teal" />
              <p className="font-display text-sm font-medium">SkillDNA helper</p>
            </div>
            <button type="button" aria-label="Close helper" onClick={() => setOpen(false)} className="text-ink-soft hover:text-ink">×</button>
          </header>

          <div className="flex-1 space-y-3 overflow-y-auto p-4 text-sm" aria-live="polite">
            {messages.map((m, i) => (
              <div key={i} className={`flex ${m.who === "me" ? "justify-end" : "justify-start"}`}>
                <div className={`max-w-[85%] rounded-2xl px-3.5 py-2 leading-relaxed ${m.who === "me" ? "bg-ink text-paper" : "bg-paper-dim"}`}>
                  <p>{m.text}</p>
                  {m.schedule && (
                    <ol className="mt-2 space-y-1.5 text-xs">
                      {m.schedule.filter((d) => d.tasks.length).slice(0, 7).map((d) => (
                        <li key={d.day}>
                          <span className="font-mono text-ink-soft">{d.day}</span>{" "}
                          {d.tasks.map((t) => t.skill).join(", ")}
                        </li>
                      ))}
                    </ol>
                  )}
                </div>
              </div>
            ))}
            {busy && <p className="font-mono text-xs text-ink-soft">typing…</p>}
            <div ref={endRef} />
          </div>

          <div className="flex flex-wrap gap-2 px-4 pb-2">
            {ACTIONS.map((item) => (
              <button key={item.action} type="button" onClick={() => runAction(item)} disabled={busy}
                className="rounded-full bg-helix-teal/10 px-3 py-1 text-xs font-medium text-helix-teal hover:bg-helix-teal/20 disabled:opacity-40">
                {item.label}
              </button>
            ))}
          </div>

          {suggestions.length > 0 && messages.length < 5 && (
            <div className="flex flex-wrap gap-2 px-4 pb-2">
              {suggestions.map((s) => (
                <button key={s} type="button" onClick={() => send(s)}
                  className="rounded-full border border-line px-3 py-1 text-xs hover:border-helix-teal hover:text-helix-teal">
                  {s}
                </button>
              ))}
            </div>
          )}

          <form className="flex gap-2 border-t border-line p-3" onSubmit={(e) => { e.preventDefault(); send(text); }}>
            <input
              value={text}
              onChange={(e) => setText(e.target.value.slice(0, 800))}
              aria-label="Ask the helper"
              placeholder="Ask about the app…"
              className="min-w-0 flex-1 rounded-full border border-line bg-surface px-4 py-2 text-sm focus:border-helix-teal focus:outline-none"
            />
            <button type="submit" disabled={busy || !text.trim()}
              className="rounded-full bg-ink px-4 py-2 font-display text-sm text-paper disabled:opacity-40">
              Send
            </button>
          </form>
        </section>
      )}

      <button
        type="button"
        aria-label={open ? "Close the SkillDNA helper" : "Open the SkillDNA helper"}
        aria-expanded={open}
        onClick={() => setOpen((o) => !o)}
        className="flex h-14 w-14 items-center justify-center rounded-full bg-helix-teal text-paper shadow-xl transition-transform duration-200 hover:scale-105 focus-visible:outline-helix-teal"
      >
        {open ? "×" : (
          <svg viewBox="0 0 24 24" width="22" height="22" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" aria-hidden="true">
            <path d="M21 12a8 8 0 0 1-11.6 7.1L4 20l1-4.6A8 8 0 1 1 21 12Z" />
          </svg>
        )}
      </button>
    </div>
  );
}
