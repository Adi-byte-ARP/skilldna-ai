import { useState, useRef, useLayoutEffect } from "react";
import { useNavigate, Link } from "react-router-dom";
import { motion, AnimatePresence } from "framer-motion";
import { gsap } from "../lib/gsapSetup";
import Helix from "../components/Helix";
import { useAuth } from "../context/AuthContext";

export default function Login() {
  const [mode, setMode] = useState("login"); // "login" | "register"
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState(null);
  const [submitting, setSubmitting] = useState(false);

  const { login, register } = useAuth();
  const navigate = useNavigate();
  const root = useRef(null);

  useLayoutEffect(() => {
    const ctx = gsap.context(() => {
      gsap.from("[data-login-panel]", {
        opacity: 0,
        y: 24,
        duration: 0.7,
        ease: "power3.out",
      });
      gsap.from("[data-login-helix]", {
        opacity: 0,
        scale: 0.88,
        duration: 0.9,
        ease: "back.out(1.5)",
        delay: 0.15,
      });
      gsap.to("[data-login-helix]", {
        y: -12,
        duration: 3.4,
        ease: "sine.inOut",
        repeat: -1,
        yoyo: true,
      });
    }, root);
    return () => ctx.revert();
  }, []);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      if (mode === "login") {
        await login(email.trim(), password);
      } else {
        await register(name.trim(), email.trim(), password);
      }
      navigate("/app");
    } catch (err) {
      if (err.message?.toLowerCase().includes("failed to fetch")) {
        setError("Can't reach the backend. Make sure it's running: uvicorn app.main:app --reload");
      } else {
        setError(err.message || "Something went wrong.");
      }
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div ref={root} className="min-h-screen bg-paper text-ink font-body grid lg:grid-cols-2">
      <div className="flex flex-col justify-between px-6 md:px-14 py-8 md:py-10">
        <Link to="/" className="font-display font-semibold text-lg tracking-tight flex items-center gap-2 w-fit">
          <span className="w-2.5 h-2.5 rounded-full bg-helix-teal inline-block" />
          SkillDNA<span className="text-helix-teal">.AI</span>
        </Link>

        <div data-login-panel className="max-w-sm mx-auto w-full">
          <p className="font-mono text-xs uppercase tracking-[0.2em] text-helix-teal mb-3">
            {mode === "login" ? "Welcome back" : "Get started"}
          </p>
          <h1 className="font-display text-3xl font-medium tracking-tight mb-2">
            {mode === "login" ? "Sign in to your sequence" : "Create your SkillDNA profile"}
          </h1>
          <p className="text-ink-soft text-sm mb-8">
            {mode === "login"
              ? "Pick up right where your evidence left off."
              : "One profile, cross-checked across everything you upload."}
          </p>

          <form onSubmit={handleSubmit} className="space-y-4">
            <AnimatePresence mode="popLayout">
              {mode === "register" && (
                <motion.div
                  key="name-field"
                  initial={{ opacity: 0, height: 0 }}
                  animate={{ opacity: 1, height: "auto" }}
                  exit={{ opacity: 0, height: 0 }}
                  transition={{ duration: 0.25, ease: "easeOut" }}
                  className="overflow-hidden"
                >
                  <label className="font-mono text-xs uppercase tracking-widest text-ink-soft">
                    Name
                  </label>
                  <input
                    required={mode === "register"}
                    value={name}
                    onChange={(e) => setName(e.target.value)}
                    className="w-full mt-1 rounded-xl border border-line px-4 py-3 focus:outline-none focus:border-helix-teal bg-white"
                    placeholder="Jane Dev"
                  />
                </motion.div>
              )}
            </AnimatePresence>

            <div>
              <label className="font-mono text-xs uppercase tracking-widest text-ink-soft">Email</label>
              <input
                required
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="w-full mt-1 rounded-xl border border-line px-4 py-3 focus:outline-none focus:border-helix-teal bg-white"
                placeholder="jane@example.com"
              />
            </div>

            <div>
              <label className="font-mono text-xs uppercase tracking-widest text-ink-soft">Password</label>
              <input
                required
                type="password"
                minLength={8}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="w-full mt-1 rounded-xl border border-line px-4 py-3 focus:outline-none focus:border-helix-teal bg-white"
                placeholder={mode === "register" ? "At least 8 characters" : "••••••••"}
              />
            </div>

            <button
              type="submit"
              disabled={submitting}
              className="w-full font-display font-medium py-3.5 rounded-full bg-helix-teal text-paper hover:bg-ink transition-colors duration-300 disabled:opacity-50"
            >
              {submitting
                ? mode === "login"
                  ? "Signing in…"
                  : "Creating profile…"
                : mode === "login"
                ? "Sign in"
                : "Create my profile"}
            </button>

            {error && <p className="text-signal-coral text-xs font-mono pt-1">{error}</p>}
          </form>

          <p className="text-ink-soft text-sm mt-6 text-center">
            {mode === "login" ? "New here?" : "Already have a profile?"}{" "}
            <button
              type="button"
              onClick={() => {
                setError(null);
                setMode(mode === "login" ? "register" : "login");
              }}
              className="text-helix-teal font-medium hover:underline underline-offset-4"
            >
              {mode === "login" ? "Create an account" : "Sign in instead"}
            </button>
          </p>
        </div>

        <p className="font-mono text-[11px] text-ink-soft">
          SkillDNA AI — Basaveshwar Engineering College Bagalkote, DISE, 22UIS717P
        </p>
      </div>

      <div className="hidden lg:flex bg-ink text-paper items-center justify-center relative overflow-hidden">
        <div className="grain absolute inset-0 opacity-40" />
        <div data-login-helix className="relative z-10 text-center">
          <Helix variant="hero" height={420} width={280} spin speed={0.5} />
          <p className="font-mono text-xs text-paper/60 mt-4 max-w-xs mx-auto leading-relaxed">
            Every skill starts as a claim. It becomes a strength once evidence
            from a second source confirms it.
          </p>
        </div>
      </div>
    </div>
  );
}
