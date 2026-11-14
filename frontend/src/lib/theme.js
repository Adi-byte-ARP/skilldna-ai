import { useSyncExternalStore } from "react";

/*
 * Theme preference: "light", "dark", or "system" (follow the operating system).
 * The resolved value is written to <html data-theme>, which the CSS tokens key off.
 * The stored choice lives in localStorage, and a small script in main.jsx applies it
 * before the first paint, so the page never flashes the wrong colours.
 */

export const THEME_KEY = "skilldna-theme";
const listeners = new Set();

function systemPrefersDark() {
  return typeof window !== "undefined" && !!window.matchMedia?.("(prefers-color-scheme: dark)").matches;
}

export function readPreference() {
  try {
    const value = localStorage.getItem(THEME_KEY);
    return value === "light" || value === "dark" ? value : "system";
  } catch {
    return "system";
  }
}

export function resolveTheme(preference) {
  if (preference === "light" || preference === "dark") return preference;
  return systemPrefersDark() ? "dark" : "light";
}

export function applyTheme(preference = readPreference(), { animate = false } = {}) {
  const root = document.documentElement;
  if (animate) {
    root.classList.add("theme-transition");
    window.setTimeout(() => root.classList.remove("theme-transition"), 450);
  }
  root.setAttribute("data-theme", resolveTheme(preference));
}

export function setPreference(preference) {
  try {
    if (preference === "system") localStorage.removeItem(THEME_KEY);
    else localStorage.setItem(THEME_KEY, preference);
  } catch {
    /* private mode: the choice still applies for this visit */
  }
  applyTheme(preference, { animate: true });
  listeners.forEach((fn) => fn());
}

export function initTheme() {
  applyTheme(readPreference());
  // When the preference is "system", follow the OS if it changes during the visit.
  window.matchMedia?.("(prefers-color-scheme: dark)").addEventListener?.("change", () => {
    if (readPreference() === "system") applyTheme("system");
  });
}

function subscribe(fn) {
  listeners.add(fn);
  return () => listeners.delete(fn);
}

/** The user's preference ("light" | "dark" | "system"), kept in sync across the page. */
export function useThemePreference() {
  return useSyncExternalStore(subscribe, readPreference, () => "system");
}
