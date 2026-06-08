import { describe, it, expect, vi, beforeEach } from "vitest";
import { Hono } from "hono";

const mockConfig = vi.hoisted(() => ({
  getLocalConfigPath: vi.fn(() => "/tmp/test/local.yaml"),
  reloadAllConfigs: vi.fn(),
}));

const mockYaml = vi.hoisted(() => ({
  mutateYaml: vi.fn(),
}));

const store = vi.hoisted(() => ({
  list: vi.fn(),
  get: vi.fn(),
  clear: vi.fn(),
  setState: vi.fn(),
}));

vi.mock("@src/config.js", () => ({
  getLocalConfigPath: mockConfig.getLocalConfigPath,
  reloadAllConfigs: mockConfig.reloadAllConfigs,
}));

vi.mock("@src/utils/yaml-mutate.js", () => ({
  mutateYaml: mockYaml.mutateYaml,
}));

vi.mock("@src/logs/store.js", () => ({
  logStore: store,
}));

import { createLogRoutes } from "@src/routes/admin/logs.js";

describe("log routes", () => {
  beforeEach(() => {
    store.list.mockReset();
    store.get.mockReset();
    store.clear.mockReset();
    store.setState.mockReset();
    mockConfig.getLocalConfigPath.mockReset();
    mockConfig.getLocalConfigPath.mockReturnValue("/tmp/test/local.yaml");
    mockConfig.reloadAllConfigs.mockReset();
    mockYaml.mutateYaml.mockReset();
  });

  it("returns paginated logs", async () => {
    store.list.mockReturnValue({
      total: 2,
      offset: 0,
      limit: 1,
      records: [
        {
          id: "1",
          requestId: "r1",
          direction: "ingress",
          ts: "2026-04-15T00:00:01.000Z",
          method: "POST",
          path: "/v1/messages",
          status: 200,
          latencyMs: 10,
        },
      ],
    });

    const app = new Hono();
    app.route("/", createLogRoutes());

    const res = await app.request("/admin/logs?limit=1&offset=0&direction=egress&search=messages");
    expect(res.status).toBe(200);

    expect(store.list).toHaveBeenCalledWith({ direction: "egress", search: "messages", limit: 1, offset: 0 });
    const body = await res.json();
    expect(body.total).toBe(2);
    expect(body.records).toHaveLength(1);
    expect(body.records[0].id).toBe("1");
  });

  it("rejects invalid pagination params", async () => {
    const app = new Hono();
    app.route("/", createLogRoutes());

    const badLimit = await app.request("/admin/logs?limit=abc");
    expect(badLimit.status).toBe(400);
    expect(store.list).not.toHaveBeenCalled();

    const badOffset = await app.request("/admin/logs?offset=-1");
    expect(badOffset.status).toBe(400);
    expect(store.list).not.toHaveBeenCalled();
  });

  it("falls back to all when direction is unknown", async () => {
    store.list.mockReturnValue({ total: 0, offset: 0, limit: 50, records: [] });

    const app = new Hono();
    app.route("/", createLogRoutes());

    const res = await app.request("/admin/logs?direction=weird");
    expect(res.status).toBe(200);
    expect(store.list).toHaveBeenCalledWith({ direction: "all", search: undefined, limit: undefined, offset: undefined });
  });

  it("returns a selected log entry", async () => {
    store.get.mockReturnValue({
      id: "abc",
      requestId: "r1",
      direction: "ingress",
      ts: "2026-04-15T00:00:01.000Z",
      method: "GET",
      path: "/health",
      status: 200,
    });

    const app = new Hono();
    app.route("/", createLogRoutes());

    const res = await app.request("/admin/logs/abc");
    expect(res.status).toBe(200);
    expect(await res.json()).toMatchObject({ id: "abc", path: "/health" });
  });

  it("persists enabled state changes while keeping paused in memory", async () => {
    store.setState.mockReturnValue({ enabled: false, paused: true, dropped: 0, size: 0, capacity: 2000 });

    const app = new Hono();
    app.route("/", createLogRoutes());

    const res = await app.request("/admin/logs/state", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ enabled: false, paused: true }),
    });

    expect(res.status).toBe(200);
    expect(mockYaml.mutateYaml).toHaveBeenCalledOnce();
    expect(mockConfig.reloadAllConfigs).toHaveBeenCalledOnce();
    expect(store.setState).toHaveBeenCalledWith({ enabled: false, paused: true });
  });

  it("resets paused when enabling logs", async () => {
    store.setState.mockReturnValue({ enabled: true, paused: false, dropped: 0, size: 0, capacity: 2000 });

    const app = new Hono();
    app.route("/", createLogRoutes());

    const res = await app.request("/admin/logs/state", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ enabled: true, paused: true }),
    });

    expect(res.status).toBe(200);
    expect(store.setState).toHaveBeenCalledWith({ enabled: true, paused: true });
  });
});
