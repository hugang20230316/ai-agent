import assert from "node:assert/strict";
import test from "node:test";

import {
  getEnvProxyRelaunch,
  sanitizeError
} from "./oss_workguid.mjs";

test("builds an env-proxy relaunch when proxy variables are configured", () => {
  const relaunch = getEnvProxyRelaunch({
    argv: ["/usr/local/bin/node", "/tmp/oss_workguid.mjs", "list", "work-guid"],
    env: { HTTPS_PROXY: "http://127.0.0.1:7897" },
    execArgv: [],
    allowedNodeEnvironmentFlags: new Set(["--use-env-proxy"])
  });

  assert.deepEqual(relaunch.args, ["--use-env-proxy", "/tmp/oss_workguid.mjs", "list", "work-guid"]);
  assert.equal(relaunch.env.OSS_WORKGUID_ENV_PROXY_REEXEC, "1");
});

test("does not relaunch when env-proxy is already enabled", () => {
  const relaunch = getEnvProxyRelaunch({
    argv: ["/usr/local/bin/node", "/tmp/oss_workguid.mjs", "list", "work-guid"],
    env: {
      HTTPS_PROXY: "http://127.0.0.1:7897",
      NODE_OPTIONS: "--use-env-proxy"
    },
    execArgv: [],
    allowedNodeEnvironmentFlags: new Set(["--use-env-proxy"])
  });

  assert.equal(relaunch, null);
});

test("sanitizes credentials while keeping fetch cause details", () => {
  const error = new Error("fetch failed AccessKeyId=plain");
  error.cause = Object.assign(new Error("getaddrinfo ENOTFOUND example.com"), {
    code: "ENOTFOUND",
    syscall: "getaddrinfo",
    hostname: "example.com"
  });

  const sanitized = sanitizeError(error);

  assert.match(sanitized, /fetch failed AccessKeyId=\[REDACTED\]/);
  assert.match(sanitized, /cause:/);
  assert.match(sanitized, /code=ENOTFOUND/);
  assert.match(sanitized, /hostname=example\.com/);
  assert.doesNotMatch(sanitized, /plain/);
});
