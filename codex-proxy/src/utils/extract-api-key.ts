import type { Context } from "hono";

/**
 * Extracts the proxy API key from the request Context.
 * Supports:
 * - Query param `?key=` (Gemini)
 * - Header `x-goog-api-key` (Gemini)
 * - Header `x-api-key` (Anthropic)
 * - Header `Authorization: Bearer <key>` (OpenAI and general)
 */
export function extractProxyApiKey(c: Context): string | null {
  const queryKey = c.req.query("key");
  const googKey = c.req.header("x-goog-api-key");
  const xApiKey = c.req.header("x-api-key");
  const authHeader = c.req.header("Authorization");
  const bearerKey = authHeader?.replace(/^bearer\s+/i, "");
  return queryKey ?? googKey ?? xApiKey ?? bearerKey ?? null;
}
