import React from "react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";

vi.mock("../lib/api", () => ({
  api: {
    planHistory: vi.fn(),
    profileGet: vi.fn(),
    mockRoles: vi.fn(),
    planGet: vi.fn(),
    planToggleTask: vi.fn(),
    dailyToday: vi.fn(),
    dailyAnswer: vi.fn(),
    dailyHistory: vi.fn(),
    dailyStatus: vi.fn(),
    remindersGet: vi.fn(),
    remindersSet: vi.fn(),
  },
}));

import { api } from "../lib/api";
import Plan from "../pages/Plan";
import Daily from "../pages/Daily";

function planFixture(done = false) {
  const tasks = [
    { key: "sql:task0", text: "Complete the SQL lessons", done },
    { key: "sql:task1", text: "Write 10 queries", done: false },
    { key: "sql:task2", text: "Use EXPLAIN", done: false },
  ];
  return {
    role: "Backend Engineer",
    overall_score: 42,
    tier: "Developing",
    summary: "For Backend Engineer, you have 1 gap.",
    strengths_to_leverage: ["python"],
    gap_count: 1,
    total_hours_estimate: 25,
    no_gaps: false,
    mode: "gap",
    improve: [{ key: "sql", skill: "sql", status: "missing", score: null, priority: "High",
      reason: "Not shown yet. Almost every data role needs it.", next_task: "Complete the SQL lessons",
      next_task_key: "sql:task0", phase_index: 0, hours: 25 }],
    progress: { done: done ? 1 : 0, total: 3, percent: done ? 33.3 : 0 },
    phases: [
      { name: "Phase 1 · Foundations (weeks 1-2)", goal: "Work through SQL.", items: ["sql"] },
      { name: "Phase 2 · Build (weeks 3-4)", goal: "None.", items: [] },
      { name: "Phase 3 · Apply (weeks 5-6)", goal: "None.", items: [] },
      { name: "Phase 4 · Prove it (weeks 7-8)", goal: "Mock test.", items: [] },
    ],
    items: [{
      key: "sql",
      skill: "sql",
      status: "missing",
      current_score: null,
      why: "Almost every data role needs it.",
      objectives: ["Write SELECT with GROUP BY"],
      progress: { baseline_score: 0, current_score: 55, score_change: 55, tasks_done: 1, tasks_total: 3,
                  daily_correct: 2, daily_attempts: 3, message: "Up 55 points since you started this plan." },
      tasks,
      project: "A sales report.",
      resources: [{ name: "SQLBolt", url: "https://sqlbolt.org" }],
      hours_estimate: 25,
      check: "Pass 4 of 5 challenges.",
    }],
  };
}

function challengeFixture(answered = false) {
  return {
    date: "2026-10-12",
    role: "Full-Stack Developer",
    streak: 2,
    total_points: 20,
    explore: false,
    challenge: { id: "d-sql-2", skill: "sql", question: "Which clause filters groups after GROUP BY?", options: ["WHERE", "HAVING", "FILTER", "ORDER BY"] },
    answered,
    result: null,
  };
}

beforeEach(() => {
  vi.clearAllMocks();
  api.mockRoles.mockResolvedValue({ roles: ["Backend Engineer", "Full-Stack Developer"] });
  api.planGet.mockResolvedValue(planFixture());
  api.planHistory.mockResolvedValue([]);
  api.profileGet.mockResolvedValue({ effective_role: "Full-Stack Developer" });
  api.planToggleTask.mockResolvedValue({ task_key: "sql:task0", done: true });
  api.dailyHistory.mockResolvedValue({ streak: 2, total_points: 20, days: [] });
  api.dailyStatus.mockResolvedValue({ answered_today: false, remind_now: false, streak: 2, email_opt_in: false });
  api.remindersGet.mockResolvedValue({ email_opt_in: false });
  api.remindersSet.mockResolvedValue({ email_opt_in: true });
});

