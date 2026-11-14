import { useContext, useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { AuthContext } from "../context/authContextValue";
import ThemeToggle from "../ui/ThemeToggle";
import { api } from "../lib/api";
import AppHeader from "../layout/AppHeader";
import Appear from "../components/Appear";
import Card from "../ui/Card";
import Badge from "../ui/Badge";
import Button from "../ui/Button";
import EmptyState from "../ui/EmptyState";
import { SkeletonLines } from "../ui/Skeleton";
import { useToast } from "../ui/useToast";
import ScrollProgress from "../components/ScrollProgress";

const TABS = [
  { id: "overview", label: "Overview" },
  { id: "history", label: "History" },
  { id: "settings", label: "Settings" },
];

export default function Profile() {
  const toast = useToast();
  const auth = useContext(AuthContext);
  const navigate = useNavigate();
  const [tab, setTab] = useState("overview");
  const [profile, setProfile] = useState(null);
  const [error, setError] = useState(null);
  const [roles, setRoles] = useState([]);
  const [historyFilter, setHistoryFilter] = useState("all");

  function reload() {
    api.profileGet().then(setProfile).catch((e) => setError(e.message || "Could not load your profile."));
    api.profileRecommendations().then(setRoles).catch(() => {});
  }

  useEffect(() => { reload(); }, []);

  async function chooseRole(role) {
    try {
      await api.profileSetTargetRole(role);
      toast.show(role ? `Your target role is now ${role}.` : "Using the recommended role.", "success");
      reload();
    } catch (e) {
      toast.show(e.message || "Could not change the role.", "error");
    }
  }

  async function toggleAssistant(on) {
    try {
      await api.profileSettings(on);
      setProfile((p) => ({ ...p, assistant_context: on }));
      toast.show(on ? "The assistant can use your progress." : "The assistant will not use your progress.", "info");
    } catch (e) {
      toast.show(e.message || "Could not save that setting.", "error");
    }
  }

  async function exportData() {
    try {
      const blob = await api.profileExport();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = "skilldna-export.json";
      a.click();
      URL.revokeObjectURL(url);
      toast.show("Your export has downloaded.", "success");
    } catch (e) {
      toast.show(e.message || "Could not export your data.", "error");
    }
  }

  return (
    <div className="relative min-h-screen bg-paper font-body text-ink">
      <ScrollProgress />
      <AppHeader width="page" />
      <main className="mx-auto max-w-4xl space-y-8 px-6 py-10 md:px-10">
        {error && <p className="text-sm text-signal-coral">{error}</p>}
        {!profile && !error && <SkeletonLines lines={6} />}

        {profile && (
          <>
            <Appear>
              <section className="space-y-3">
                <p className="font-mono text-xs uppercase tracking-[0.2em] text-helix-teal">Profile</p>
                <h1 className="font-display text-3xl font-medium tracking-tight">{profile.name}</h1>
                <p className="font-mono text-xs text-ink-soft">{profile.email}</p>
                <div className="rounded-2xl border border-helix-teal/40 bg-helix-teal/5 px-5 py-4">
                  <p className="font-mono text-[11px] uppercase tracking-widest text-helix-teal">Be honest with yourself</p>
                  <p className="mt-1 font-display text-lg">{profile.motto}</p>
                </div>
              </section>
            </Appear>

            <nav aria-label="Profile sections" className="flex gap-2 border-b border-line">
              {TABS.map((t) => (
                <button key={t.id} type="button" onClick={() => setTab(t.id)} aria-current={tab === t.id ? "page" : undefined}
                  className={`-mb-px border-b-2 px-4 py-2.5 font-display text-sm transition-colors ${
                    tab === t.id ? "border-helix-teal text-ink" : "border-transparent text-ink-soft hover:text-ink"}`}>
                  {t.label}
                </button>
              ))}
            </nav>

            {tab === "overview" && (
              <div className="space-y-6">
                <div className="grid gap-4 md:grid-cols-4">
                  <Stat label="Score" value={`${Math.round(profile.summary.overall)}/100`} hint={profile.summary.tier} />
                  <Stat label="Skills" value={profile.summary.skills} hint="counted across sources" />
                  <Stat label="Streak" value={`${profile.stats.streak} day${profile.stats.streak === 1 ? "" : "s"}`} hint="daily challenge" />
                  <Stat label="Phases passed" value={profile.stats.phases_passed} hint="phase tests" />
                </div>

                <div className="grid gap-4 md:grid-cols-2">
                  <Card>
                    <p className="font-display font-medium">Strengths</p>
                    <p className="mt-2 text-sm text-ink-soft">{profile.summary.strengths.join(", ") || "None shown yet. Upload evidence to start."}</p>
                    <p className="mt-5 font-display font-medium">Gaps to close</p>
                    <p className="mt-2 text-sm text-ink-soft">{profile.summary.gaps.join(", ") || "No gaps on record."}</p>
                  </Card>
                  <Card>
                    <p className="font-display font-medium">Your target role</p>
                    <p className="mt-2 text-sm">
                      {profile.effective_role}
                      {!profile.target_role && <span className="ml-2 text-xs text-ink-soft">(recommended for you)</span>}
                    </p>
                    <p className="mt-4 text-xs text-ink-soft">Change it in Settings. Your plan follows this role.</p>
                  </Card>
                </div>

                <section className="space-y-3">
                  <p className="font-mono text-xs uppercase tracking-widest text-ink-soft">Roles that fit your evidence</p>
                  {profile.recommendations.length === 0 ? (
                    <EmptyState title="No recommendations yet" body="Upload a resume or certificates and roles will be ranked here." />
                  ) : (
                    <div className="grid gap-4 md:grid-cols-3">
                      {profile.recommendations.map((r) => (
                        <Card key={r.role} className="flex flex-col gap-3">
                          <div className="flex items-center justify-between gap-2">
                            <p className="font-display font-medium">{r.role}</p>
                            <Badge tone={r.fit >= 60 ? "teal" : "neutral"}>{Math.round(r.fit)}% fit</Badge>
                          </div>
                          <p className="text-xs text-ink-soft">{r.reason}</p>
                          <Button variant="ghost" size="sm" onClick={() => chooseRole(r.role)}>Make this my target</Button>
                        </Card>
                      ))}
                    </div>
                  )}
                </section>

                <section className="space-y-3">
                  <p className="font-mono text-xs uppercase tracking-widest text-ink-soft">Achievements</p>
                  <div className="grid gap-3 md:grid-cols-2">
                    {profile.achievements.map((a) => (
                      <div key={a.id} className={`flex items-start gap-3 rounded-2xl border p-4 ${a.earned ? "border-helix-teal/50 bg-helix-teal/5" : "border-line bg-surface opacity-70"}`}>
                        <span aria-hidden="true" className="text-lg">{a.earned ? "◆" : "◇"}</span>
                        <div>
                          <p className="font-display text-sm font-medium">{a.title}</p>
                          <p className="text-xs text-ink-soft">{a.detail}</p>
                        </div>
                      </div>
                    ))}
                  </div>
                </section>
              </div>
            )}

            {tab === "history" && (
              <section className="space-y-4">
                <div className="flex flex-wrap gap-2" role="group" aria-label="Filter history">
                  {["all", "upload", "plan", "daily", "phase", "mock", "interview"].map((k) => (
                    <button key={k} type="button" aria-pressed={historyFilter === k} onClick={() => setHistoryFilter(k)}
                      className={`rounded-full border px-3 py-1 font-mono text-xs ${historyFilter === k ? "border-ink bg-ink text-paper" : "border-line text-ink-soft hover:text-ink"}`}>
                      {k}
                    </button>
                  ))}
                </div>
                {profile.history.filter((h) => historyFilter === "all" || h.kind === historyFilter).length === 0 ? (
                  <EmptyState title="Nothing here yet" body="Uploads, plan snapshots, daily answers, tests and interviews appear here as you use them." />
                ) : (
                  <ol className="relative space-y-3 border-l border-line pl-6">
                    {profile.history
                      .filter((h) => historyFilter === "all" || h.kind === historyFilter)
                      .map((h, i) => (
                        <li key={`${h.kind}-${i}`} className="relative">
                          <span className={`absolute -left-[31px] top-1.5 h-2.5 w-2.5 rounded-full ${h.tone === "coral" ? "bg-signal-coral" : h.tone === "teal" ? "bg-helix-teal" : "bg-helix-violet"}`} />
                          <p className="font-mono text-[11px] text-ink-soft">{String(h.at || "").slice(0, 10)} · {h.kind}</p>
                          <p className="text-sm font-medium">{h.title}</p>
                          <p className="text-xs text-ink-soft">{h.detail}</p>
                        </li>
                      ))}
                  </ol>
                )}
              </section>
            )}

            {tab === "settings" && (
              <div className="space-y-6">
                <Card className="space-y-3">
                  <p className="font-display font-medium">Target role</p>
                  <select aria-label="Target role" value={profile.target_role || ""} onChange={(e) => chooseRole(e.target.value || null)}
                    className="w-full rounded-xl border border-line bg-surface px-4 py-2.5 text-sm">
                    <option value="">Use the recommended role ({profile.effective_role})</option>
                    {roles.map((r) => <option key={r.role} value={r.role}>{r.role}</option>)}
                  </select>
                </Card>

                <Card className="space-y-3">
                  <label className="flex cursor-pointer items-start gap-3">
                    <input type="checkbox" className="mt-1" checked={profile.assistant_context} onChange={(e) => toggleAssistant(e.target.checked)} />
                    <span>
                      <span className="font-display font-medium">Let the assistant use my progress</span>
                      <span className="mt-1 block text-sm text-ink-soft">
                        The assistant can answer "what next?" and plan your week from your plan and scores. It never reads your documents.
                        Switch this off and it answers general questions only.
                      </span>
                    </span>
                  </label>
                </Card>

                <Card className="space-y-3">
                  <p className="font-display font-medium">Your data</p>
                  <p className="text-sm text-ink-soft">Download everything SkillDNA holds about you as one file. Document text is not included.</p>
                  <Button variant="ink" onClick={exportData}>Download my data</Button>
                </Card>

                <Card className="space-y-3">
                  <p className="font-display font-medium">Appearance</p>
                  <p className="text-sm text-ink-soft">Light, dark, or follow your device's setting.</p>
                  <ThemeToggle />
                </Card>

                <Card className="space-y-3">
                  <p className="font-display font-medium">Account</p>
                  <p className="text-sm text-ink-soft">Signed in as {profile.email}</p>
                  <Button variant="ghost" onClick={() => { auth?.logout?.(); navigate("/login"); }}>Log out</Button>
                </Card>
              </div>
            )}
          </>
        )}
      </main>
    </div>
  );
}

function Stat({ label, value, hint }) {
  return (
    <div className="rounded-2xl border border-line bg-surface p-4">
      <p className="font-mono text-[11px] uppercase tracking-widest text-ink-soft">{label}</p>
      <p className="mt-1 font-display text-2xl font-medium">{value}</p>
      {hint && <p className="mt-1 text-xs text-ink-soft">{hint}</p>}
    </div>
  );
}
