import { useEffect, useState } from "react";
import { motion, AnimatePresence, animate } from "framer-motion";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  Cell,
} from "recharts";
import Helix from "./Helix";

/* ── animated counter ─────────────────────────────────────────────── */
function CountUp({ value, decimals = 1 }) {
  const [display, setDisplay] = useState(0);
  useEffect(() => {
    const ctrl = animate(0, value, {
      duration: 1.2,
      ease: [0.16, 1, 0.3, 1],
      onUpdate: (v) => setDisplay(v),
    });
    return () => ctrl.stop();
  }, [value]);
  return <>{decimals === 0 ? Math.round(display) : display.toFixed(decimals)}</>;
}

/* ── colour tokens per source ─────────────────────────────────────── */
const SOURCE_META = {
  resume: {
    label: "Resume",
    icon: "📄",
    color: "#0F9E8E",          // helix-teal
    bg: "bg-[#0F9E8E]/10",
    border: "border-[#0F9E8E]/30",
    text: "text-[#0F9E8E]",
    track: "#0F9E8E",
  },
  github: {
    label: "GitHub",
    icon: "💻",
    color: "#6C5CE0",
    bg: "bg-[#6C5CE0]/10",
    border: "border-[#6C5CE0]/30",
    text: "text-[#6C5CE0]",
    track: "#6C5CE0",
  },
  linkedin: {
    label: "LinkedIn",
    icon: "🔗",
    color: "#2D8FD1",
    bg: "bg-[#2D8FD1]/10",
    border: "border-[#2D8FD1]/30",
    text: "text-[#2D8FD1]",
    track: "#2D8FD1",
  },
  certificate: {
    label: "Certificate",
    icon: "🎓",
    color: "#E8A93C",
    bg: "bg-[#E8A93C]/10",
    border: "border-[#E8A93C]/30",
    text: "text-[#E8A93C]",
    track: "#E8A93C",
  },
};

const SOURCE_WEIGHTS = {
  resume: 30,
  github: 30,
  linkedin: 25,
  certificate: 15,
};
const SOURCE_MAX = Object.values(SOURCE_WEIGHTS).reduce((sum, value) => sum + value, 0);
const SOURCE_ORDER = ["resume", "github", "linkedin", "certificate"];

/* ── radial arc progress ring ─────────────────────────────────────── */
function ArcRing({ value, max = SOURCE_MAX, color, size = 72 }) {
  const r = (size - 10) / 2;
  const circ = 2 * Math.PI * r;
  const pct = Math.min(value / max, 1);
  const [dash, setDash] = useState(0);
  useEffect(() => {
    const ctrl = animate(0, pct * circ, {
      duration: 1.2,
      ease: [0.16, 1, 0.3, 1],
      onUpdate: (v) => setDash(v),
    });
    return () => ctrl.stop();
  }, [pct, circ]);

  return (
    <svg width={size} height={size} className="rotate-[-90deg]">
      <circle
        cx={size / 2} cy={size / 2} r={r}
        fill="none" stroke="#E8EAE3" strokeWidth={6}
      />
      <circle
        cx={size / 2} cy={size / 2} r={r}
        fill="none" stroke={color} strokeWidth={6}
        strokeLinecap="round"
        strokeDasharray={`${dash} ${circ}`}
        style={{ transition: "stroke-dasharray 0.05s" }}
      />
    </svg>
  );
}

/* ── single source card ───────────────────────────────────────────── */
function SourceCard({ sourceKey, earned, index }) {
  const meta = SOURCE_META[sourceKey];
  const max = SOURCE_WEIGHTS[sourceKey];
  const pct = Math.round((earned / max) * 100);
  const status =
    earned === 0 ? "Not added" : pct >= 80 ? "Strong" : pct >= 50 ? "Moderate" : "Partial";

  return (
    <motion.div
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: index * 0.07, duration: 0.45, ease: "easeOut" }}
      className={`rounded-2xl border ${meta.border} ${meta.bg} p-4 flex flex-col gap-3`}
    >
      {/* header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span className="text-xl">{meta.icon}</span>
          <span className="font-display font-medium text-sm">{meta.label}</span>
        </div>
        <span className={`font-mono text-[10px] px-2 py-0.5 rounded-full border ${meta.border} ${meta.text}`}>
          {status}
        </span>
      </div>

      {/* arc + score */}
      <div className="flex items-center gap-4">
        <div className="relative shrink-0">
          <ArcRing value={earned} color={meta.color} size={72} />
          <div className="absolute inset-0 flex flex-col items-center justify-center">
            <span className={`font-display font-semibold text-base leading-none ${meta.text}`}>
              <CountUp value={earned} decimals={1} />
            </span>
          </div>
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex justify-between items-end mb-1.5">
            <span className="font-mono text-[10px] text-ink-soft uppercase tracking-widest">Score</span>
            <span className="font-mono text-xs text-ink-soft">/ {max}</span>
          </div>
          {/* progress bar */}
          <div className="h-1.5 rounded-full bg-line overflow-hidden">
            <motion.div
              className="h-full rounded-full"
              style={{ backgroundColor: meta.color }}
              initial={{ width: 0 }}
              animate={{ width: `${pct}%` }}
              transition={{ duration: 1.2, ease: [0.16, 1, 0.3, 1], delay: index * 0.07 }}
            />
          </div>
          <p className="font-mono text-[10px] text-ink-soft mt-1.5">
            {earned === 0
              ? "Upload to earn points"
              : `${pct}% of ${max} pts`}
          </p>
        </div>
      </div>
    </motion.div>
  );
}

