import React from "react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";

vi.mock("../lib/api", () => ({
  api: {
    interviewStart: vi.fn(),
    interviewAnswer: vi.fn(),
    interviewEvent: vi.fn(),
    profileGet: vi.fn(),
    profileRecommendations: vi.fn(),
    profileSetTargetRole: vi.fn(),
    profileSettings: vi.fn(),
    profileExport: vi.fn(),
    assistantAction: vi.fn(),
    assistantChat: vi.fn(),
  },
}));

import { api } from "../lib/api";
import AIInterview from "../components/AIInterview";
import HelpBot from "../components/HelpBot";
import Profile from "../pages/Profile";
import { ToastProvider } from "../ui/Toast";

// The interview opens on its set-up screen; the candidate starts it.
async function startInterview() {
  fireEvent.click(await screen.findByRole("button", { name: "Start interview" }));
}

const started = {
  id: 4, role: "Backend Engineer", status: "active", turns: [], target_turns: 3, overall: null,
  integrity: { points: 0, flags: [] },
  current_question: { kind: "opening", question: "Tell me about yourself.", skill: null, keywords: [] },
};

beforeEach(() => {
  vi.clearAllMocks();
  api.interviewStart.mockResolvedValue(started);
  api.interviewEvent.mockResolvedValue({ auto_submitted: false, integrity: { points: 3, flags: [{ type: "tab_hidden", label: "Switched to another tab" }] } });
});

describe("AI interview integrity", () => {
  it("reports a paste attempt to the server and blocks the paste", async () => {
    render(<AIInterview role="Backend Engineer" />);
    await startInterview();
    const box = await screen.findByRole("textbox", { name: "Your answer" });
    const event = new Event("paste", { cancelable: true, bubbles: true });
    box.dispatchEvent(event);
    expect(event.defaultPrevented).toBe(true);
    await waitFor(() => expect(api.interviewEvent).toHaveBeenCalledWith(4, "paste"));
  });

  it("shows the automatic submission and the reason when the server ends the interview", async () => {
    api.interviewAnswer.mockResolvedValue({
      ...started, done: true, auto_submitted: true, feedback: "Submitted.", current_question: null,
      integrity: { points: 6, flags: [{ type: "answer_burst", label: "Answer arrived too fast to be typed" }] },
      report: { overall: 40, verdict: "Not yet.", strengths: [], gaps: ["sql"], engine: "rule-based" },
    });
    render(<AIInterview role="Backend Engineer" />);
    await startInterview();
    fireEvent.change(await screen.findByRole("textbox", { name: "Your answer" }), { target: { value: "a long answer" } });
    fireEvent.click(screen.getByRole("button", { name: "Send answer" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("Submitted automatically");
    expect(screen.getByRole("alert")).toHaveTextContent("Answer arrived too fast to be typed");
  });

  it("sends how long the answer took", async () => {
    api.interviewAnswer.mockResolvedValue({ ...started, done: false, auto_submitted: false, feedback: "Ok.", report: null,
      current_question: { kind: "question", question: "Next?", skill: "sql", keywords: [] },
      integrity: { points: 0, flags: [] } });
    render(<AIInterview role="Backend Engineer" />);
    await startInterview();
    fireEvent.change(await screen.findByRole("textbox", { name: "Your answer" }), { target: { value: "answer" } });
    fireEvent.click(screen.getByRole("button", { name: "Send answer" }));
    await waitFor(() => expect(api.interviewAnswer).toHaveBeenCalled());
    const [, , seconds] = api.interviewAnswer.mock.calls[0];
    expect(typeof seconds).toBe("number");
  });
});

describe("personal assistant", () => {
  it("offers one-tap actions and shows the week schedule", async () => {
    api.assistantAction.mockResolvedValue({ reply: "Your next few days: Mon: Python.", source: "plan",
      data: { schedule: [{ day: "2026-10-12", tasks: [{ skill: "Python", task: "Read the tutorial" }] }] } });
    render(<HelpBot />);
    fireEvent.click(screen.getByRole("button", { name: "Open the SkillDNA helper" }));
    fireEvent.click(screen.getByRole("button", { name: "Plan my week" }));
    expect(await screen.findByText("Your next few days: Mon: Python.")).toBeInTheDocument();
    expect(api.assistantAction).toHaveBeenCalledWith("week");
  });

  it("explains what to do when the action needs sign-in or permission", async () => {
    api.assistantAction.mockRejectedValue(new Error("Turn on 'let the assistant use my progress' in your profile to use this."));
    render(<HelpBot />);
    fireEvent.click(screen.getByRole("button", { name: "Open the SkillDNA helper" }));
    fireEvent.click(screen.getByRole("button", { name: "What's next?" }));
    expect(await screen.findByText(/let the assistant use my progress/)).toBeInTheDocument();
  });
});

describe("profile page", () => {
  const profile = {
    name: "Priya Nair", email: "priya@gmail.com", target_role: null, effective_role: "Data Analyst",
    assistant_context: true, motto: "Be honest with yourself: a skill counts when you can show it.",
    summary: { overall: 42, tier: "Developing", skills: 5, strengths: ["python"], gaps: ["sql"] },
    recommendations: [{ role: "Data Analyst", fit: 61, reason: "You already show 5 of 10 skills." }],
    stats: { streak: 2, daily_points: 20, plan_snapshots: 1, mock_sessions: 0, interviews_finished: 0, phases_passed: 0 },
    achievements: [{ id: "first-evidence", title: "First evidence", detail: "Your first counted upload.", earned: true }],
    history: [{ at: "2026-10-12", kind: "daily", title: "Daily challenge · sql", detail: "correct · +10 points", tone: "teal" }],
  };

  it("shows the honest note, the summary, recommended roles and achievements", async () => {
    api.profileGet.mockResolvedValue(profile);
    api.profileRecommendations.mockResolvedValue([]);
    render(<ToastProvider><MemoryRouter><Profile /></MemoryRouter></ToastProvider>);
    expect(await screen.findByRole("heading", { name: "Priya Nair" })).toBeInTheDocument();
    expect(screen.getByText(profile.motto)).toBeInTheDocument();
    expect(screen.getAllByText("Data Analyst").length).toBeGreaterThan(0);
    expect(screen.getByText("61% fit")).toBeInTheDocument();
    expect(screen.getByText("First evidence")).toBeInTheDocument();
  });

  it("the history tab lists what happened across features", async () => {
    api.profileGet.mockResolvedValue(profile);
    api.profileRecommendations.mockResolvedValue([]);
    render(<ToastProvider><MemoryRouter><Profile /></MemoryRouter></ToastProvider>);
    await screen.findByRole("heading", { name: "Priya Nair" });
    fireEvent.click(screen.getByRole("button", { name: "History" }));
    expect(screen.getByText("Daily challenge · sql")).toBeInTheDocument();
  });

  it("the assistant switch can be turned off from settings", async () => {
    api.profileGet.mockResolvedValue(profile);
    api.profileRecommendations.mockResolvedValue([]);
    api.profileSettings.mockResolvedValue({ assistant_context: false });
    render(<ToastProvider><MemoryRouter><Profile /></MemoryRouter></ToastProvider>);
    await screen.findByRole("heading", { name: "Priya Nair" });
    fireEvent.click(screen.getByRole("button", { name: "Settings" }));
    fireEvent.click(screen.getByRole("checkbox", { name: /Let the assistant use my progress/ }));
    await waitFor(() => expect(api.profileSettings).toHaveBeenCalledWith(false));
  });
});
