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

function CountUpScore({ value }) {
  const [display, setDisplay] = useState(0);
  useEffect(() => {
    const controls = animate(0, value, {
      duration: 1.1,
      ease: [0.16, 1, 0.3, 1],
      onUpdate: (v) => setDisplay(v),
    });
    return () => controls.stop();
  }, [value]);
  return <>{display.toFixed(1)}</>;
}

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
      <div className="rounded-2xl border border-dashed border-line p-10 text-center">
        <p className="font-display text-lg mb-1">No evidence yet</p>
        <p className="text-ink-soft text-sm">
          Upload a resume, GitHub username, LinkedIn screenshot, or certificate on
          the left to generate your SkillDNA score.
        </p>
      </div>
    );
  }

  const chartData = [...report.all_scores]
    .sort((a, b) => b.score - a.score)
    .map((s) => ({ name: s.skill_name, score: s.score, category: s.category }));

  return (
    <div className="space-y-8">
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
            <CountUpScore value={report.overall_score} />
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