/* ── category colours for skill chart ────────────────────────────── */
const CATEGORY_COLORS = {
  "Programming Language": "#0F9E8E",
  Framework: "#6C5CE0",
  Database: "#2D8FD1",
  "Cloud/DevOps": "#E8A93C",
  "Data/ML": "#E85D4C",
  "Soft Skill": "#8C93A6",
};

function ScoreBadge({ score }) {
  const color =
    score >= 75 ? "text-helix-teal" : score >= 50 ? "text-helix-violet" : "text-signal-coral";
  return <span className={`font-mono font-semibold ${color}`}>{score.toFixed(0)}</span>;
}

/* ── main component ───────────────────────────────────────────────── */
export default function ReportPanel({ report, loading }) {
  if (loading) {
    return (
      <div className="rounded-2xl border border-line p-10 text-center text-ink-soft font-mono text-sm">
        Sequencing your evidence…
      </div>
    );
  }

  if (!report || report.all_scores.length === 0) {
    return (
      <div className="space-y-8">
        <div className="rounded-2xl border border-dashed border-line p-6">
          <p className="font-mono text-xs uppercase tracking-widest text-ink-soft mb-1">
            Overall SkillDNA score
          </p>
          <p className="font-display text-5xl font-medium">
            0<span className="text-ink-soft text-2xl">/100</span>
          </p>
          <p className="text-ink-soft text-sm mt-3">
            Upload evidence on the left to start building your score.
          </p>
        </div>

        {/* source breakdown — all zeroed */}
        <div>
          <p className="font-mono text-xs uppercase tracking-widest text-ink-soft mb-3">
            Score breakdown — weighted by evidence source
          </p>
          <div className="grid sm:grid-cols-2 xl:grid-cols-4 gap-3">
            {SOURCE_ORDER.map((k, i) => (
              <SourceCard key={k} sourceKey={k} earned={0} index={i} />
            ))}
          </div>
        </div>
      </div>
    );
  }

  const srcScores = report.source_scores || {};
  const chartData = [...report.all_scores]
    .sort((a, b) => b.score - a.score)
    .map((s) => ({ name: s.skill_name, score: s.score, category: s.category }));

  return (
    <div className="space-y-8">
      {/* ── overall score ── */}
      <motion.div
        initial={{ opacity: 0, scale: 0.97 }}
        animate={{ opacity: 1, scale: 1 }}
        transition={{ duration: 0.4, ease: "easeOut" }}
        className="rounded-2xl border border-line p-6 flex items-center gap-8 flex-wrap"
      >
        <div>
          <p className="font-mono text-xs uppercase tracking-widest text-ink-soft mb-1">
            Overall SkillDNA score
          </p>
          <p className="font-display text-5xl font-medium">
            <CountUp value={report.overall_score} />
            <span className="text-ink-soft text-2xl">/100</span>
          </p>
          {report.tier && (
            <span className="inline-block mt-1.5 font-mono text-xs px-2.5 py-1 rounded-full bg-helix-teal-soft text-helix-teal">
              {report.tier}
            </span>
          )}
        </div>
        <div className="w-px self-stretch bg-line hidden sm:block" />
        <div className="flex gap-6 font-mono text-sm">
          <div>
            <p className="text-2xl font-display">{report.all_scores.length}</p>
            <p className="text-ink-soft text-xs">skills detected</p>
          </div>
          <div>
            <p className="text-2xl font-display">{report.strengths.length}</p>
            <p className="text-ink-soft text-xs">strengths</p>
          </div>
          <div>
            <p className="text-2xl font-display">{report.gaps.length}</p>
            <p className="text-ink-soft text-xs">gaps</p>
          </div>
        </div>
      </motion.div>

      {/* ── source score breakdown ── */}
      <div>
        <p className="font-mono text-xs uppercase tracking-widest text-ink-soft mb-3">
          Score breakdown — weighted contribution to total score
        </p>

        {/* equation: A + B + C + D = total */}
        <div className="grid sm:grid-cols-2 xl:grid-cols-4 gap-3 mb-3">
          {SOURCE_ORDER.map((k, i) => (
            <SourceCard key={k} sourceKey={k} earned={srcScores[k] ?? 0} index={i} />
          ))}
        </div>

        {/* sum row */}
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.4 }}
          className="rounded-xl border border-line bg-paper px-5 py-3 flex items-center justify-between flex-wrap gap-2"
        >
          <div className="flex items-center gap-2 flex-wrap">
            {SOURCE_ORDER.map((k, i) => {
              const meta = SOURCE_META[k];
              const v = srcScores[k] ?? 0;
              return (
                <span key={k} className="flex items-center gap-1 font-mono text-xs">
                  <span className={meta.text}>{v.toFixed(1)}</span>
                  {i < SOURCE_ORDER.length - 1 && <span className="text-ink-soft">+</span>}
                </span>
              );
            })}
            <span className="text-ink-soft font-mono text-xs">=</span>
          </div>
          <div className="font-display text-lg font-semibold">
            <CountUp value={report.overall_score} />
            <span className="text-ink-soft text-sm font-normal"> / 100</span>
          </div>
        </motion.div>
      </div>

      {/* ── skill chart + helix ── */}
      <div className="grid lg:grid-cols-5 gap-8">
        <div className="lg:col-span-3 rounded-2xl border border-line p-6">
          <p className="font-display font-medium mb-4">Skill scores by evidence strength</p>
          <ResponsiveContainer width="100%" height={Math.max(220, chartData.length * 34)}>
            <BarChart data={chartData} layout="vertical" margin={{ left: 8, right: 24 }}>
              <XAxis type="number" domain={[0, 100]} tick={{ fontSize: 11, fontFamily: "IBM Plex Mono" }} stroke="#D8DBD3" />
              <YAxis
                dataKey="name"
                type="category"
                width={110}
                tick={{ fontSize: 12, fontFamily: "Inter" }}
                stroke="#D8DBD3"
              />
              <Tooltip
                formatter={(v) => [`${v.toFixed(1)} / 100`, "Score"]}
                contentStyle={{ fontFamily: "IBM Plex Mono", fontSize: 12, borderRadius: 8 }}
              />
              <Bar dataKey="score" radius={[0, 6, 6, 0]} maxBarSize={18}>
                {chartData.map((entry, i) => (
                  <Cell key={i} fill={CATEGORY_COLORS[entry.category] || "#0F9E8E"} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>

        <div className="lg:col-span-2 rounded-2xl border border-line p-6 flex flex-col items-center justify-center">
          <p className="font-display font-medium mb-2 self-start">Evidence strand</p>
          <Helix variant="report" skills={report.all_scores.slice(0, 10)} height={280} width={200} />
          <p className="font-mono text-[11px] text-ink-soft mt-2">
            <span className="text-helix-teal">teal rung</span> = confirmed by 2+ sources
          </p>
        </div>
      </div>

      {/* ── strengths + gaps ── */}
      <div className="grid md:grid-cols-2 gap-8">
        <div className="rounded-2xl border border-line p-6">
          <p className="font-display font-medium mb-4">Strengths</p>
          <ul className="space-y-2.5">
            {report.strengths.map((s) => (
              <li key={s.skill_name} className="flex items-center justify-between text-sm">
                <span>{s.skill_name}</span>
                <ScoreBadge score={s.score} />
              </li>
            ))}
          </ul>
        </div>

        <div className="rounded-2xl border border-line p-6">
          <p className="font-display font-medium mb-4">Gaps to shore up</p>
          {report.gaps.length === 0 ? (
            <p className="text-ink-soft text-sm">No low-confidence skills — nice work.</p>
          ) : (
            <ul className="space-y-2.5">
              {report.gaps.map((s) => (
                <li key={s.skill_name} className="flex items-center justify-between text-sm">
                  <span>{s.skill_name}</span>
                  <ScoreBadge score={s.score} />
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>

      {/* ── roadmap ── */}
      <div className="rounded-2xl bg-ink text-paper p-6">
        <p className="font-display font-medium mb-4">Your roadmap</p>
        <ul className="space-y-3">
          <AnimatePresence>
            {report.recommendations.map((r, i) => (
              <motion.li
                key={r}
                initial={{ opacity: 0, x: -8 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: i * 0.08 }}
                className="text-sm text-paper/80 leading-relaxed pl-4 border-l-2 border-helix-teal"
              >
                {r}
              </motion.li>
            ))}
          </AnimatePresence>
        </ul>
      </div>
    </div>
  );
}
