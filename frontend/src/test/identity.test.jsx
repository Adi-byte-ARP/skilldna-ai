import React from "react";
import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import IdentityPanel from "../components/IdentityPanel";
import Icon from "../ui/Icon";

const docs = [
  { id: 1, source: "resume", file: "cv.pdf", status: "processed", name_read: "Aditya R Pattar" },
  { id: 2, source: "certificate", file: "course.png", status: "processed", name_read: "ADITYA PATTAR" },
  { id: 3, source: "resume", file: "other.pdf", status: "name_mismatch", name_read: "Rahul Pattar" },
  { id: 4, source: "linkedin", file: "li.png", status: "name_unverified", name_read: null },
];

describe("identity panel", () => {
  it("says how many documents belong to the account holder", () => {
    render(<IdentityPanel documents={docs} accountName="Aditya R Pattar" loading={false} />);
    expect(screen.getByText("2 documents belong to Aditya R Pattar")).toBeInTheDocument();
  });

  it("marks every document with the reason it was or was not counted", () => {
    render(<IdentityPanel documents={docs} accountName="Aditya R Pattar" loading={false} />);
    expect(screen.getAllByText("Counted")).toHaveLength(2);
    expect(screen.getByText("Different name")).toBeInTheDocument();
    expect(screen.getByText("No name found")).toBeInTheDocument();
    expect(screen.getByText("LinkedIn uploads must show your name and Skills section in the same file.")).toBeInTheDocument();
    expect(screen.getByText("Name read: Rahul Pattar")).toBeInTheDocument();
  });

  it("explains the rule when nothing is counted yet", () => {
    render(<IdentityPanel documents={[]} accountName="Aditya R Pattar" loading={false} />);
    expect(screen.getByText("No document is counted yet")).toBeInTheDocument();
    expect(screen.getByText(/Only documents that carry your name are counted/)).toBeInTheDocument();
  });
});

describe("icons", () => {
  it("are decorative unless given a title", () => {
    const { container } = render(<Icon name="check" />);
    expect(container.querySelector("svg")).toHaveAttribute("aria-hidden", "true");
  });
  it("are announced when given a title", () => {
    render(<Icon name="lock" title="Locked" />);
    expect(screen.getByRole("img", { name: "Locked" })).toBeInTheDocument();
  });
});
