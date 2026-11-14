import { useEffect, useState, useCallback, useRef } from "react";
import { api } from "../lib/api";
import AppHeader from "../layout/AppHeader";
import { useAuth } from "../context/useAuth";
import UploadCard from "../components/UploadCard";
import ReportPanel from "../components/ReportPanel";
import IdentityPanel from "../components/IdentityPanel";
import Icon from "../ui/Icon";
import FeatureCard from "../components/FeatureCard";
import AmbientBackground from "../components/AmbientBackground";
import { useGsap } from "../lib/motion";

export default function Dashboard() {
  const { user } = useAuth();
  const page = useRef(null);

  // Entrance: the header drops in, then the evidence cards and the report rise in a stagger.
  useGsap(page, ({ reduce, gsap }) => {
    if (reduce) return undefined;
    gsap
      .timeline({ defaults: { ease: "power3.out" } })
      .from("[data-dash-header]", { y: -8, opacity: 0, duration: 0.5 })
      .from("[data-dash-card]", { y: 16, opacity: 0, duration: 0.6, stagger: 0.08 }, "-=0.2")
      .from("[data-dash-report]", { y: 16, opacity: 0, duration: 0.7 }, "-=0.5");
    return undefined;
  });

  const [report, setReport] = useState(null);
  const [reportLoading, setReportLoading] = useState(false);
  const [apiOffline, setApiOffline] = useState(false);
  const [reportError, setReportError] = useState(null);

  const refreshReport = useCallback(async (userId) => {
    setReportLoading(true);
    setApiOffline(false);
    setReportError(null);
    // The identity panel follows the same refresh, so a new upload shows its check straight away.
    api.profileGet()
      .then((profile) => setPractice((prev) => ({ ...prev, motto: profile?.motto ?? prev.motto, documents: profile?.documents ?? [] })))
      .catch(() => {});
    try {
      const r = await api.getReport(userId);
      setReport(r);
    } catch (error) {
      setApiOffline(error instanceof TypeError);
      setReportError(error.message || "Could not load your SkillDNA report.");
    } finally {
      setReportLoading(false);
    }
  }, []);

  useEffect(() => {
    if (user) refreshReport(user.id);
  }, [user, refreshReport]);

  const firstName = user?.name?.split(" ")[0];

  // Practice history for the three feature cards. Loaded once per visit.
  const [practice, setPractice] = useState({ loading: true, plan: [], daily: null, mock: [], motto: null, documents: [] });
  useEffect(() => {
    if (!user) return undefined;
    let cancelled = false;
    Promise.all([
      api.planHistory().catch(() => []),
      api.dailyHistory().catch(() => null),
      api.mockSessions().catch(() => []),
    ]).then(([plan, daily, mock]) => {
      if (!cancelled) setPractice((prev) => ({ ...prev, loading: false, plan, daily, mock }));
    });
    return () => { cancelled = true; };
  }, [user]);

  const planItems = practice.plan.map((row) => ({
    key: `${row.day}-${row.role}`,
    when: row.day,
    label: row.role,
    value: `${Math.round(row.progress_percent)}%`,
    tone: "text-helix-teal",
  }));
  const dailyItems = (practice.daily?.days || []).map((d) => ({
    key: `${d.day}-${d.skill}`,
    when: d.day,
    label: d.skill,
    value: d.correct ? `+${d.points}` : "missed",
    tone: d.correct ? "text-helix-teal" : "text-signal-coral",
  }));
  const mockItems = practice.mock.map((m) => ({
    key: String(m.id),
    when: new Date(m.started_at).toLocaleDateString(),
    label: `${m.kind === "test" ? "Test" : "Interview"} · ${m.role}`,
    value: m.score != null ? `${Math.round(m.score)}/100` : m.status,
    tone: m.violation_count ? "text-signal-coral" : "text-ink",
  }));

  return (
    <div ref={page} className="relative min-h-screen bg-paper text-ink font-body overflow-hidden">
      <AmbientBackground className="z-0 opacity-70" />
      <AppHeader />

      {reportError && (
        <div className="bg-signal-coral-soft border-b border-signal-coral/30">
          <div className="max-w-6xl mx-auto px-6 md:px-10 py-3 flex flex-wrap items-center justify-between gap-3 font-mono text-xs text-ink" role="alert">
            <p>
              {apiOffline
                ? "Backend not reachable at the configured API URL. Start it with uvicorn app.main:app --reload in backend/."
                : `Could not load your SkillDNA report: ${reportError}`}
            </p>
            <button
              onClick={() => user && refreshReport(user.id)}
              disabled={reportLoading}
              className="underline underline-offset-4 disabled:opacity-50"
            >
              {reportLoading ? "Retrying…" : "Retry"}
            </button>
          </div>
        </div>
      )}

      <main className="relative z-10 max-w-6xl mx-auto px-6 md:px-10 py-10">
        <div data-dash-header className="mb-8">
          <p className="font-mono text-xs uppercase tracking-[0.2em] text-helix-teal mb-1.5">
            {new Date().toLocaleDateString(undefined, { weekday: "long", month: "long", day: "numeric" })}
          </p>
          <h1 className="font-display text-2xl md:text-3xl font-medium tracking-tight">
            Welcome back{firstName ? `, ${firstName}` : ""}.
          </h1>
        </div>

        {practice.motto && (
          <div className="mb-8 rounded-2xl border border-helix-teal/40 bg-helix-teal/5 px-6 py-4">
            <p className="font-mono text-[11px] uppercase tracking-widest text-helix-teal">Be honest with yourself</p>
            <p className="mt-1 font-display text-lg">{practice.motto}</p>
          </div>
        )}
        <section aria-label="Practice" className="grid md:grid-cols-3 gap-5 mb-10">
          <FeatureCard
            icon="target"
            title="Improve plan"
            description="A week-by-week roadmap for the skills your target role needs, with tasks you can tick off."
            stat={practice.plan[0] ? `${Math.round(practice.plan[0].overall_score)}/100` : report?.overall_score != null ? `${Math.round(report.overall_score)}/100` : null}
            statLabel="Latest SkillDNA score"
            items={planItems}
            emptyText="Open the plan to create your first snapshot."
            to="/app/plan"
            cta="Open improve plan"
            loading={practice.loading}
          />
          <FeatureCard
            icon="spark"
            title="Daily challenge"
            description="One question a day. Most days target your gaps, and every third day explores something new."
            stat={practice.daily ? `${practice.daily.streak} day${practice.daily.streak === 1 ? "" : "s"}` : null}
            statLabel={practice.daily ? `${practice.daily.total_points} points in total` : "Current streak"}
            items={dailyItems}
            emptyText="Answer today's question to start your history."
            to="/app/daily"
            cta="Open daily challenge"
            loading={practice.loading}
          />
          <FeatureCard
            icon="shield"
            title="Mock test & interview"
            description="A timed, proctored mock test or interview for your target role, scored with feedback."
            stat={practice.mock.length ? `${practice.mock.length}` : null}
            statLabel="Sessions taken"
            items={mockItems}
            emptyText="No sessions yet. Start a mock test to see your history here."
            to="/app/mock"
            cta="Open mock test & interview"
            loading={practice.loading}
          />
        </section>

        <div className="grid lg:grid-cols-[320px_1fr] gap-10">
          <div className="space-y-4">
            <p className="font-mono text-xs uppercase tracking-widest text-ink-soft mb-1">
              Add evidence
            </p>
            <div data-dash-card>
                <UploadCard
                icon={<Icon name="document" className="h-5 w-5" />}
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
          </div>
            <div data-dash-card>
                <UploadCard
                icon={<Icon name="code" className="h-5 w-5" />}
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
          </div>
            <div data-dash-card>
                <UploadCard
                icon={<Icon name="link" className="h-5 w-5" />}
                title="LinkedIn skills"
                description="Upload your LinkedIn profile PDF, or a screenshot showing both your name and Skills section. Skills-only screenshots can't be verified."
                accept="image/png,image/jpeg,image/webp,application/pdf"
                buttonLabel="Upload screenshot or PDF"
                onSubmit={async (file) => {
                  const r = await api.uploadLinkedin(user.id, file);
                  refreshReport(user.id);
                  return r;
                }}
              />
          </div>
            <div data-dash-card>
                <UploadCard
                icon={<Icon name="certificate" className="h-5 w-5" />}
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
          </div>
          </div>

          <div className="space-y-6">
            <IdentityPanel documents={practice.documents} accountName={user?.name} loading={practice.loading} />
          <div data-dash-report>
            <p className="font-mono text-xs uppercase tracking-widest text-ink-soft mb-4">
              Your SkillDNA
            </p>
            <ReportPanel report={report} loading={reportLoading && !report} />
          </div>
          </div>
        </div>
      </main>
    </div>
  );
}
