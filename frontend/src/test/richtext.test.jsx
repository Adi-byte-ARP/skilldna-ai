import React from "react";
import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import RichText from "../ui/RichText";
import { plainText } from "../lib/plainText";

describe("question text", () => {
  it("shows backtick segments as inline code without the backticks", () => {
    const { container } = render(<p><RichText text="What does `'abc'.upper()` return?" /></p>);
    expect(container.querySelector("code")).toHaveTextContent("'abc'.upper()");
    expect(container.textContent).toBe("What does 'abc'.upper() return?");
  });

  it("leaves text without code marks alone", () => {
    render(<p><RichText text="Describe a project you built." /></p>);
    expect(screen.getByText("Describe a project you built.")).toBeInTheDocument();
  });

  it("strips the marks for read-aloud", () => {
    expect(plainText("Use `git rebase` here")).toBe("Use git rebase here");
  });
});
