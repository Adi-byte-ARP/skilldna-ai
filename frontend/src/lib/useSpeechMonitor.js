import { useEffect, useRef } from "react";

/*
 * Listens to the exam's microphone and reports sustained talking. Speech rises and falls in
 * syllables, so its level varies a lot from one moment to the next. A steady tone, a fan or
 * background hum does not. A short noise (a cough, a key) does not last long enough to count.
 */
export const WINDOW_SIZE = 12;        // readings in the sliding window
export const READ_EVERY_MS = 100;     // one reading every 100 ms, so the window spans 1.2 s
export const MIN_LEVEL = 0.02;        // quieter than this is silence
export const MIN_VARIATION = 0.35;    // spread of the level relative to its average
export const SUSTAIN_MS = 1500;       // talking must last this long to count
export const COOLDOWN_MS = 8000;      // at most one report per this interval

export function isSpeechPattern(levels) {
  if (levels.length < WINDOW_SIZE) return false;
  const mean = levels.reduce((a, b) => a + b, 0) / levels.length;
  if (mean < MIN_LEVEL) return false;
  const variance = levels.reduce((a, b) => a + (b - mean) ** 2, 0) / levels.length;
  return Math.sqrt(variance) / mean >= MIN_VARIATION;
}

export default function useSpeechMonitor({ stream, enabled, onSpeech }) {
  const callback = useRef(onSpeech);
  useEffect(() => { callback.current = onSpeech; }, [onSpeech]);

  useEffect(() => {
    if (!enabled || typeof stream?.getAudioTracks !== "function" || stream.getAudioTracks().length === 0) return undefined;
    const Ctx = globalThis.AudioContext || globalThis.webkitAudioContext;
    if (!Ctx) return undefined;

    const ctx = new Ctx();
    const source = ctx.createMediaStreamSource(new MediaStream(stream.getAudioTracks()));
    const analyser = ctx.createAnalyser();
    analyser.fftSize = 1024;
    source.connect(analyser);
    const buffer = new Float32Array(analyser.fftSize);
    const levels = [];
    let speakingSince = null;
    let lastReported = 0;

    const timer = setInterval(() => {
      analyser.getFloatTimeDomainData(buffer);
      let sum = 0;
      for (const v of buffer) sum += v * v;
      levels.push(Math.sqrt(sum / buffer.length));
      if (levels.length > WINDOW_SIZE) levels.shift();

      const now = Date.now();
      if (isSpeechPattern(levels)) {
        if (speakingSince === null) speakingSince = now;
        if (now - speakingSince >= SUSTAIN_MS && now - lastReported >= COOLDOWN_MS) {
          lastReported = now;
          callback.current?.();
        }
      } else {
        speakingSince = null;
      }
    }, READ_EVERY_MS);

    return () => {
      clearInterval(timer);
      source.disconnect();
      ctx.close?.();
    };
  }, [enabled, stream]);
}
