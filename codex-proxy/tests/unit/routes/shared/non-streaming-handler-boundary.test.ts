import { describe, expect, it } from "vitest";
import { handleNonStreaming } from "@src/routes/shared/non-streaming-handler.js";
import {
  retryNonStreamingEmptyResponse,
  handleNonStreamingPrematureClose,
  logNonStreamingUsage,
  recordNonStreamingSuccessAffinity,
  planNonStreamingCollectErrorResponse,
  handleNonStreamingEmptyResponseExhausted,
  handleNonStreamingCollectFailure,
  rethrowNonStreamingCodexApiErrorDuringCollect,
  releaseNonStreamingSuccessAccount,
  collectNonStreamingResponse,
} from "@src/routes/shared/non-streaming-helpers.js";
import { createResponseMetadataCollector } from "@src/routes/shared/response-metadata-collector.js";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import * as ts from "typescript";

const ROOT = process.cwd();
const NON_STREAMING_HANDLER_MODULE = "src/routes/shared/non-streaming-handler.ts";
const HELPERS_MODULE = "src/routes/shared/non-streaming-helpers.ts";
const EMPTY_RESPONSE_RETRY_MODULE = HELPERS_MODULE;
const PREMATURE_CLOSE_MODULE = HELPERS_MODULE;
const USAGE_LOG_MODULE = HELPERS_MODULE;
const AFFINITY_MODULE = HELPERS_MODULE;
const COLLECT_ERROR_RESPONSE_MODULE = HELPERS_MODULE;
const EMPTY_RESPONSE_EXHAUSTED_MODULE = HELPERS_MODULE;
const COLLECT_FAILURE_MODULE = HELPERS_MODULE;
const CODEX_API_ERROR_MODULE = HELPERS_MODULE;
const SUCCESS_RELEASE_MODULE = HELPERS_MODULE;
const RESPONSE_METADATA_COLLECTOR_MODULE = "src/routes/shared/response-metadata-collector.ts";
const COLLECT_RESPONSE_MODULE = HELPERS_MODULE;

function source(path: string): string {
  return readFileSync(resolve(ROOT, path), "utf-8");
}

function importedModuleSpecifiers(content: string, path = "inline.ts"): string[] {
  const file = ts.createSourceFile(path, content, ts.ScriptTarget.Latest, true, ts.ScriptKind.TS);
  const specs: string[] = [];

  for (const statement of file.statements) {
    if (!ts.isImportDeclaration(statement)) continue;
    const moduleSpecifier = statement.moduleSpecifier;
    if (ts.isStringLiteral(moduleSpecifier)) specs.push(moduleSpecifier.text);
  }

  return specs;
}

function importsNamedBinding(content: string, moduleSuffix: string, binding: string, path = "inline.ts"): boolean {
  const file = ts.createSourceFile(path, content, ts.ScriptTarget.Latest, true, ts.ScriptKind.TS);

  for (const statement of file.statements) {
    if (!ts.isImportDeclaration(statement)) continue;
    const moduleSpecifier = statement.moduleSpecifier;
    if (!ts.isStringLiteral(moduleSpecifier) || !moduleSpecifier.text.endsWith(moduleSuffix)) continue;
    const namedBindings = statement.importClause?.namedBindings;
    if (!namedBindings || !ts.isNamedImports(namedBindings)) continue;
    if (namedBindings.elements.some((element) => (element.propertyName?.text ?? element.name.text) === binding)) {
      return true;
    }
  }

  return false;
}

