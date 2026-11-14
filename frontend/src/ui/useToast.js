import { useContext } from "react";
import { ToastContext } from "./ToastContext";

/** Returns { show(message, tone), dismiss(id) }. Outside a provider it logs instead of failing. */
export function useToast() {
  const ctx = useContext(ToastContext);
  if (ctx) return ctx;
  return { show: (message) => console.info(message), dismiss: () => {} };
}
