import { useState, useRef, useLayoutEffect } from "react";
import { useNavigate, Link } from "react-router-dom";
import { motion, AnimatePresence } from "framer-motion";
import { gsap } from "../lib/gsapSetup";
import Helix from "../components/Helix";
import AmbientBackground from "../components/AmbientBackground";
import { checkFullName, checkGmail, passwordChecks } from "../lib/accountRules";
import { useAuth } from "../context/useAuth";

export default function Login() {
  const [mode, setMode] = useState("login"); // "login" | "register"
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
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

  // Each check gives a message when it fails. Registration needs all of them to pass.
  const gmailCheck = checkGmail(email);
  const nameCheck = checkFullName(name);
  const checks = passwordChecks(password, email);
  const passwordOk = checks.every((c) => c.ok);
  const confirmOk = confirm === password && confirm.length > 0;
  const registerValid = gmailCheck.ok && nameCheck.ok && passwordOk && confirmOk;
  const loginValid = gmailCheck.ok && password.length > 0;
  const formValid = mode === "login" ? loginValid : registerValid;

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError(null);
    if (mode === "register") {
      if (!nameCheck.ok) return setError(nameCheck.message);
      if (!gmailCheck.ok) return setError(gmailCheck.message);
      if (!passwordOk) return setError("Password needs " + checks.filter((c) => !c.ok).map((c) => c.label.toLowerCase()).join(", ") + ".");
      if (!confirmOk) return setError("The two passwords do not match.");
    } else if (!gmailCheck.ok) {
      return setError(gmailCheck.message);
    }
    setSubmitting(true);
    try {
      if (mode === "login") {
        await login(gmailCheck.value, password);
      } else {
        await register(nameCheck.value, gmailCheck.value, password);
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
      <div className="relative overflow-hidden">
        <AmbientBackground className="z-0 opacity-60" />
      <div className="relative z-10 flex flex-col justify-between h-full px-6 md:px-14 py-8 md:py-10">
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
                    className="w-full mt-1 rounded-xl border border-line px-4 py-3 focus:outline-none focus:border-helix-teal bg-surface"
                    placeholder="Aditya Pattar"
                    autoComplete="name"
                  />
                  <p className="text-[11px] font-mono text-ink-soft mt-1">
                    Use the name on your resume and certificates. Documents are checked against it.
                  </p>
                  {name.length > 0 && !nameCheck.ok && (
                    <p className="text-[11px] font-mono text-signal-coral mt-1">{nameCheck.message}</p>
                  )}
                </motion.div>
              )}
            </AnimatePresence>

            <div>
              <label className="font-mono text-xs uppercase tracking-widest text-ink-soft">Email</label>
              <input
                required
                type="email"
                autoComplete="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                aria-invalid={email.length > 0 && !gmailCheck.ok}
                className="w-full mt-1 rounded-xl border border-line px-4 py-3 focus:outline-none focus:border-helix-teal bg-surface"
                placeholder="yourname@gmail.com"
              />
              {email.length > 0 && !gmailCheck.ok && (
                <p className="text-[11px] font-mono text-signal-coral mt-1">{gmailCheck.message}</p>
              )}
            </div>

            <div>
              <label className="font-mono text-xs uppercase tracking-widest text-ink-soft">Password</label>
              <input
                required
                type="password"
                autoComplete={mode === "register" ? "new-password" : "current-password"}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="w-full mt-1 rounded-xl border border-line px-4 py-3 focus:outline-none focus:border-helix-teal bg-surface"
                placeholder={mode === "register" ? "Choose a strong password" : "••••••••"}
              />
              {mode === "register" && password.length > 0 && (
                <ul className="mt-2 grid grid-cols-2 gap-x-3 gap-y-1 text-[11px] font-mono" aria-label="Password rules">
                  {checks.map((c) => (
                    <li key={c.label} className={c.ok ? "text-helix-teal" : "text-ink-soft"}>
                      {c.ok ? "✓" : "○"} {c.label}
                    </li>
                  ))}
                </ul>
              )}
            </div>

            {mode === "register" && (
              <div>
                <label className="font-mono text-xs uppercase tracking-widest text-ink-soft">Confirm password</label>
                <input
                  required
                  type="password"
                  autoComplete="new-password"
                  value={confirm}
                  onChange={(e) => setConfirm(e.target.value)}
                  aria-invalid={confirm.length > 0 && !confirmOk}
                  className="w-full mt-1 rounded-xl border border-line px-4 py-3 focus:outline-none focus:border-helix-teal bg-surface"
                  placeholder="Type it again"
                />
                {confirm.length > 0 && !confirmOk && (
                  <p className="text-[11px] font-mono text-signal-coral mt-1">The two passwords do not match.</p>
                )}
              </div>
            )}

            <button
              type="submit"
              disabled={submitting || !formValid}
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
