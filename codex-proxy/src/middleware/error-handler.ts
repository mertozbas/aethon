import type { Context } from "hono";
import type { ErrorHandler as HonoErrorHandler } from "hono";
import type { StatusCode } from "hono/utils/http-status";
import type { OpenAIErrorBody } from "../types/openai.js";
import type { AnthropicErrorBody, AnthropicErrorType } from "../types/anthropic.js";
import { GEMINI_STATUS_MAP } from "../types/gemini.js";

function makeOpenAIError(
  message: string,
  type: string,
  code: string | null,
): OpenAIErrorBody {
  return {
    error: {
      message,
      type,
      param: null,
      code,
    },
  };
}

function makeAnthropicError(
  message: string,
  errorType: AnthropicErrorType,
): AnthropicErrorBody {
  return { type: "error", error: { type: errorType, message } };
}

interface GeminiErrorBody {
  error: { code: number; message: string; status: string };
}

function makeGeminiError(
  code: number,
  message: string,
  status: string,
): GeminiErrorBody {
  return { error: { code, message, status } };
}

export const errorHandler: HonoErrorHandler = (err: Error, c: Context): Response => {
  const errRecord = err as unknown as Record<string, unknown>;
  const message = err.message || "Internal server error";
  console.error("[ErrorHandler]", err.stack ?? message);

  const status = typeof errRecord.status === "number" ? errRecord.status : undefined;
  const path = c.req.path;

  // Malformed JSON request body should be treated as a client error.
  const isSyntaxError = err instanceof SyntaxError || err.name === "SyntaxError" || String(err).includes("SyntaxError");
  if (isSyntaxError && message.toLowerCase().includes("json")) {
    c.status(400);
    if (path.startsWith("/v1/messages")) {
      return c.json(
        makeAnthropicError("Malformed JSON request body", "invalid_request_error"),
      );
    }
    if (path.startsWith("/v1beta/")) {
      return c.json(
        makeGeminiError(400, "Malformed JSON request body", "INVALID_ARGUMENT"),
      );
    }
    return c.json(
      makeOpenAIError(
        "Malformed JSON request body",
        "invalid_request_error",
        "invalid_json",
      ),
    );
  }

  // Anthropic Messages API errors
  if (path.startsWith("/v1/messages")) {
    if (status === 401) {
      c.status(401);
      return c.json(
        makeAnthropicError(
          "Invalid or expired token. Please re-authenticate.",
          "authentication_error",
        ),
      );
    }
    if (status === 429) {
      c.status(429);
      return c.json(
        makeAnthropicError(
          "Rate limit exceeded. Please try again later.",
          "rate_limit_error",
        ),
      );
    }
    if (status && status >= 500) {
      c.status(502);
      return c.json(
        makeAnthropicError(`Upstream server error: ${message}`, "api_error"),
      );
    }
    c.status(500);
    return c.json(makeAnthropicError(message, "api_error"));
  }

  // Gemini API errors
  if (path.startsWith("/v1beta/")) {
    const code = status ?? 500;
    const geminiStatus = GEMINI_STATUS_MAP[code] ?? "INTERNAL";
    c.status((code >= 400 && code < 600 ? code : 500) as StatusCode);
    return c.json(makeGeminiError(code, message, geminiStatus));
  }

  // Default: OpenAI-format errors
  if (status === 401) {
    c.status(401);
    return c.json(
      makeOpenAIError(
        "Invalid or expired ChatGPT token. Please re-authenticate.",
        "invalid_request_error",
        "invalid_api_key",
      ),
    );
  }

  if (status === 429) {
    c.status(429);
    return c.json(
      makeOpenAIError(
        "Rate limit exceeded. Please try again later.",
        "rate_limit_error",
        "rate_limit_exceeded",
      ),
    );
  }

  if (status && status >= 500) {
    c.status(502);
    return c.json(
      makeOpenAIError(
        `Upstream server error: ${message}`,
        "server_error",
        "server_error",
      ),
    );
  }

  c.status(500);
  return c.json(
    makeOpenAIError(message, "server_error", "internal_error"),
  );
};
