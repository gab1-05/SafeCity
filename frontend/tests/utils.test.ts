import { describe, expect, it } from "vitest";
import { cn, formatBytes, timeAgo } from "@/lib/utils";

describe("cn", () => {
  it("merges class names", () => {
    expect(cn("a", "b")).toBe("a b");
  });

  it("dedupes tailwind conflicts", () => {
    const result = cn("px-2", "px-4");
    expect(result).toBe("px-4");
  });
});

describe("timeAgo", () => {
  it("returns just now for fresh timestamps", () => {
    expect(timeAgo(new Date().toISOString())).toBe("just now");
  });

  it("returns minutes for recent timestamps", () => {
    const fiveMinAgo = new Date(Date.now() - 5 * 60_000).toISOString();
    expect(timeAgo(fiveMinAgo)).toBe("5 minutes ago");
  });

  it("handles null", () => {
    expect(timeAgo(null)).toBe("—");
  });
});

describe("formatBytes", () => {
  it("formats KB and MB", () => {
    expect(formatBytes(500)).toBe("500 B");
    expect(formatBytes(2048)).toBe("2.0 KB");
    expect(formatBytes(5 * 1024 * 1024)).toBe("5.0 MB");
  });
});
