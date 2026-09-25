import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { SeverityBadge, StatusBadge } from "@/components/incident/Badges";

describe("StatusBadge", () => {
  it("renders resolved with success variant", () => {
    render(<StatusBadge status="resolved" />);
    const badge = screen.getByText("Resolved");
    expect(badge.className).toContain("text-success");
  });

  it("renders escalated with danger variant", () => {
    render(<StatusBadge status="escalated" />);
    const badge = screen.getByText("Escalated");
    expect(badge.className).toContain("text-danger");
  });

  it("renders submitted with warning variant", () => {
    render(<StatusBadge status="submitted" />);
    const badge = screen.getByText("Submitted");
    expect(badge.className).toContain("text-warning");
  });
});

describe("SeverityBadge", () => {
  it("labels emergencies distinctly", () => {
    render(<SeverityBadge severity="critical" critical />);
    expect(screen.getByText(/emergency/i)).toBeInTheDocument();
  });

  it("renders low severity muted", () => {
    render(<SeverityBadge severity="low" />);
    expect(screen.getByText("Low").className).toContain("text-muted-foreground");
  });
});
