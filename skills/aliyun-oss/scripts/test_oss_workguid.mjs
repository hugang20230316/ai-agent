import assert from "node:assert/strict";
import crypto from "node:crypto";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import test from "node:test";

import {
  buildSignedGetUrl,
  getEnvProxyRelaunch,
  loadRuntimeConfig,
  parseOssUrl,
  resolveAccessibleObject,
  splitObjectPath,
  sanitizeError
} from "./oss_workguid.mjs";

test("splits a logical bucket and object key", () => {
  assert.deepEqual(
    splitObjectPath("media/reports/example image.png"),
    {
      logicalBucket: "media",
      key: "reports/example image.png"
    }
  );
});

test("builds a two-hour signed GET URL", () => {
  const now = new Date("2026-07-20T06:42:49Z");
  const client = {
    accessKeyId: "test-access-key",
    accessKeySecret: "test-secret",
    baseUrl: new URL("https://oss-cn-qingdao.aliyuncs.com"),
    bucket: "media-dev"
  };
  const key = "reports/example image.png";

  const signedUrl = new URL(buildSignedGetUrl(client, key, { now }));
  const expires = Math.floor(now.getTime() / 1000) + 2 * 60 * 60;
  const stringToSign = `GET\n\n\n${expires}\n/media-dev/${key}`;
  const expectedSignature = crypto
    .createHmac("sha1", client.accessKeySecret)
    .update(stringToSign, "utf8")
    .digest("base64");

  assert.equal(signedUrl.hostname, "media-dev.oss-cn-qingdao.aliyuncs.com");
  assert.equal(signedUrl.pathname, "/reports/example%20image.png");
  assert.equal(signedUrl.searchParams.get("OSSAccessKeyId"), client.accessKeyId);
  assert.equal(signedUrl.searchParams.get("Expires"), String(expires));
  assert.equal(signedUrl.searchParams.get("Signature"), expectedSignature);
});

test("uses the explicit logical bucket and allows public access without credentials", () => {
  const config = loadRuntimeConfig("media", {
    appConfig: {
      OssConfig: {
        BucketFormat: "{0}-dev",
        PublicEndpoint: "https://oss-cn-qingdao.aliyuncs.com",
        Region: "cn-qingdao"
      }
    },
    env: { OSS_BUCKET: "wrong-bucket" },
    envConfig: {},
    preferLogicalBucket: true,
    requireCredentials: false
  });

  assert.equal(config.bucket, "media-dev");
  assert.equal(config.accessKeyId, undefined);
  assert.equal(config.accessKeySecret, undefined);
});

test("recognizes the generated V1 URL as signed", () => {
  assert.equal(
    parseOssUrl(
      "https://bucket.oss-cn-qingdao.aliyuncs.com/path/image.png?OSSAccessKeyId=test&Expires=123&Signature=signed"
    ).hasSignedQuery,
    true
  );
});

test("returns an unsigned public URL when the object is publicly readable", async () => {
  const requests = [];
  const client = {
    accessKeyId: "test-access-key",
    accessKeySecret: "test-secret",
    baseUrl: new URL("https://oss-cn-qingdao.aliyuncs.com"),
    bucket: "media-dev"
  };

  const result = await resolveAccessibleObject(client, "reports/report.png", {
    fetchFn: async (url) => {
      requests.push(url);
      return { status: 206 };
    }
  });

  assert.equal(result.access, "public-url");
  assert.equal(result.verifiedStatus, 206);
  assert.equal(new URL(result.url).search, "");
  assert.equal(requests.length, 1);
});

test("returns a verified signed URL for a private object", async () => {
  const requests = [];
  const client = {
    accessKeyId: "test-access-key",
    accessKeySecret: "test-secret",
    baseUrl: new URL("https://oss-cn-qingdao.aliyuncs.com"),
    bucket: "media-dev"
  };

  const result = await resolveAccessibleObject(client, "reports/report.png", {
    fetchFn: async (url) => {
      requests.push(url);
      return { status: requests.length === 1 ? 403 : 206 };
    },
    now: new Date("2026-07-20T06:42:49Z")
  });

  assert.equal(result.access, "signed-url");
  assert.equal(result.verifiedStatus, 206);
  assert.equal(new URL(result.url).searchParams.has("Signature"), true);
  assert.equal(requests.length, 2);
});

test("reports missing credentials after public URL verification fails", async () => {
  const client = {
    baseUrl: new URL("https://oss-cn-qingdao.aliyuncs.com"),
    bucket: "media-dev"
  };

  await assert.rejects(
    resolveAccessibleObject(client, "reports/report.png", {
      fetchFn: async () => ({ status: 403 })
    }),
    /not publicly accessible and OSS credentials are not configured/
  );
});

test("distinguishes a public URL verification error from a private object", async () => {
  const client = {
    baseUrl: new URL("https://oss-cn-qingdao.aliyuncs.com"),
    bucket: "media-dev"
  };

  await assert.rejects(
    resolveAccessibleObject(client, "reports/report.png", {
      fetchFn: async () => {
        throw new Error("network unavailable");
      }
    }),
    /public URL could not be verified and OSS credentials are not configured/
  );
});

test("downloads to a user-accessible directory when URLs cannot be verified", async () => {
  const outDir = fs.mkdtempSync(path.join(os.tmpdir(), "oss-access-test-"));
  const client = {
    accessKeyId: "test-access-key",
    accessKeySecret: "test-secret",
    baseUrl: new URL("https://oss-cn-qingdao.aliyuncs.com"),
    bucket: "media-dev"
  };

  try {
    const result = await resolveAccessibleObject(client, "reports/report.png", {
      fetchFn: async () => ({ status: 403 }),
      getObjectFn: async () => ({
        body: Buffer.from("image-data"),
        headers: { "content-type": "image/png" }
      }),
      outDir
    });

    assert.equal(result.access, "local-file");
    assert.equal(result.localPath, path.join(outDir, "reports/report.png"));
    assert.equal(fs.readFileSync(result.localPath, "utf8"), "image-data");
  } finally {
    fs.rmSync(outDir, { recursive: true, force: true });
  }
});

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
