import type { Context, Next, MiddlewareHandler } from "hono";
import { getConfig } from "../config.js";
import { extractProxyApiKey } from "../utils/extract-api-key.js";
import type { AccountPool } from "../auth/account-pool.js";

function makeOpenAIError(message: string) {
  return {
    error: {
      message,
      type: "invalid_request_error",
      param: null,
      code: "invalid_api_key",
    },
  };
}

function makeAnthropicError(message: string) {
  return {
    type: "error",
    error: {
      type: "authentication_error",
      message,
    },
  };
}

function makeGeminiError(code: number, message: string) {
  return {
    error: {
      code,
      message,
      status: "UNAUTHENTICATED",
    },
  };
}

export function apiKeyAuth(accountPool: AccountPool): MiddlewareHandler {
  return async (c: Context, next: Next) => {
    const config = getConfig();
    if (!config.server.proxy_api_key) {
      return next();
    }

    const providedKey = extractProxyApiKey(c);
    if (!providedKey || !accountPool.validateProxyApiKey(providedKey)) {
      const path = c.req.path;
      c.status(401);

      if (path.startsWith("/admin/")) {
        return c.json({ error: "Invalid current API key" });
      }
      if (path.startsWith("/v1/messages")) {
        return c.json(makeAnthropicError("Invalid API key"));
      }
      if (path.startsWith("/v1beta/")) {
        return c.json(makeGeminiError(401, "Invalid API key"));
      }
      return c.json(makeOpenAIError("Invalid proxy API key"));
    }

    return next();
  };
}
