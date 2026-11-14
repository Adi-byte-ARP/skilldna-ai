import React from "react";
import { describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen } from "@testing-library/react";
import UploadCard from "../components/UploadCard";

describe("UploadCard", () => {
  it("shows the backend's LinkedIn identity guidance", async () => {
    const message = "Upload your LinkedIn profile PDF, or a screenshot showing both your name and Skills section.";
    render(
      <UploadCard
        title="LinkedIn skills"
        accept="application/pdf"
        onSubmit={vi.fn().mockResolvedValue({
          status: "name_unverified",
          original_filename: "skills.pdf",
          error_message: message,
        })}
      />,
    );

    fireEvent.change(document.querySelector('input[type="file"]'), {
      target: { files: [new File(["skills"], "skills.pdf", { type: "application/pdf" })] },
    });

    expect(await screen.findByText(message)).toBeInTheDocument();
  });
});