describe("improve plan page", () => {
  it("shows the gap card with its objectives, tasks, project and resources", async () => {
    render(<MemoryRouter><Plan /></MemoryRouter>);
    expect(await screen.findByText("Your skill-gap roadmap")).toBeInTheDocument();
    expect(screen.getByText(/Phase 1 · Foundations/)).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: /sql/i }));
    expect(screen.getByText("Write SELECT with GROUP BY")).toBeInTheDocument();
    expect(screen.getAllByText("Complete the SQL lessons").length).toBeGreaterThan(0);
    expect(screen.getByText("A sales report.")).toBeInTheDocument();
    const link = screen.getByRole("link", { name: "SQLBolt" });
    expect(link).toHaveAttribute("href", "https://sqlbolt.org");
    expect(link).toHaveAttribute("rel", "noopener noreferrer");
  });

  it("ticking a task saves it to the server and refreshes progress", async () => {
    api.planGet.mockResolvedValueOnce(planFixture()).mockResolvedValue(planFixture(true));
    render(<MemoryRouter><Plan /></MemoryRouter>);
    await screen.findByText("Your skill-gap roadmap");
    fireEvent.click(screen.getByRole("button", { name: /sql/i }));
    fireEvent.click(screen.getByRole("checkbox", { name: /Complete the SQL lessons/i }));
    await waitFor(() => expect(api.planToggleTask).toHaveBeenCalledWith("sql:task0", true, "Full-Stack Developer", "gap"));
    // overall progress bar and the per-skill progress both show "1 of 3"
    expect((await screen.findAllByText(/1 of 3/)).length).toBeGreaterThan(0);
  });

  it("switching the target role reloads the plan for that role", async () => {
    render(<MemoryRouter><Plan /></MemoryRouter>);
    await screen.findByText("Your skill-gap roadmap");
    fireEvent.change(screen.getByLabelText(/Target role/i), { target: { value: "Full-Stack Developer" } });
    await waitFor(() => expect(api.planGet).toHaveBeenCalledWith("Full-Stack Developer", "gap"));
  });
});

describe("plan progress", () => {
  it("shows the score change, task count and daily accuracy for each skill", async () => {
    render(<MemoryRouter><Plan /></MemoryRouter>);
    await screen.findByText("Your skill-gap roadmap");
    fireEvent.click(screen.getByRole("button", { name: /sql/i }));
    expect(screen.getByText(/Score: 0 at start/)).toBeInTheDocument();
    expect(screen.getByText(/\+55/)).toBeInTheDocument();
    expect(screen.getByText(/Tasks ticked: 1 of 3/)).toBeInTheDocument();
    expect(screen.getByText(/2 correct of 3 answered/)).toBeInTheDocument();
    expect(screen.getByText("Up 55 points since you started this plan.")).toBeInTheDocument();
  });
});

describe("daily challenge page", () => {
  it("shows the question, grades the answer and reveals the explanation", async () => {
    api.dailyToday.mockResolvedValue(challengeFixture());
    api.dailyAnswer.mockResolvedValue({
      correct: true, your_index: 1, correct_index: 1,
      explanation: "HAVING filters groups after aggregation.", points: 10, streak: 3,
    });
    render(<MemoryRouter><Daily /></MemoryRouter>);
    expect(await screen.findByText("Which clause filters groups after GROUP BY?")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "HAVING" }));
    fireEvent.click(screen.getByRole("button", { name: /submit answer/i }));
    await waitFor(() => expect(api.dailyAnswer).toHaveBeenCalledWith("d-sql-2", 1, "Full-Stack Developer", undefined));
    expect(await screen.findByText(/Correct · \+10 points/)).toBeInTheDocument();
    expect(screen.getByText("HAVING filters groups after aggregation.")).toBeInTheDocument();
  });

  it("does not offer a second answer once today is answered", async () => {
    api.dailyToday.mockResolvedValue({
      ...challengeFixture(true),
      result: { correct: false, your_index: 0, correct_index: 1, explanation: "Use HAVING.", points: 0 },
    });
    render(<MemoryRouter><Daily /></MemoryRouter>);
    expect(await screen.findByText("Not this time")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /submit answer/i })).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "HAVING" })).toBeDisabled();
  });

  it("shows the streak and points from the server", async () => {
    api.dailyToday.mockResolvedValue(challengeFixture());
    render(<MemoryRouter><Daily /></MemoryRouter>);
    expect(await screen.findByText("2 days")).toBeInTheDocument();
    expect(screen.getByText("20")).toBeInTheDocument();
  });
});

