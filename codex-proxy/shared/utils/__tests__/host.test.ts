import { describe, expect, it } from "vitest";
import { isLoopbackHostname, isNetworkExposedHost, normalizeHostname } from "../host";

describe("host utilities", () => {
  it("normalizes hostnames for comparison", () => {
    expect(normalizeHostname(" Localhost. ")).toBe("localhost");
    expect(normalizeHostname("[::1]")).toBe("::1");
  });

  it("recognizes loopback hosts", () => {
    for (const host of ["localhost", "127.0.0.1", "127.10.20.30", "::1", "[::1]", "0:0:0:0:0:0:0:1"]) {
      expect(isLoopbackHostname(host)).toBe(true);
      expect(isNetworkExposedHost(host)).toBe(false);
    }
  });

  it("treats wildcard and non-loopback hosts as network-exposed", () => {
    for (const host of ["0.0.0.0", "::", "192.168.1.10", "10.0.0.2", "example.com"]) {
      expect(isLoopbackHostname(host)).toBe(false);
      expect(isNetworkExposedHost(host)).toBe(true);
    }
  });

  it("does not warn for an empty in-progress host draft", () => {
    expect(isNetworkExposedHost("   ")).toBe(false);
  });
});