describe("non-streaming handler module boundary", () => {
  it("exports the non-streaming collect handler from its own module", () => {
    expect(handleNonStreaming).toBeTypeOf("function");
  });

  it("exports the empty-response retry helper from its own module", () => {
    expect(retryNonStreamingEmptyResponse).toBeTypeOf("function");
  });

  it("exports the premature-close helper from its own module", () => {
    expect(handleNonStreamingPrematureClose).toBeTypeOf("function");
  });

  it("exports the usage log helper from its own module", () => {
    expect(logNonStreamingUsage).toBeTypeOf("function");
  });

  it("exports the non-streaming affinity helper from its own module", () => {
    expect(recordNonStreamingSuccessAffinity).toBeTypeOf("function");
  });

  it("exports the collect error response planner from its own module", () => {
    expect(planNonStreamingCollectErrorResponse).toBeTypeOf("function");
  });

  it("exports the exhausted empty-response helper from its own module", () => {
    expect(handleNonStreamingEmptyResponseExhausted).toBeTypeOf("function");
  });

  it("exports the collect failure helper from its own module", () => {
    expect(handleNonStreamingCollectFailure).toBeTypeOf("function");
  });

  it("exports the CodexApiError collect rethrow helper from its own module", () => {
    expect(rethrowNonStreamingCodexApiErrorDuringCollect).toBeTypeOf("function");
  });

  it("exports the success release helper from its own module", () => {
    expect(releaseNonStreamingSuccessAccount).toBeTypeOf("function");
  });

  it("exports the response metadata collector helper from its own module", () => {
    expect(createResponseMetadataCollector).toBeTypeOf("function");
  });

  it("exports the non-streaming collect response helper from its own module", () => {
    expect(collectNonStreamingResponse).toBeTypeOf("function");
  });

  it("keeps empty-response retry reacquire and upstream send details out of the collect handler", () => {
    const handler = source(NON_STREAMING_HANDLER_MODULE);

    expect(importsNamedBinding(
      handler,
      "non-streaming-helpers.js",
      "retryNonStreamingEmptyResponse",
      NON_STREAMING_HANDLER_MODULE,
    )).toBe(true);
    expect(importsNamedBinding(handler, "account-acquisition.js", "acquireAccount", NON_STREAMING_HANDLER_MODULE)).toBe(false);
    expect(importsNamedBinding(handler, "proxy-handler-utils.js", "buildCodexApi", NON_STREAMING_HANDLER_MODULE)).toBe(false);
    expect(importsNamedBinding(handler, "proxy-egress-log.js", "recordProxyEgressLog", NON_STREAMING_HANDLER_MODULE)).toBe(false);
    expect(importsNamedBinding(handler, "../../utils/retry.js", "withRetry", NON_STREAMING_HANDLER_MODULE)).toBe(false);
  });


  it("keeps premature-close stream event and release details out of the collect handler", () => {
    const handler = source(NON_STREAMING_HANDLER_MODULE);
    const helper = source(PREMATURE_CLOSE_MODULE);

    expect(importsNamedBinding(
      handler,
      "non-streaming-helpers.js",
      "handleNonStreamingPrematureClose",
      NON_STREAMING_HANDLER_MODULE,
    )).toBe(true);
    expect(importsNamedBinding(
      handler,
      "stream-close-event.js",
      "recordStreamCloseEvent",
      NON_STREAMING_HANDLER_MODULE,
    )).toBe(false);
    expect(importsNamedBinding(
      helper,
      "stream-close-event.js",
      "recordStreamCloseEvent",
      PREMATURE_CLOSE_MODULE,
    )).toBe(true);
    expect(handler).not.toContain("upstream premature close (hadReasoning=");
  });


  it("keeps non-streaming usage log formatting details out of the collect handler", () => {
    const handler = source(NON_STREAMING_HANDLER_MODULE);

    expect(importsNamedBinding(
      handler,
      "non-streaming-helpers.js",
      "logNonStreamingUsage",
      NON_STREAMING_HANDLER_MODULE,
    )).toBe(true);
    expect(handler).not.toContain("High input token count");
    expect(handler).not.toContain("cached=");
    expect(handler).not.toContain("uncached=");
  });


  it("keeps non-streaming affinity record details out of the collect handler", () => {
    const handler = source(NON_STREAMING_HANDLER_MODULE);

    expect(importsNamedBinding(
      handler,
      "non-streaming-helpers.js",
      "recordNonStreamingSuccessAffinity",
      NON_STREAMING_HANDLER_MODULE,
    )).toBe(true);
    expect(handler).not.toContain("affinityMap.record(");
  });


  it("keeps generic collect error status parsing out of the collect handler", () => {
    const handler = source(NON_STREAMING_HANDLER_MODULE);

    expect(importsNamedBinding(
      handler,
      "non-streaming-helpers.js",
      "handleNonStreamingCollectFailure",
      NON_STREAMING_HANDLER_MODULE,
    )).toBe(true);
    expect(importsNamedBinding(
      handler,
      "non-streaming-helpers.js",
      "planNonStreamingCollectErrorResponse",
      NON_STREAMING_HANDLER_MODULE,
    )).toBe(false);
    expect(importsNamedBinding(handler, "proxy-error-handler.js", "toErrorStatus", NON_STREAMING_HANDLER_MODULE)).toBe(false);
    expect(handler).not.toContain("HTTP/[\\\\d.]");
    expect(handler).not.toContain("Unknown error");
  });


  it("keeps exhausted empty-response logging and recording details out of the collect handler", () => {
    const handler = source(NON_STREAMING_HANDLER_MODULE);

    expect(importsNamedBinding(
      handler,
      "non-streaming-helpers.js",
      "handleNonStreamingEmptyResponseExhausted",
      NON_STREAMING_HANDLER_MODULE,
    )).toBe(true);
    expect(handler).not.toContain("all retries exhausted");
    expect(handler).not.toContain("recordEmptyResponse");
    expect(handler).not.toContain("Codex returned empty responses across all available accounts");
  });


  it("keeps generic collect failure release details out of the collect handler", () => {
    const handler = source(NON_STREAMING_HANDLER_MODULE);

    expect(handler).not.toContain("annotateImageGenOutcome(undefined, req.expectsImageGen)");
  });


  it("keeps CodexApiError collect log formatting out of the collect handler", () => {
    const handler = source(NON_STREAMING_HANDLER_MODULE);

    expect(importsNamedBinding(
      handler,
      "non-streaming-helpers.js",
      "rethrowNonStreamingCodexApiErrorDuringCollect",
      NON_STREAMING_HANDLER_MODULE,
    )).toBe(true);
    expect(importsNamedBinding(
      handler,
      "proxy-handler-utils.js",
      "stripCodexErrorPrefix",
      NON_STREAMING_HANDLER_MODULE,
    )).toBe(false);
    expect(handler).not.toContain("during collect:");
  });


  it("keeps success release details out of the collect handler", () => {
    const handler = source(NON_STREAMING_HANDLER_MODULE);

    expect(importsNamedBinding(
      handler,
      "non-streaming-helpers.js",
      "releaseNonStreamingSuccessAccount",
      NON_STREAMING_HANDLER_MODULE,
    )).toBe(true);
    expect(importsNamedBinding(handler, "account-acquisition.js", "releaseAccount", NON_STREAMING_HANDLER_MODULE)).toBe(false);
    expect(importsNamedBinding(
      handler,
      "proxy-handler-utils.js",
      "annotateImageGenOutcome",
      NON_STREAMING_HANDLER_MODULE,
    )).toBe(false);
    expect(handler).not.toContain("releaseAccount(accountPool");
  });


  it("keeps response metadata collection details out of the non-streaming collect handler", () => {
    const handler = source(NON_STREAMING_HANDLER_MODULE);

    expect(importsNamedBinding(
      handler,
      "response-metadata-collector.js",
      "createResponseMetadataCollector",
      NON_STREAMING_HANDLER_MODULE,
    )).toBe(false);
    expect(handler).not.toContain("new Set<string>()");
    expect(handler).not.toContain("metadata.functionCallIds");
  });


  it("keeps collectTranslator and metadata collector plumbing out of the non-streaming handler", () => {
    const handler = source(NON_STREAMING_HANDLER_MODULE);

    expect(importsNamedBinding(
      handler,
      "non-streaming-helpers.js",
      "collectNonStreamingResponse",
      NON_STREAMING_HANDLER_MODULE,
    )).toBe(true);
    expect(importsNamedBinding(
      handler,
      "response-metadata-collector.js",
      "createResponseMetadataCollector",
      NON_STREAMING_HANDLER_MODULE,
    )).toBe(false);
    expect(handler).not.toContain("fmt.collectTranslator");
    expect(handler).not.toContain("metadataCollector");
  });

  it("does not let the consolidated helpers module import back into the handler or upper-layer modules", () => {
    const helpers = source(HELPERS_MODULE);
    const importedSpecs = importedModuleSpecifiers(helpers, HELPERS_MODULE);

    // Must not circularly import the handler
    expect(importedSpecs).not.toContain("./non-streaming-handler.js");

    // Must not import streaming handler
    expect(importedSpecs).not.toContain("./streaming-handler.js");

    // Must not import Hono runtime (type-only imports are erased and won't appear)
    for (const spec of importedSpecs) {
      if (spec === "hono" || spec.startsWith("hono/")) {
        // Verify it's type-only — value imports of hono are forbidden
        expect(importsNamedBinding(helpers, spec, "Hono", HELPERS_MODULE)).toBe(false);
      }
    }

    // Must not directly format error responses (that's the handler's job)
    expect(helpers).not.toContain("c.json(");
    expect(helpers).not.toContain("c.status(");

    // Must not own the entry-level request logger
    expect(importedSpecs).not.toContain("../../logs/entry.js");
  });

});
