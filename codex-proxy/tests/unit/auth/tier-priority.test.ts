/**
 * Tests for tier_priority — account selection prefers higher-tier plan types.
 */

import { describe, it, expect, vi, beforeEach } from "vitest";

vi.mock("fs", () => ({
  readFileSync: vi.fn(() => { throw new Error("ENOENT"); }),
  writeFileSync: vi.fn(),
  renameSync: vi.fn(),
  existsSync: vi.fn(() => false),
  mkdirSync: vi.fn(),
}));

vi.mock("@src/paths.js", () => ({
  getDataDir: vi.fn(() => "/tmp/test-data"),
  getConfigDir: vi.fn(() => "/tmp/test-config"),
}));

vi.mock("@src/config.js", () => ({
  getConfig: vi.fn(() => ({
    auth: {
      jwt_token: null,
      rotation_strategy: "least_used",
      rate_limit_backoff_seconds: 60,
      max_concurrent_per_account: 3,
      tier_priority: null,
    },
  })),
}));

vi.mock("@src/auth/jwt-utils.js", () => ({
  decodeJwtPayload: vi.fn(() => ({ exp: Math.floor(Date.now() / 1000) + 3600 })),
  extractChatGptAccountId: vi.fn((token: string) => `acct-${token.slice(0, 8)}`),
  extractUserProfile: vi.fn((token: string) => {
    let plan = "free";
    if (token.includes("plus")) plan = "plus";
    else if (token.includes("team")) plan = "team";
    else if (token.includes("pro")) plan = "pro";
    return { email: `${token}@test.com`, chatgpt_plan_type: plan };
  }),
  isTokenExpired: vi.fn(() => false),
}));

vi.mock("@src/utils/jitter.js", () => ({
  jitter: vi.fn((val: number) => val),
}));

vi.mock("@src/models/model-store.js", () => ({
  getModelPlanTypes: vi.fn(() => []),
  isPlanFetched: vi.fn(() => true),
}));

import { AccountPool } from "@src/auth/account-pool.js";
import { getConfig } from "@src/config.js";
import { extractUserProfile } from "@src/auth/jwt-utils.js";

describe("tier_priority", () => {
  let pool: AccountPool;

  function setupPool(tierPriority: string[] | null): void {
    vi.mocked(getConfig).mockReturnValue({
      auth: {
        jwt_token: null,
        rotation_strategy: "least_used",
        rate_limit_backoff_seconds: 60,
        max_concurrent_per_account: 3,
        tier_priority: tierPriority,
      },
    } as ReturnType<typeof getConfig>);
    pool = new AccountPool({ rotationStrategy: "least_used" });
  }

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("without tier_priority, uses default least_used ordering", () => {
    setupPool(null);
    // Add free first, then plus — with least_used, both have 0 requests
    pool.addAccount("free-token-1");
    pool.addAccount("plus-token-1");

    // With no tier priority, the order is determined by least_used (both equal → round robin)
    const first = pool.acquire();
    expect(first).not.toBeNull();
    // Just verify acquire works — order is not tier-based
  });

  it("plus is preferred over free when tier_priority is set", () => {
    setupPool(["plus", "team", "free"]);
    pool.addAccount("free-token-1");
    pool.addAccount("plus-token-1");

    const acquired = pool.acquire();
    expect(acquired).not.toBeNull();
    // Verify it picked the plus account
    const entry = pool.getEntry(acquired!.entryId);
    expect(entry?.planType).toBe("plus");
  });

  it("team is preferred over free but not plus", () => {
    setupPool(["plus", "team", "free"]);
    pool.addAccount("free-token-1");
    pool.addAccount("team-token-1");

    const acquired = pool.acquire();
    expect(acquired).not.toBeNull();
    const entry = pool.getEntry(acquired!.entryId);
    expect(entry?.planType).toBe("team");
  });

  it("within same tier, only that tier is offered to the strategy", () => {
    setupPool(["plus", "free"]);
    pool.addAccount("plus-token-a");
    pool.addAccount("plus-token-b");
    pool.addAccount("free-token-1");

    // Tier filter should restrict candidates to plus accounts only,
    // so free account is never chosen while a plus is available
    for (let i = 0; i < 6; i++) {
      const acq = pool.acquire();
      expect(acq).not.toBeNull();
      const entry = pool.getEntry(acq!.entryId);
      expect(entry?.planType).toBe("plus");
      pool.release(acq!.entryId, { input_tokens: 10, output_tokens: 5 });
    }
  });

  it("accounts with null planType sort after all listed tiers", () => {
    setupPool(["plus", "free"]);
    // Create an account with null planType
    vi.mocked(extractUserProfile).mockReturnValueOnce({
      email: "null@test.com",
      chatgpt_plan_type: null,
    } as ReturnType<typeof extractUserProfile>);
    pool.addAccount("null-plan-token");
    pool.addAccount("free-token-1");

    const acquired = pool.acquire();
    expect(acquired).not.toBeNull();
    const entry = pool.getEntry(acquired!.entryId);
    // free is in the priority list, null is not — free should be preferred
    expect(entry?.planType).toBe("free");
  });

  it("accounts with planType not in list sort after listed tiers", () => {
    setupPool(["plus"]);
    pool.addAccount("free-token-1"); // "free" not in priority list
    pool.addAccount("plus-token-1");

    const acquired = pool.acquire();
    expect(acquired).not.toBeNull();
    const entry = pool.getEntry(acquired!.entryId);
    expect(entry?.planType).toBe("plus");
  });

  it("falls through to lower tier when higher tier accounts are busy", () => {
    vi.mocked(getConfig).mockReturnValue({
      auth: {
        jwt_token: null,
        rotation_strategy: "least_used",
        rate_limit_backoff_seconds: 60,
        max_concurrent_per_account: 1, // Only 1 concurrent per account
        tier_priority: ["plus", "free"],
      },
    } as ReturnType<typeof getConfig>);
    pool = new AccountPool({ rotationStrategy: "least_used" });
    pool.addAccount("plus-token-1");
    pool.addAccount("free-token-1");

    // First acquire takes the plus account
    const first = pool.acquire();
    expect(pool.getEntry(first!.entryId)?.planType).toBe("plus");

    // Second acquire — plus is at capacity, falls to free
    const second = pool.acquire();
    expect(second).not.toBeNull();
    expect(pool.getEntry(second!.entryId)?.planType).toBe("free");
  });

  it("works with round_robin strategy", () => {
    setupPool(["plus", "free"]);
    pool.setRotationStrategy("round_robin");
    pool.addAccount("free-token-1");
    pool.addAccount("plus-token-1");

    // With tier priority, plus should come first regardless of round_robin order
    const acquired = pool.acquire();
    expect(acquired).not.toBeNull();
    const entry = pool.getEntry(acquired!.entryId);
    expect(entry?.planType).toBe("plus");
  });

  it("works with sticky strategy", () => {
    setupPool(["plus", "free"]);
    pool.setRotationStrategy("sticky");
    pool.addAccount("free-token-1");
    pool.addAccount("plus-token-1");

    const acquired = pool.acquire();
    expect(acquired).not.toBeNull();
    const entry = pool.getEntry(acquired!.entryId);
    expect(entry?.planType).toBe("plus");
  });
});
