import React from "react";
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, fireEvent, waitFor, act } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";

vi.mock("../lib/api", () => ({
  api: {
    mockSessions: vi.fn(),
    interviewStart: vi.fn(),
    interviewAnswer: vi.fn(),
    mockRoles: vi.fn(),
    mockStart: vi.fn(),
    mockEvent: vi.fn(),
    mockAnswer: vi.fn(),
    mockSubmit: vi.fn(),
  },
}));

import { api } from "../lib/api";
import MockExam from "../pages/MockExam";

const ROLES = {
  roles: ["Backend Engineer", "Data / ML Engineer"],
  kinds: ["test", "interview"],
  max_violations: 3,
  violation_types: { window_blur: "Clicked outside the exam window", tab_hidden: "Switched tab" },
};

function sessionFixture(overrides = {}) {
  return {
    id: 7,
    kind: "test",
    role: "Backend Engineer",
    status: "active",
    time_limit_seconds: 900,
    remaining_seconds: 900,
    deadline_at: new Date(Date.now() + 900_000).toISOString(),
    max_violations: 3,
    violations: [],
    answered_ids: [],
    questions: [
      { id: "q1", kind: "mcq", skill: "python", question: "First question?", options: ["a", "b", "c", "d"] },
      { id: "q2", kind: "mcq", skill: "sql", question: "Second question?", options: ["w", "x", "y", "z"] },
    ],
    ...overrides,
  };
}

function fakeStream() {
  const track = { stop: vi.fn(), addEventListener: vi.fn(), removeEventListener: vi.fn() };
  return { getTracks: () => [track], getVideoTracks: () => [track] };
}

function renderPage() {
  return render(
    <MemoryRouter>
      <MockExam />
    </MemoryRouter>
  );
}

async function goToExam() {
  renderPage();
  await waitFor(() => expect(api.mockRoles).toHaveBeenCalled());
  for (const box of screen.getAllByRole("checkbox")) fireEvent.click(box);
  fireEvent.click(screen.getByRole("button", { name: /continue to camera check/i }));
  await screen.findByRole("button", { name: /start in fullscreen/i });
  fireEvent.click(screen.getByRole("button", { name: /start in fullscreen/i }));
  await screen.findByText(/Question 1 of 2/i);
  // Monitoring listeners are attached in an effect that runs after the DOM commit.
  // Flush it so events fired by the test reach the listeners, as they would for a user.
  await act(async () => {});
}

beforeEach(() => {
  vi.clearAllMocks();
  api.mockRoles.mockResolvedValue(ROLES);
  api.mockSessions.mockResolvedValue([]);
  api.mockStart.mockResolvedValue(sessionFixture());
  api.mockEvent.mockResolvedValue(sessionFixture());
  api.mockAnswer.mockResolvedValue(sessionFixture({ answered_ids: ["q1"] }));
  api.mockSubmit.mockResolvedValue(sessionFixture({ status: "submitted", result: { score: 50, correct: 1, total: 2, feedback: ["ok"] } }));
  navigator.mediaDevices = { getUserMedia: vi.fn().mockResolvedValue(fakeStream()) };
  document.documentElement.requestFullscreen = vi.fn().mockResolvedValue(undefined);
  document.exitFullscreen = vi.fn().mockResolvedValue(undefined);
  Object.defineProperty(document, "fullscreenElement", { configurable: true, get: () => null });
});

afterEach(() => {
  vi.useRealTimers();
});

describe("mock exam setup and consent", () => {
  it("keeps Continue disabled until all three consents are ticked", async () => {
    renderPage();
    const button = await screen.findByRole("button", { name: /continue to camera check/i });
    expect(button).toBeDisabled();
    const boxes = screen.getAllByRole("checkbox");
    fireEvent.click(boxes[0]);
    fireEvent.click(boxes[1]);
    expect(button).toBeDisabled();
    fireEvent.click(boxes[2]);
    expect(button).toBeEnabled();
  });

  it("explains that the camera is required and blocks the exam when camera access is denied", async () => {
    navigator.mediaDevices.getUserMedia.mockRejectedValueOnce(new Error("denied"));
    renderPage();
    await waitFor(() => expect(api.mockRoles).toHaveBeenCalled());
    for (const box of screen.getAllByRole("checkbox")) fireEvent.click(box);
    fireEvent.click(await screen.findByRole("button", { name: /continue to camera check/i }));
    expect(await screen.findByText(/Camera and microphone access are required/i)).toBeInTheDocument();
    expect(api.mockStart).not.toHaveBeenCalled();
  });
});

