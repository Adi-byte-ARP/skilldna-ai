import { useEffect, useState, useCallback } from "react";
import { Link, useNavigate } from "react-router-dom";
import { motion } from "framer-motion";
import { api } from "../lib/api";
import { useAuth } from "../context/useAuth";
import UploadCard from "../components/UploadCard";
import ReportPanel from "../components/ReportPanel";

const container = {
  hidden: { opacity: 0 },
  show: { opacity: 1, transition: { staggerChildren: 0.08, delayChildren: 0.1 } },
};
const item = {
  hidden: { opacity: 0, y: 14 },
  show: { opacity: 1, y: 0, transition: { duration: 0.5, ease: "easeOut" } },
};

export default function Dashboard() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  const [report, setReport] = useState(null);
  const [reportLoading, setReportLoading] = useState(false);
  const [apiOffline, setApiOffline] = useState(false);

  const refreshReport = useCallback(async (userId) => {
    setReportLoading(true);
    try {
      const r = await api.getReport(userId);
      setReport(r);
      setApiOffline(false);
    } catch {
      setApiOffline(true);
    } finally {
      setReportLoading(false);
    }
  }, []);

  useEffect(() => {
    if (user) refreshReport(user.id);
  }, [user, refreshReport]);

  const handleLogout = () => {
    logout();
    navigate("/login");
  };

  const firstName = user?.name?.split(" ")[0];

  return (
    <div className="min-h-screen bg-paper text-ink font-body">
      <header className="border-b border-line">
        <div className="max-w-6xl mx-auto px-6 md:px-10 py-5 flex items-center justify-between">
          <Link to="/" className="font-display font-semibold text-lg tracking-tight flex items-center gap-2">
            <span className="w-2.5 h-2.5 rounded-full bg-helix-teal inline-block" />
            SkillDNA<span className="text-helix-teal">.AI</span>
          </Link>
          {user && (
            <div className="flex items-center gap-4">
              <span className="font-mono text-xs text-ink-soft hidden sm:inline">{user.email}</span>
              <button
                onClick={handleLogout}
                className="font-display text-xs text-ink-soft hover:text-ink underline underline-offset-4"
              >
                Log out
              </button>
            </div>
          )}
        </div>
      </header>

      {apiOffline && (
        <div className="bg-signal-coral-soft border-b border-signal-coral/30">
          <div className="max-w-6xl mx-auto px-6 md:px-10 py-3 font-mono text-xs text-ink">
            Backend not reachable at the configured API URL. Start it with{" "}
            <code className="bg-white px-1.5 py-0.5 rounded">uvicorn app.main:app --reload</code> in{" "}
            <code className="bg-white px-1.5 py-0.5 rounded">backend/</code>.
          </div>
        </div>
      )}

      <main className="max-w-6xl mx-auto px-6 md:px-10 py-10">
        <motion.div initial={{ opacity: 0, y: -8 }} animate={{ opacity: 1, y: 0 }} className="mb-8">
          <p className="font-mono text-xs uppercase tracking-[0.2em] text-helix-teal mb-1.5">
            {new Date().toLocaleDateString(undefined, { weekday: "long", month: "long", day: "numeric" })}
          </p>
          <h1 className="font-display text-2xl md:text-3xl font-medium tracking-tight">
            Welcome back{firstName ? `, ${firstName}` : ""}.
          </h1>
        </motion.div>

        <motion.div
          variants={container}
          initial="hidden"
          animate="show"
          className="grid lg:grid-cols-[320px_1fr] gap-10"
        >
          <motion.div variants={item} className="space-y-4">
            <p className="font-mono text-xs uppercase tracking-widest text-ink-soft mb-1">
              Add evidence
            </p>
            <UploadCard
              icon="📄"
              title="Resume"
              description="PDF only. We extract every skill mentioned."
              accept="application/pdf"
              buttonLabel="Upload resume"
              onSubmit={async (file) => {
                const r = await api.uploadResume(user.id, file);
                refreshReport(user.id);
                return r;
              }}
            />
            <UploadCard
              icon="💻"
              title="GitHub"
              description="Your public repos, analyzed by language usage."
              mode="text"
              textPlaceholder="username or profile URL"
              buttonLabel="Analyze"
              onSubmit={async (username) => {
                const r = await api.analyzeGithub(user.id, username);
                refreshReport(user.id);
                return r;
              }}
            />
            <UploadCard
              icon="🔗"
              title="LinkedIn skills"
              description="Screenshot your Skills section, or export your profile as a PDF from LinkedIn — either works."
              accept="image/png,image/jpeg,image/webp,application/pdf"
              buttonLabel="Upload screenshot or PDF"
              onSubmit={async (file) => {
                const r = await api.uploadLinkedin(user.id, file);
                refreshReport(user.id);
                return r;
              }}
            />
            <UploadCard
              icon="🎓"
              title="Certificates"
              description="Course completions, certifications — images or PDFs. Select several at once."
              accept="image/png,image/jpeg,image/webp,application/pdf"
              buttonLabel="Upload certificates"
              mode="multiFile"
              onSubmit={async (files) => {
                const r = await api.uploadCertificates(user.id, files);
                refreshReport(user.id);
                return r;
              }}
            />
          </motion.div>

          <motion.div variants={item}>
            <p className="font-mono text-xs uppercase tracking-widest text-ink-soft mb-4">
              Your SkillDNA
            </p>
            <ReportPanel report={report} loading={reportLoading && !report} />
          </motion.div>
        </motion.div>
      </main>
    </div>
  );
}
