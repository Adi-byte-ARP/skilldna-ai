/*
 * Phones and tablets cannot run the proctored mock test: their cameras, screens and multitasking
 * cannot be monitored. A device is treated as mobile when its browser says so, or when its only
 * pointer is a touch screen.
 */
export function isMobileDevice(nav = globalThis.navigator, win = globalThis.window) {
  if (!nav) return false;
  if (/Android|iPhone|iPad|iPod|Mobile|Tablet|Silk|Kindle/i.test(nav.userAgent || "")) return true;
  const matches = (q) => Boolean(win?.matchMedia && win.matchMedia(q).matches);
  return matches("(pointer: coarse)") && !matches("(pointer: fine)");
}
