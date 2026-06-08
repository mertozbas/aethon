import { describe, it, expect, vi, beforeEach } from "vitest";

const mocks = vi.hoisted(() => ({
  enqueueLogEntry: vi.fn(),
  getConfig: vi.fn(() => ({ logs: { llm_only: true } })),
}));

vi.mock("@src/logs/entry.js", () => ({
  enqueueLogEntry: mocks.enqueueLogEntry,
}));

vi.mock("@src/config.js", () => ({
  getConfig: mocks.getConfig,
}));

import { isKnownLlmPath, logCapture } from "@src/middleware/log-capture.js";

function createContext(path = "/v1/messages", extraGet: Record<string, unknown> = {}) {
  const headers = new Map<string, string>();
  return {
    get: vi.fn((key: string) => {
      if (key === "requestId") return "req-123";
      return extraGet[key];
    }),
    header: vi.fn((key: string, value: string) => {
      headers.set(key, value);
    }),
    req: { method: "POST", path },
    res: { status: 201 },
  } as unknown as Parameters<typeof logCapture>[0];
}

describe("logCapture middleware", () => {
  beforeEach(() => {
    mocks.enqueueLogEntry.mockClear();
    mocks.getConfig.mockReturnValue({ logs: { llm_only: true } });
    vi.useFakeTimers();
    vi.setSystemTime(new Date("2026-04-15T00:00:00.000Z"));
  });

  it("recognizes known LLM paths", () => {
    expect(isKnownLlmPath("/v1/chat/completions")).toBe(true);
    expect(isKnownLlmPath("/v1/messages")).toBe(true);
    expect(isKnownLlmPath("/v1beta/models/gemini-2.5-pro:generateContent")).toBe(true);
    expect(isKnownLlmPath("/admin/settings")).toBe(false);
  });

  it("enqueues an ingress log for LLM paths", async () => {
    const c = createContext("/v1/messages");
    const next = vi.fn(async () => {
      vi.setSystemTime(new Date("2026-04-15T00:00:00.025Z"));
    });

    await logCapture(c, next as never);

    expect(next).toHaveBeenCalledTimes(1);
    expect(mocks.enqueueLogEntry).toHaveBeenCalledWith(expect.objectContaining({
      requestId: "req-123",
      direction: "ingress",
      method: "POST",
      path: "/v1/messages",
      status: 201,
      latencyMs: 25,
    }));
  });

  it("skips unrelated requests in llm-only mode", async () => {
    const c = createContext("/admin/settings");

    await logCapture(c, vi.fn(async () => {}) as never);

    expect(mocks.enqueueLogEntry).not.toHaveBeenCalled();
  });

  it("captures forwarded requests even when path is unrelated", async () => {
    const c = createContext("/custom/provider", { logForwarded: true });

    await logCapture(c, vi.fn(async () => {}) as never);

    expect(mocks.enqueueLogEntry).toHaveBeenCalledOnce();
  });

  it("captures all requests when llm-only mode is disabled", async () => {
    mocks.getConfig.mockReturnValue({ logs: { llm_only: false } });
    const c = createContext("/admin/settings");

    await logCapture(c, vi.fn(async () => {}) as never);

    expect(mocks.enqueueLogEntry).toHaveBeenCalledOnce();
  });
});
