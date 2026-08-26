import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";

import { GenerationModeSelector } from "@/components/campaigns/GenerationModeSelector";

describe("GenerationModeSelector", () => {
  it("renders both mode options", () => {
    render(<GenerationModeSelector value="generate" onChange={vi.fn()} />);
    expect(screen.getByRole("radio", { name: /generate from my notes/i })).toBeInTheDocument();
    expect(screen.getByRole("radio", { name: /assist my writing/i })).toBeInTheDocument();
  });

  it("shows blog_full tagline for generate mode by default", () => {
    render(<GenerationModeSelector value="generate" onChange={vi.fn()} />);
    expect(screen.getByText("Turn rough notes into a full article and social posts")).toBeInTheDocument();
  });

  it("shows social_only tagline for generate mode when contentType=social_only", () => {
    render(<GenerationModeSelector value="generate" onChange={vi.fn()} contentType="social_only" />);
    expect(screen.getByText("Turn rough notes into a post for each platform")).toBeInTheDocument();
    expect(screen.queryByText("Turn rough notes into a full article and social posts")).not.toBeInTheDocument();
  });

  it("shows blog_full tagline for assist mode by default", () => {
    render(<GenerationModeSelector value="assist" onChange={vi.fn()} />);
    expect(screen.getByText("Keep my writing and only fix grammar and logic")).toBeInTheDocument();
  });

  it("shows social_only tagline for assist mode when contentType=social_only", () => {
    render(<GenerationModeSelector value="assist" onChange={vi.fn()} contentType="social_only" />);
    expect(screen.getByText("Keep my wording, just polish and fit each platform")).toBeInTheDocument();
    expect(screen.queryByText("Keep my writing and only fix grammar and logic")).not.toBeInTheDocument();
  });

  it("calls onChange when a different mode is selected", () => {
    const onChange = vi.fn();
    render(<GenerationModeSelector value="generate" onChange={onChange} />);
    fireEvent.click(screen.getByRole("radio", { name: /assist my writing/i }));
    expect(onChange).toHaveBeenCalledWith("assist");
  });

  it("marks the current value as checked", () => {
    render(<GenerationModeSelector value="assist" onChange={vi.fn()} />);
    expect(screen.getByRole("radio", { name: /assist my writing/i })).toBeChecked();
    expect(screen.getByRole("radio", { name: /generate from my notes/i })).not.toBeChecked();
  });

  it("renders for social_only without crashing", () => {
    const { container } = render(
      <GenerationModeSelector value="generate" onChange={vi.fn()} contentType="social_only" />
    );
    expect(container.querySelector("fieldset")).toBeInTheDocument();
    expect(container.querySelectorAll("input[type=radio]")).toHaveLength(2);
  });
});