describe("free-text daily challenge", () => {
  it("accepts a typed answer and shows the grade with the accepted answers", async () => {
    api.dailyToday.mockResolvedValue({
      ...challengeFixture(),
      challenge: { id: "t-git-1", kind: "text", skill: "git", question: "Name the command.", min_hits: 1 },
    });
    api.dailyAnswer.mockResolvedValue({
      correct: true, accepted: ["checkout -b", "switch -c"], hits: ["checkout -b"], needed: 1,
      explanation: "Use checkout -b.", points: 10, streak: 3,
    });
    render(<MemoryRouter><Daily /></MemoryRouter>);
    const box = await screen.findByLabelText(/Your answer/i);
    fireEvent.change(box, { target: { value: "git checkout -b feature" } });
    fireEvent.click(screen.getByRole("button", { name: /submit answer/i }));
    await waitFor(() => expect(api.dailyAnswer).toHaveBeenCalledWith("t-git-1", null, "Full-Stack Developer", "git checkout -b feature"));
    expect(await screen.findByText(/Accepted answers include: checkout -b, switch -c/)).toBeInTheDocument();
    expect(screen.getByLabelText(/Your answer/i)).toHaveValue("git checkout -b feature");
  });

  it("keeps submit disabled until something is typed", async () => {
    api.dailyToday.mockResolvedValue({
      ...challengeFixture(),
      challenge: { id: "t-git-1", kind: "text", skill: "git", question: "Name the command.", min_hits: 1 },
    });
    render(<MemoryRouter><Daily /></MemoryRouter>);
    await screen.findByLabelText(/Your answer/i);
    expect(screen.getByRole("button", { name: /submit answer/i })).toBeDisabled();
  });
});

describe("reminders", () => {
  it("shows an in-app reminder in the evening while today is open", async () => {
    // The reminder state now arrives with today's question, in one request.
    api.dailyToday.mockResolvedValue({ ...challengeFixture(), remind_now: true, email_opt_in: false });
    render(<MemoryRouter><Daily /></MemoryRouter>);
    expect(await screen.findByText(/still open/i)).toBeInTheDocument();
  });

  it("turns email reminders on through the server", async () => {
    api.dailyToday.mockResolvedValue(challengeFixture());
    render(<MemoryRouter><Daily /></MemoryRouter>);
    const box = await screen.findByRole("checkbox", { name: /Email me an evening reminder/i });
    expect(box).not.toBeChecked();
    fireEvent.click(box);
    await waitFor(() => expect(api.remindersSet).toHaveBeenCalledWith(true));
  });
});


describe("skills to improve and learn a role", () => {
  it("lists the skills to improve, most urgent first, with the reason and the next task", async () => {
    render(<MemoryRouter><Plan /></MemoryRouter>);
    const list = await screen.findByRole("region", { name: "Skills to improve" });
    expect(list).toHaveTextContent("High");
    expect(list).toHaveTextContent("Not shown yet. Almost every data role needs it.");
    expect(list).toHaveTextContent("Complete the SQL lessons");
  });

  it("the learn card builds a full roadmap from scratch in a separate mode", async () => {
    // the server answers a scratch request with a scratch plan
    api.planGet.mockImplementation(async (role, mode = "gap") => ({ ...planFixture(), role, mode }));
    render(<MemoryRouter><Plan /></MemoryRouter>);
    await screen.findByRole("region", { name: "Learn a role from scratch" });
    fireEvent.change(screen.getByLabelText("Role to learn"), { target: { value: "Backend Engineer" } });
    fireEvent.click(screen.getByRole("button", { name: "Build full roadmap" }));
    await waitFor(() => expect(api.planGet).toHaveBeenCalledWith("Backend Engineer", "scratch"));
    expect(await screen.findByText(/Learning from scratch: Backend Engineer/)).toBeInTheDocument();
  });

  it("the learn card can return to the gap plan", async () => {
    render(<MemoryRouter><Plan /></MemoryRouter>);
    await screen.findByRole("region", { name: "Learn a role from scratch" });
    fireEvent.click(screen.getByRole("button", { name: "Build full roadmap" }));
    fireEvent.click(await screen.findByRole("button", { name: "Back to my gap plan" }));
    await waitFor(() => expect(api.planGet).toHaveBeenLastCalledWith("Full-Stack Developer", "gap"));
  });
});
