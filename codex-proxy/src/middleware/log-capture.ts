import type { Context, Next } from "hono";
import { getConfig } from "../config.js";
import { enqueueLogEntry } from "../logs/entry.js";

const KNOWN_LLM_PATHS = [
  /^\/v1\/chat\/completions$/,
  /^\/v1\/messages$/,
  /^\/v1\/responses(?:\/compact)?$/,
  /^\/v1\/models(?:\/.*)?$/,
  /^\/v1beta\/models(?:\/.*)?$/,
];

export function isKnownLlmPath(path: string): boolean {
  return KNOWN_LLM_PATHS.some((pattern) => pattern.test(path));
}

export function shouldCaptureRequest(c: Context): boolean {
  const config = getConfig();
  if (!config.logs.llm_only) return true;
  if (c.get("logForwarded") === true) return true;
  return isKnownLlmPath(c.req.path);
}

export async function logCapture(c: Context, next: Next): Promise<void> {
  const startMs = Date.now();
  await next();
  if (!shouldCaptureRequest(c)) return;

  enqueueLogEntry({
    requestId: c.get("requestId") ?? "-",
    direction: "ingress",
    method: c.req.method,
    path: c.req.path,
    status: c.res.status,
    latencyMs: Date.now() - startMs,
  });
}
