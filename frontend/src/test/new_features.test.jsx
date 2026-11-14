import React from "react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";

vi.mock("../lib/api", () => ({
  api: {
    assistantChat: vi.fn(),
    interviewStart: vi.fn(),
    interviewAnswer: vi.fn(),
    interviewEvent: vi.fn().mockResolvedValue({ auto_submitted: false, integrity: { points: 0, flags: [] } }),
    planPhaseTest: vi.fn(),
    planPhaseSubmit: vi.fn(),
    mockRoles: vi.fn(),
    planGet: vi.fn(),
    planHistory: vi.fn(),
    planToggleTask: vi.fn(),
  },
}));

import { api } from "../lib/api";
import HelpBot from "../components/HelpBot";
import AIInterview from "../components/AIInterview";
import PhaseTest from "../components/PhaseTest";

// The interview opens on its set-up screen; the candidate starts it.
async function startInterview() {
  fireEvent.click(await screen.findByRole("button", { name: "Start interview" }));
}

beforeEach(() => {
  vi.clearAllMocks();
});

describe("help bubble", () => {
  it("opens from the corner button and answers a question", async () => {
    api.assistantChat.mockResolvedValue({ reply: "Scores use four sources.", suggestions: ["How do I upload?"] });
    render(<HelpBot />);
    fireEvent.click(screen.getByRole("button", { name: "Open the SkillDNA helper" }));
    expect(screen.getByRole("region", { name: "SkillDNA helper" })).toBeInTheDocument();
    fireEvent.change(screen.getByRole("textbox", { name: "Ask the helper" }), { target: { value: "How is my score calculated?" } });
    fireEvent.click(screen.getByRole("button", { name: "Send" }));
    expect(await screen.findByText("Scores use four sources.")).toBeInTheDocument();
    expect(api.assistantChat).toHaveBeenCalledWith("How is my score calculated?", expect.any(Array));
  });

  it("can be closed again", () => {
    render(<HelpBot />);
    fireEvent.click(screen.getByRole("button", { name: "Open the SkillDNA helper" }));
    fireEvent.click(screen.getByRole("button", { name: "Close helper" }));
    expect(screen.queryByRole("region", { name: "SkillDNA helper" })).not.toBeInTheDocument();
  });
});

describe("AI interview chat", () => {
  const first = {
    id: 9, role: "Backend Engineer", status: "active", turns: [], target_turns: 2, overall: null,
    integrity: { points: 0, flags: [] },
    current_question: { kind: "opening", question: "Tell me about yourself.", skill: null, keywords: [] },
  };

  it("blocks paste in the answer box", async () => {
    api.interviewStart.mockResolvedValue(first);
    render(<AIInterview role="Backend Engineer" />);
    await startInterview();
    const box = await screen.findByRole("textbox", { name: "Your answer" });
    const pasted = new Event("paste", { bubbles: true, cancelable: true });
    box.dispatchEvent(pasted);
    expect(pasted.defaultPrevented).toBe(true);
  });

  it("sends an answer, shows the feedback and the next question", async () => {
    api.interviewStart.mockResolvedValue(first);
    api.interviewAnswer.mockResolvedValue({
      ...first,
      turns: [{ question: "Tell me about yourself.", answer: "x", score: 70, feedback: "Good start." }],
      current_question: { kind: "question", question: "How do you cache?", skill: "redis", keywords: [] },
      feedback: "Good start.", done: false, report: null, auto_submitted: false, integrity: { points: 0, flags: [] },
    });
    render(<AIInterview role="Backend Engineer" />);
    await startInterview();
    fireEvent.change(await screen.findByRole("textbox", { name: "Your answer" }), { target: { value: "I built a service" } });
    fireEvent.click(screen.getByRole("button", { name: "Send answer" }));
    expect((await screen.findAllByText("How do you cache?")).length).toBeGreaterThan(0);
    expect(screen.getAllByText("Good start.").length).toBeGreaterThan(0);
    expect(api.interviewAnswer).toHaveBeenCalledWith(9, "I built a service", expect.any(Number));
  });

  it("ends with a report", async () => {
    api.interviewStart.mockResolvedValue(first);
    api.interviewAnswer.mockResolvedValue({
      ...first, done: true, feedback: "Done.", current_question: null, auto_submitted: false, integrity: { points: 0, flags: [] },
      report: { overall: 80, verdict: "Ready for a first interview round.", strengths: ["python"], gaps: [], engine: "rule-based" },
    });
    render(<AIInterview role="Backend Engineer" />);
    await startInterview();
    fireEvent.change(await screen.findByRole("textbox", { name: "Your answer" }), { target: { value: "answer" } });
    fireEvent.click(screen.getByRole("button", { name: "Send answer" }));
    expect(await screen.findByText("Interview report")).toBeInTheDocument();
    expect(screen.getByText("Ready for a first interview round.")).toBeInTheDocument();
  });
});

describe("phase test", () => {
  const questions = [
    { id: "q1", question: "Which keyword declares a constant?", options: ["var", "const", "let"] },
    { id: "q2", question: "What does JSON.parse return?", options: ["a string", "a value"] },
  ];

  it("keeps submit disabled until every question is answered", async () => {
    api.planPhaseTest.mockResolvedValue({ phase_index: 0, pass_score: 60, questions });
    render(<PhaseTest index={0} role="Backend Engineer" />);
    const submit = await screen.findByRole("button", { name: "Submit test" });
    expect(submit).toBeDisabled();
    fireEvent.click(screen.getByRole("radio", { name: "const" }));
    expect(submit).toBeDisabled();
    fireEvent.click(screen.getByRole("radio", { name: "a value" }));
    expect(submit).toBeEnabled();
  });

  it("a pass tells the user the next phase is open", async () => {
    api.planPhaseTest.mockResolvedValue({ phase_index: 0, pass_score: 60, questions });
    api.planPhaseSubmit.mockResolvedValue({ passed: true, score: 100, unlocked_next: true });
    const onPassed = vi.fn();
    render(<PhaseTest index={0} role="Backend Engineer" onPassed={onPassed} />);
    fireEvent.click(await screen.findByRole("radio", { name: "const" }));
    fireEvent.click(screen.getByRole("radio", { name: "a value" }));
    fireEvent.click(screen.getByRole("button", { name: "Submit test" }));
    expect(await screen.findByText(/The next phase is now open/)).toBeInTheDocument();
    await waitFor(() => expect(onPassed).toHaveBeenCalled());
  });

  it("a fail says what the pass mark is and allows a retry", async () => {
    api.planPhaseTest.mockResolvedValue({ phase_index: 0, pass_score: 60, questions });
    api.planPhaseSubmit.mockResolvedValue({ passed: false, score: 40, unlocked_next: false });
    render(<PhaseTest index={0} role="Backend Engineer" />);
    fireEvent.click(await screen.findByRole("radio", { name: "var" }));
    fireEvent.click(screen.getByRole("radio", { name: "a string" }));
    fireEvent.click(screen.getByRole("button", { name: "Submit test" }));
    expect(await screen.findByText(/You need 60% to pass/)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Submit test" })).toBeEnabled();
  });
});
