import { useCallback, useMemo, useRef, useState } from "react";
import { ToastContext } from "./ToastContext";

const TONE = {
  success: "border-helix-teal/50 text-helix-teal",
  error: "border-signal-coral/60 text-signal-coral",
  info: "border-line text-ink",
};

/** Shows short, dismissing messages in the corner. Use useToast().show(message, tone). */
export function ToastProvider({ children }) {
  const [toasts, setToasts] = useState([]);
  const nextId = useRef(1);

  const dismiss = useCallback((id) => setToasts((list) => list.filter((t) => t.id !== id)), []);

  const show = useCallback((message, tone = "info") => {
    const id = nextId.current++;
    setToasts((list) => [...list.slice(-2), { id, message, tone }]);
    window.setTimeout(() => dismiss(id), 4200);
  }, [dismiss]);

  const value = useMemo(() => ({ show, dismiss }), [show, dismiss]);

  return (
    <ToastContext.Provider value={value}>
      {children}
      <div aria-live="polite" className="pointer-events-none fixed bottom-5 right-5 z-[60] flex w-[min(360px,calc(100vw-2.5rem))] flex-col gap-2">
        {toasts.map((t) => (
          <div
            key={t.id}
            role={t.tone === "error" ? "alert" : "status"}
            className={`pointer-events-auto flex items-start justify-between gap-3 rounded-xl border bg-surface px-4 py-3 text-sm shadow-lg ${TONE[t.tone]}`}
          >
            <span>{t.message}</span>
            <button type="button" aria-label="Dismiss" onClick={() => dismiss(t.id)} className="text-ink-soft hover:text-ink">
              ×
            </button>
          </div>
        ))}
      </div>
    </ToastContext.Provider>
  );
}
