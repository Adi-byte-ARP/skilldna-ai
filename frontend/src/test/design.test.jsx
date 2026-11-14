import React from "react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { MemoryRouter, Routes, Route } from "react-router-dom";
import Button from "../ui/Button";
import Badge from "../ui/Badge";
import EmptyState from "../ui/EmptyState";
import { SkeletonLines } from "../ui/Skeleton";
import ErrorBoundary from "../ui/ErrorBoundary";
import { ToastProvider } from "../ui/Toast";
import { useToast } from "../ui/useToast";
import ThemeToggle from "../ui/ThemeToggle";
import AppHeader from "../layout/AppHeader";
import { AuthContext } from "../context/authContextValue";
import { applyTheme, readPreference, resolveTheme, setPreference, THEME_KEY } from "../lib/theme";

beforeEach(() => {
  localStorage.clear();
  document.documentElement.removeAttribute("data-theme");
});

describe("primitives", () => {
  it("button is a button by default and carries its variant", () => {
    render(<Button variant="ghost">Go</Button>);
    const btn = screen.getByRole("button", { name: "Go" });
    expect(btn).toHaveAttribute("type", "button");
    expect(btn.className).toContain("border-line");
  });

  it("badge shows its text in the chosen tone", () => {
    render(<Badge tone="coral">2 violations</Badge>);
    expect(screen.getByText("2 violations").className).toContain("text-signal-coral");
  });

  it("empty state explains what to do next", () => {
    render(<EmptyState title="No sessions yet" body="Start one." action={<button type="button">Start</button>} />);
    expect(screen.getByText("No sessions yet")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Start" })).toBeInTheDocument();
  });

  it("skeleton announces that content is loading", () => {
    render(<SkeletonLines lines={2} />);
    expect(screen.getByRole("status", { name: "Loading" })).toBeInTheDocument();
  });
});

describe("error boundary", () => {
  function Boom() {
    throw new Error("broken page");
  }

  it("shows a recoverable message instead of a blank screen", () => {
    const spy = vi.spyOn(console, "error").mockImplementation(() => {});
    render(<ErrorBoundary resetKey="/a"><Boom /></ErrorBoundary>);
    expect(screen.getByRole("alert")).toHaveTextContent("This page could not be shown.");
    expect(screen.getByRole("button", { name: "Try again" })).toBeInTheDocument();
    spy.mockRestore();
  });

  it("clears the error when the route changes", () => {
    const spy = vi.spyOn(console, "error").mockImplementation(() => {});
    const { rerender } = render(<ErrorBoundary resetKey="/a"><Boom /></ErrorBoundary>);
    rerender(<ErrorBoundary resetKey="/b"><p>Other page</p></ErrorBoundary>);
    expect(screen.getByText("Other page")).toBeInTheDocument();
    spy.mockRestore();
  });
});

describe("toasts", () => {
  function Trigger() {
    const toast = useToast();
    return (
      <>
        <button type="button" onClick={() => toast.show("Saved your answer", "success")}>save</button>
        <button type="button" onClick={() => toast.show("Could not save", "error")}>fail</button>
      </>
    );
  }

  it("announces success politely and errors assertively", () => {
    render(<ToastProvider><Trigger /></ToastProvider>);
    fireEvent.click(screen.getByRole("button", { name: "save" }));
    expect(screen.getByRole("status")).toHaveTextContent("Saved your answer");
    fireEvent.click(screen.getByRole("button", { name: "fail" }));
    expect(screen.getByRole("alert")).toHaveTextContent("Could not save");
  });

  it("can be dismissed", () => {
    render(<ToastProvider><Trigger /></ToastProvider>);
    fireEvent.click(screen.getByRole("button", { name: "save" }));
    fireEvent.click(screen.getByRole("button", { name: "Dismiss" }));
    expect(screen.queryByText("Saved your answer")).not.toBeInTheDocument();
  });
});

describe("theme", () => {
  it("defaults to following the system", () => {
    expect(readPreference()).toBe("system");
  });

  it("applies a chosen theme to the document and remembers it", () => {
    setPreference("dark");
    expect(document.documentElement.getAttribute("data-theme")).toBe("dark");
    expect(localStorage.getItem(THEME_KEY)).toBe("dark");
    setPreference("light");
    expect(document.documentElement.getAttribute("data-theme")).toBe("light");
  });

  it("returns to the system choice by forgetting the stored value", () => {
    setPreference("dark");
    setPreference("system");
    expect(localStorage.getItem(THEME_KEY)).toBeNull();
    expect(["light", "dark"]).toContain(resolveTheme("system"));
  });

  it("the toggle switches the theme", () => {
    render(<ThemeToggle />);
    fireEvent.click(screen.getByRole("radio", { name: "Dark theme" }));
    expect(document.documentElement.getAttribute("data-theme")).toBe("dark");
    expect(screen.getByRole("radio", { name: "Dark theme" })).toHaveAttribute("aria-checked", "true");
  });

  it("applyTheme can be called without a stored value", () => {
    applyTheme("light");
    expect(document.documentElement.getAttribute("data-theme")).toBe("light");
  });
});

describe("app header", () => {
  const auth = { user: { email: "someone@gmail.com" }, logout: vi.fn() };

  function renderAt(path, value = auth) {
    return render(
      <AuthContext.Provider value={value}>
        <MemoryRouter initialEntries={[path]}>
          <Routes>
            <Route path="*" element={<AppHeader />} />
          </Routes>
        </MemoryRouter>
      </AuthContext.Provider>
    );
  }

  it("lists the four practice areas", () => {
    renderAt("/app");
    for (const name of ["Dashboard", "Improve plan", "Daily challenge", "Mock test"]) {
      expect(screen.getByRole("link", { name })).toBeInTheDocument();
    }
  });

  it("marks the current page", () => {
    renderAt("/app/plan");
    expect(screen.getByRole("link", { name: "Improve plan" })).toHaveAttribute("aria-current", "page");
    expect(screen.getByRole("link", { name: "Dashboard" })).not.toHaveAttribute("aria-current", "page");
  });

  it("keeps the header to navigation; the avatar opens the profile, where log out lives", () => {
    renderAt("/app", { user: auth.user, logout: vi.fn() });
    expect(screen.queryByRole("button", { name: "Log out" })).not.toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Your profile" }).getAttribute("href")).toMatch(/\/app\/profile$/);
  });

  it("shows no profile link when there is no signed-in user (the exam screens)", () => {
    renderAt("/app/mock", null);
    expect(screen.queryByRole("link", { name: "Your profile" })).not.toBeInTheDocument();
  });
});