describe("mock exam monitoring", () => {
  it("starts the session in fullscreen and shows the first question", async () => {
    await goToExam();
    expect(document.documentElement.requestFullscreen).toHaveBeenCalled();
    expect(api.mockStart).toHaveBeenCalledWith("test", "Backend Engineer");
    expect(screen.getByText("First question?")).toBeInTheDocument();
  });

  it("labels a test as a test and offers test navigation", async () => {
    await goToExam();
    expect(screen.getByText(/Mock test · Backend Engineer/)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Lock answer and continue" })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /previous/i })).not.toBeInTheDocument();
  });

  it("reports window blur to the server and shows a warning with the count", async () => {
    api.mockEvent.mockResolvedValueOnce(
      sessionFixture({ violations: [{ type: "window_blur", label: "Clicked outside the exam window", at: "t" }] })
    );
    await goToExam();
    fireEvent(window, new Event("blur"));
    await waitFor(() => expect(api.mockEvent).toHaveBeenCalledWith(7, "window_blur"));
    expect(await screen.findByText(/Warning 1 of 3/i)).toBeInTheDocument();
  });

  it("blocks copy and reports it", async () => {
    await goToExam();
    const event = new Event("copy", { cancelable: true });
    document.dispatchEvent(event);
    expect(event.defaultPrevented).toBe(true);
    await waitFor(() => expect(api.mockEvent).toHaveBeenCalledWith(7, "copy"));
  });

  it("blocks Ctrl+C style shortcuts and reports them", async () => {
    await goToExam();
    const event = new KeyboardEvent("keydown", { key: "c", ctrlKey: true, cancelable: true });
    window.dispatchEvent(event);
    expect(event.defaultPrevented).toBe(true);
    await waitFor(() => expect(api.mockEvent).toHaveBeenCalledWith(7, "shortcut_blocked"));
  });

  it("locks the screen with an overlay when fullscreen is left", async () => {
    await goToExam();
    Object.defineProperty(document, "fullscreenElement", { configurable: true, get: () => null });
    fireEvent(document, new Event("fullscreenchange"));
    expect(await screen.findByText(/You left fullscreen/i)).toBeInTheDocument();
    expect(api.mockEvent).toHaveBeenCalledWith(7, "fullscreen_exit");
  });

  it("moves to the result screen when the server ends the session after the third violation", async () => {
    api.mockEvent.mockResolvedValueOnce(
      sessionFixture({
        status: "terminated",
        violations: [{ type: "window_blur" }, { type: "copy" }, { type: "tab_hidden" }],
        result: { score: 25, correct: 0, total: 2, terminated: true, feedback: ["You answered 0 of 2 correctly."] },
      })
    );
    await goToExam();
    fireEvent(window, new Event("blur"));
    expect(await screen.findByText(/Session ended/i)).toBeInTheDocument();
    expect(screen.getByText(/You answered 0 of 2 correctly/i)).toBeInTheDocument();
  });
});

describe("one action is one violation", () => {
  it("does not count a window blur that follows leaving fullscreen as a second violation", async () => {
    await goToExam();
    Object.defineProperty(document, "fullscreenElement", { configurable: true, get: () => null });
    fireEvent(document, new Event("fullscreenchange"));
    fireEvent(window, new Event("blur"));
    await waitFor(() => expect(api.mockEvent).toHaveBeenCalledWith(7, "fullscreen_exit"));
    const types = api.mockEvent.mock.calls.map((c) => c[1]);
    expect(types).toContain("fullscreen_exit");
    expect(types).not.toContain("window_blur");
  });
});

describe("AI interview from the setup screen", () => {
  it("starts an AI interview for the chosen role and shows the first question", async () => {
    api.interviewStart.mockResolvedValue({
      id: 3, role: "Backend Engineer", status: "active", turns: [], target_turns: 5, overall: null,
      current_question: { kind: "opening", question: "Tell me about yourself.", skill: null, keywords: [] },
    });
    renderPage();
    fireEvent.click(await screen.findByRole("button", { name: /AI interview/i }));
    fireEvent.click(await screen.findByRole("button", { name: "Start interview" }));
    expect((await screen.findAllByText("Tell me about yourself.")).length).toBeGreaterThan(0);
    expect(api.interviewStart).toHaveBeenCalledWith("Backend Engineer");
  });
});

