#!/usr/bin/env node

import { spawnSync } from "node:child_process";
import crypto from "node:crypto";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import process from "node:process";
import { pathToFileURL } from "node:url";

const TEACHER_AI_CONFIG = process.env.TEACHER_AI_OSS_CONFIG || findTeacherAiFile("appsettings.json");
const TEACHER_AI_ENV_CONFIG = process.env.TEACHER_AI_OSS_ENV_CONFIG || findTeacherAiFile("appsettings_k8sEnvConfigMap.txt");
const LOGICAL_BUCKET = process.env.OSS_LOGICAL_BUCKET || "7netomr";
const DEFAULT_WORK_ROOT = "edumaterials/work2images/work3";
const DEFAULT_MAX_READ_BYTES = 1024 * 1024;
const DEFAULT_SIGNED_URL_SECONDS = 2 * 60 * 60;
const MAX_SIGNED_URL_SECONDS = 24 * 60 * 60;
const TEXT_EXTENSIONS = new Set([
  ".json",
  ".md",
  ".txt",
  ".csv",
  ".log",
  ".xml",
  ".yml",
  ".yaml"
]);

if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) {
  main().catch((error) => {
    writeJson({
      ok: false,
      error: sanitizeError(error)
    });
    process.exitCode = 1;
  });
}

async function main() {
  const [command, ...args] = process.argv.slice(2);

  if (!command || command === "help" || command === "--help" || command === "-h") {
    printHelp();
    return;
  }

  if (command === "from-url") {
    const [rawUrl] = args;
    ensure(rawUrl, "from-url requires an OSS HTTP URL");
    writeJson({ ok: true, ...parseOssUrl(rawUrl) });
    return;
  }

  const relaunch = getEnvProxyRelaunch();
  if (relaunch) {
    const result = spawnSync(process.execPath, relaunch.args, {
      env: relaunch.env,
      stdio: "inherit"
    });
    if (result.error) {
      throw result.error;
    }
    if (result.signal) {
      throw new Error(`OSS command stopped by signal: ${result.signal}`);
    }
    process.exit(result.status ?? 0);
  }

  if (command === "url") {
    const { positionals, options } = parseArgs(args);
    const [objectPath] = positionals;
    const { logicalBucket, key } = splitObjectPath(objectPath);
    const config = loadRuntimeConfig(logicalBucket, {
      preferLogicalBucket: true,
      requireCredentials: false
    });
    const client = createClient(config);
    writeJson({
      ok: true,
      bucket: config.bucket,
      key,
      ...(await resolveAccessibleObject(client, key, {
        expiresSeconds: options.expires,
        outDir: options.out
      }))
    });
    return;
  }

  const config = loadRuntimeConfig();
  const client = createClient(config);

  if (command === "list") {
    const { positionals, options } = parseArgs(args);
    const [workGuid, subdir = ""] = positionals;
    ensureWorkGuid(workGuid);
    const prefix = buildObjectKey(config, workGuid, subdir, { directory: true });
    const result = await listObjects(client, prefix, options);
    writeJson({ ok: true, bucket: config.bucket, prefix, ...result });
    return;
  }

  if (command === "info") {
    const { positionals } = parseArgs(args);
    const [workGuid] = positionals;
    ensureWorkGuid(workGuid);
    const key = buildObjectKey(config, workGuid, "templete/info.json");
    const object = await getObject(client, key);
    const content = object.body.toString("utf8");
    const parsed = JSON.parse(content);
    writeJson({
      ok: true,
      bucket: config.bucket,
      key,
      contentLength: object.body.length,
      summary: summarizeInfoJson(parsed)
    });
    return;
  }

  if (command === "read") {
    const { positionals, options } = parseArgs(args);
    const [workGuid, relativePath] = positionals;
    ensureWorkGuid(workGuid);
    ensure(relativePath, "read requires a relative object path");
    const key = buildObjectKey(config, workGuid, relativePath);
    const head = await headObject(client, key);
    const size = Number(head.headers["content-length"] || 0);
    const force = Boolean(options.force);
    ensure(force || size <= DEFAULT_MAX_READ_BYTES, `object is too large to read inline: ${size} bytes`);
    ensure(force || isTextPath(key), `refusing to inline non-text object: ${key}`);
    const object = await getObject(client, key);
    writeJson({
      ok: true,
      bucket: config.bucket,
      key,
      contentLength: object.body.length,
      contentType: object.headers["content-type"] || null,
      content: object.body.toString("utf8")
    });
    return;
  }

  if (command === "download") {
    const { positionals, options } = parseArgs(args);
    const [workGuid, relativePath] = positionals;
    ensureWorkGuid(workGuid);
    ensure(relativePath, "download requires a relative object path");
    const key = buildObjectKey(config, workGuid, relativePath);
    const object = await getObject(client, key);
    const outDir = options.out || path.join(os.tmpdir(), "oss-workguid", workGuid);
    const localPath = safeDownloadPath(outDir, relativePath);
    fs.mkdirSync(path.dirname(localPath), { recursive: true });
    fs.writeFileSync(localPath, object.body);
    writeJson({
      ok: true,
      bucket: config.bucket,
      key,
      contentLength: object.body.length,
      contentType: object.headers["content-type"] || null,
      localPath
    });
    return;
  }

  throw new Error(`unknown command: ${command}`);
}

function printHelp() {
  console.log(`Usage:
  oss_workguid.mjs from-url <oss-http-url>
  oss_workguid.mjs url <logical-bucket/object-key> [--expires SECONDS] [--out DIR]
  oss_workguid.mjs list <workGuid> [subdir] [--limit N]
  oss_workguid.mjs info <workGuid>
  oss_workguid.mjs read <workGuid> <relativePath> [--force]
  oss_workguid.mjs download <workGuid> <relativePath> [--out DIR]`);
}

function parseArgs(args) {
  const positionals = [];
  const options = {};

  for (let i = 0; i < args.length; i += 1) {
    const arg = args[i];
    if (arg === "--force") {
      options.force = true;
    } else if (arg === "--out" || arg === "--limit" || arg === "--expires") {
      const value = args[i + 1];
      ensure(value, `${arg} requires a value`);
      options[arg.slice(2)] = arg === "--out" ? value : Number(value);
      i += 1;
    } else {
      positionals.push(arg);
    }
  }

  return { positionals, options };
}

export function loadRuntimeConfig(logicalBucket = LOGICAL_BUCKET, options = {}) {
  const runtimeEnv = options.env || process.env;
  const appConfig = options.appConfig ?? readJsoncFile(TEACHER_AI_CONFIG);
  const envConfig = options.envConfig ?? readEnvFile(TEACHER_AI_ENV_CONFIG);
  const ossConfig = appConfig.OssConfig || {};
  const scanOss = appConfig.ScanOss || {};

  const region = firstValue(
    runtimeEnv.OSS_REGION,
    ossConfig.Region,
    envConfig.APPCUSTOM_OssConfig__Region,
    "cn-qingdao"
  );
  const endpoint = trimSlash(firstValue(
    runtimeEnv.OSS_ENDPOINT,
    ossConfig.PublicEndpoint,
    ossConfig.Endpoint,
    envConfig.APPCUSTOM_OssConfig__PublicEndpoint,
    envConfig.APPCUSTOM_OssConfig__Endpoint,
    `https://oss-${region}.aliyuncs.com`
  ));
  const bucketFormat = firstValue(
    runtimeEnv.OSS_BUCKET_FORMAT,
    ossConfig.BucketFormat,
    envConfig.APPCUSTOM_OssConfig__BucketFormat,
    "{0}-dev"
  );
  const bucket = firstValue(
    options.preferLogicalBucket ? null : runtimeEnv.OSS_BUCKET,
    bucketFormat.replace("{0}", logicalBucket)
  );
  const accessKeyId = firstValue(
    runtimeEnv.OSS_ACCESS_KEY_ID,
    ossConfig.AccessKeyId,
    envConfig.APPCUSTOM_OssConfig__AccessKeyId
  );
  const accessKeySecret = firstValue(
    runtimeEnv.OSS_ACCESS_KEY_SECRET,
    ossConfig.AccessKeySecret,
    envConfig.APPCUSTOM_OssConfig__AccessKeySecret
  );
  const workRoot = [
    firstValue(runtimeEnv.OSS_EDUMATERIALS_PATH, scanOss.OssPath, "edumaterials"),
    "work2images",
    "work3"
  ].join("/");

  // Public URL checks do not require OSS credentials.
  if (options.requireCredentials !== false) {
    ensure(accessKeyId, "OSS access key id is not configured");
    ensure(accessKeySecret, "OSS access key secret is not configured");
  }

  return { region, endpoint, bucket, accessKeyId, accessKeySecret, workRoot };
}

function readJsoncFile(filePath) {
  if (!filePath || !fs.existsSync(filePath)) {
    return {};
  }

  const raw = fs.readFileSync(filePath, "utf8").replace(/^\uFEFF/, "");
  const stripped = stripJsonComments(raw).replace(/,\s*([}\]])/g, "$1");
  return JSON.parse(stripped);
}

function stripJsonComments(value) {
  let result = "";
  let inString = false;
  let escaped = false;

  for (let i = 0; i < value.length; i += 1) {
    const char = value[i];
    const next = value[i + 1];

    if (inString) {
      result += char;
      if (escaped) {
        escaped = false;
      } else if (char === "\\") {
        escaped = true;
      } else if (char === "\"") {
        inString = false;
      }
      continue;
    }

    if (char === "\"") {
      inString = true;
      result += char;
      continue;
    }

    if (char === "/" && next === "/") {
      while (i < value.length && value[i] !== "\n") {
        i += 1;
      }
      result += "\n";
      continue;
    }

    if (char === "/" && next === "*") {
      i += 2;
      while (i < value.length && !(value[i] === "*" && value[i + 1] === "/")) {
        i += 1;
      }
      i += 1;
      continue;
    }

    result += char;
  }

  return result;
}

function readEnvFile(filePath) {
  if (!filePath || !fs.existsSync(filePath)) {
    return {};
  }

  const result = {};
  for (const line of fs.readFileSync(filePath, "utf8").split(/\r?\n/)) {
    const match = line.match(/^\s*([A-Za-z0-9_]+)\s*[:=]\s*(.*?)\s*$/);
    if (match) {
      result[match[1]] = stripQuotes(match[2]);
    }
  }
  return result;
}

function createClient(config) {
  const baseUrl = new URL(config.endpoint);
  return { ...config, baseUrl };
}

export function getEnvProxyRelaunch({
  argv = process.argv,
  env = process.env,
  execArgv = process.execArgv,
  allowedNodeEnvironmentFlags = process.allowedNodeEnvironmentFlags
} = {}) {
  const hasProxy = [
    "HTTP_PROXY",
    "HTTPS_PROXY",
    "ALL_PROXY",
    "http_proxy",
    "https_proxy",
    "all_proxy"
  ].some((name) => Boolean(env[name]));
  if (!hasProxy) {
    return null;
  }
  if (!allowedNodeEnvironmentFlags.has("--use-env-proxy")) {
    return null;
  }
  if (env.OSS_WORKGUID_ENV_PROXY_REEXEC === "1") {
    return null;
  }
  if (execArgv.includes("--use-env-proxy") || String(env.NODE_OPTIONS || "").split(/\s+/).includes("--use-env-proxy")) {
    return null;
  }

  return {
    args: ["--use-env-proxy", ...argv.slice(1)],
    env: {
      ...env,
      OSS_WORKGUID_ENV_PROXY_REEXEC: "1"
    }
  };
}

function findTeacherAiFile(fileName) {
  for (const candidate of teacherAiCandidates(fileName)) {
    if (isTeacherAiApiFile(candidate, fileName)) {
      return candidate;
    }
  }

  const worksRoot = path.join(os.homedir(), "Works");
  const found = findTeacherAiApiFile(worksRoot, fileName, 5);
  return found || null;
}

function teacherAiCandidates(fileName) {
  const candidates = [];
  const explicitRoot = process.env.TEACHER_AI_ROOT;
  if (explicitRoot) {
    candidates.push(path.join(explicitRoot, "src", "TeacherAI.API", fileName));
  }

  for (const root of cwdAncestors()) {
    candidates.push(path.join(root, "src", "TeacherAI.API", fileName));
    candidates.push(path.join(root, "teacher-ai", "src", "TeacherAI.API", fileName));
  }

  const worksRoot = path.join(os.homedir(), "Works");
  candidates.push(path.join(worksRoot, "teacher-ai", "src", "TeacherAI.API", fileName));
  if (fs.existsSync(worksRoot)) {
    for (const entry of fs.readdirSync(worksRoot, { withFileTypes: true })) {
      if (entry.isDirectory() && !entry.name.startsWith(".")) {
        candidates.push(path.join(worksRoot, entry.name, "teacher-ai", "src", "TeacherAI.API", fileName));
      }
    }
  }

  return candidates;
}

function cwdAncestors() {
  const ancestors = [];
  let current = process.cwd();
  const home = os.homedir();

  while (current && current.startsWith(home)) {
    ancestors.push(current);
    const next = path.dirname(current);
    if (next === current || next === home) {
      break;
    }
    current = next;
  }

  return ancestors;
}

function findTeacherAiApiFile(root, fileName, maxDepth) {
  if (!root || maxDepth < 0 || !fs.existsSync(root)) {
    return null;
  }

  let entries;
  try {
    entries = fs.readdirSync(root, { withFileTypes: true });
  } catch {
    return null;
  }

  for (const entry of entries) {
    if (entry.name === "node_modules" || entry.name === ".git" || entry.name.startsWith(".")) {
      continue;
    }

    const entryPath = path.join(root, entry.name);
    if (entry.isFile() && isTeacherAiApiFile(entryPath, fileName)) {
      return entryPath;
    }
    if (entry.isDirectory()) {
      const found = findTeacherAiApiFile(entryPath, fileName, maxDepth - 1);
      if (found) {
        return found;
      }
    }
  }

  return null;
}

function isTeacherAiApiFile(filePath, fileName) {
  if (!fs.existsSync(filePath)) {
    return false;
  }

  const normalized = filePath.split(path.sep).join("/");
  return normalized.endsWith(`/teacher-ai/src/TeacherAI.API/${fileName}`) ||
    normalized.endsWith(`/src/TeacherAI.API/${fileName}`);
}

async function listObjects(client, prefix, options) {
  const limit = Number.isFinite(options.limit) && options.limit > 0 ? options.limit : 1000;
  const params = new URLSearchParams({
    "list-type": "2",
    prefix,
    "max-keys": String(Math.min(limit, 1000))
  });
  const response = await requestOss(client, "GET", "/", params);
  const body = response.body.toString("utf8");
  const objects = parseListObjects(body).slice(0, limit);

  return {
    count: objects.length,
    objects: objects.map((item) => ({
      key: item.key,
      relativePath: item.key.startsWith(prefix) ? item.key.slice(prefix.length) : item.key,
      size: item.size,
      lastModified: item.lastModified
    }))
  };
}

async function headObject(client, key) {
  return requestOss(client, "HEAD", `/${encodeObjectPath(key)}`);
}

async function getObject(client, key) {
  return requestOss(client, "GET", `/${encodeObjectPath(key)}`);
}

export function splitObjectPath(value) {
  const clean = String(value || "").replace(/^oss:\/\//, "").replace(/^\/+/, "");
  const separator = clean.indexOf("/");
  ensure(separator > 0 && separator < clean.length - 1, "object path must use logical-bucket/object-key format");
  const logicalBucket = clean.slice(0, separator);
  const key = clean.slice(separator + 1);
  ensure(/^[a-z0-9][a-z0-9-]{1,62}$/.test(logicalBucket), `invalid logical bucket: ${logicalBucket}`);
  ensure(!key.includes("\\"), "object key must not contain backslashes");
  ensure(!key.split("/").includes(".."), "object key must not contain .. segments");
  return { logicalBucket, key };
}

export function buildSignedGetUrl(client, key, options = {}) {
  const now = options.now || new Date();
  // Limit signed URLs to the short sharing window allowed by this command.
  const expiresSeconds = options.expiresSeconds === undefined
    ? DEFAULT_SIGNED_URL_SECONDS
    : Number(options.expiresSeconds);
  ensure(Number.isInteger(expiresSeconds) && expiresSeconds > 0, "--expires must be a positive integer");
  ensure(expiresSeconds <= MAX_SIGNED_URL_SECONDS, `--expires must not exceed ${MAX_SIGNED_URL_SECONDS}`);
  const expires = Math.floor(now.getTime() / 1000) + expiresSeconds;
  const stringToSign = `GET\n\n\n${expires}\n/${client.bucket}/${key}`;
  const signature = crypto
    .createHmac("sha1", client.accessKeySecret)
    .update(stringToSign, "utf8")
    .digest("base64");
  const url = new URL(client.baseUrl);
  url.hostname = `${client.bucket}.${client.baseUrl.hostname}`;
  url.pathname = `/${encodeObjectPath(key)}`;
  url.searchParams.set("OSSAccessKeyId", client.accessKeyId);
  url.searchParams.set("Expires", String(expires));
  url.searchParams.set("Signature", signature);
  return url.toString();
}

export async function resolveAccessibleObject(client, key, options = {}) {
  const fetchFn = options.fetchFn || fetch;
  const getObjectFn = options.getObjectFn || getObject;
  const unsignedUrl = new URL(client.baseUrl);
  unsignedUrl.hostname = `${client.bucket}.${client.baseUrl.hostname}`;
  unsignedUrl.pathname = `/${encodeObjectPath(key)}`;
  const publicUrl = unsignedUrl.toString();
  // Prefer a stable unsigned URL when the object is already public.
  const publicStatus = await verifyObjectUrl(publicUrl, fetchFn);
  if (publicStatus) {
    return { access: "public-url", verifiedStatus: publicStatus, url: publicUrl };
  }

  // Signed URLs and authenticated downloads need credentials after public access fails.
  if (!client.accessKeyId || !client.accessKeySecret) {
    ensure(
      publicStatus !== null,
      "public URL could not be verified and OSS credentials are not configured"
    );
    throw new Error("object is not publicly accessible and OSS credentials are not configured");
  }
  const now = options.now || new Date();
  // Limit signed URLs to the short sharing window allowed by this command.
  const expiresSeconds = options.expiresSeconds === undefined
    ? DEFAULT_SIGNED_URL_SECONDS
    : Number(options.expiresSeconds);
  ensure(Number.isInteger(expiresSeconds) && expiresSeconds > 0, "--expires must be a positive integer");
  ensure(expiresSeconds <= MAX_SIGNED_URL_SECONDS, `--expires must not exceed ${MAX_SIGNED_URL_SECONDS}`);
  const signedUrl = buildSignedGetUrl(client, key, { now, expiresSeconds });
  // Keep private objects private while making the link temporarily shareable.
  const signedStatus = await verifyObjectUrl(signedUrl, fetchFn);
  if (signedStatus) {
    return {
      access: "signed-url",
      expiresAt: new Date(now.getTime() + expiresSeconds * 1000).toISOString(),
      verifiedStatus: signedStatus,
      url: signedUrl
    };
  }

  // Preserve user access by downloading only after both URL forms fail.
  const object = await getObjectFn(client, key);
  const localPath = safeDownloadPath(
    options.outDir || path.join(os.homedir(), "Downloads", "oss", client.bucket),
    key
  );
  fs.mkdirSync(path.dirname(localPath), { recursive: true });
  fs.writeFileSync(localPath, object.body);
  return {
    access: "local-file",
    contentLength: object.body.length,
    contentType: object.headers["content-type"] || null,
    localPath
  };
}

async function verifyObjectUrl(url, fetchFn) {
  try {
    const response = await fetchFn(url, {
      method: "GET",
      headers: { range: "bytes=0-0" }
    });
    if (response.body && typeof response.body.cancel === "function") {
      await response.body.cancel();
    }
    return response.status === 200 || response.status === 206 ? response.status : false;
  } catch {
    return null;
  }
}

async function requestOss(client, method, pathname, searchParams = new URLSearchParams()) {
  const now = new Date();
  const amzDate = formatAmzDate(now);
  const dateScope = amzDate.slice(0, 8);
  const canonicalUri = pathname;
  const canonicalResourceUri = `/${client.bucket}${pathname}`;
  const canonicalQuery = canonicalizeQuery(searchParams);
  const host = `${client.bucket}.${client.baseUrl.host}`;
  const headers = {
    "x-oss-content-sha256": "UNSIGNED-PAYLOAD",
    "x-oss-date": amzDate
  };
  const additionalHeaders = "";
  const canonicalHeaders = Object.keys(headers)
    .sort()
    .map((name) => `${name}:${headers[name]}\n`)
    .join("");
  const canonicalRequest = [
    method,
    canonicalResourceUri,
    canonicalQuery,
    canonicalHeaders,
    additionalHeaders,
    "UNSIGNED-PAYLOAD"
  ].join("\n");
  const scope = `${dateScope}/${client.region}/oss/aliyun_v4_request`;
  const stringToSign = [
    "OSS4-HMAC-SHA256",
    amzDate,
    scope,
    sha256Hex(canonicalRequest)
  ].join("\n");
  const signature = signV4(client.accessKeySecret, dateScope, client.region, stringToSign);
  const authorization = `OSS4-HMAC-SHA256 Credential=${client.accessKeyId}/${scope},Signature=${signature}`;
  const url = new URL(client.baseUrl);
  url.hostname = host;
  url.pathname = canonicalUri;
  url.search = canonicalQuery;

  const response = await fetch(url, {
    method,
    headers: {
      ...headers,
      authorization
    }
  });

  const body = method === "HEAD" ? Buffer.alloc(0) : Buffer.from(await response.arrayBuffer());
  const responseHeaders = Object.fromEntries(response.headers.entries());

  if (!response.ok) {
    throw new Error(`OSS ${method} ${redactUrl(url)} failed: ${response.status} ${response.statusText} ${body.toString("utf8").slice(0, 300)}`);
  }

  return { status: response.status, headers: responseHeaders, body };
}

function parseListObjects(xml) {
  const matches = [...xml.matchAll(/<Contents>([\s\S]*?)<\/Contents>/g)];
  return matches.map((match) => ({
    key: decodeXml(textBetween(match[1], "Key")),
    lastModified: decodeXml(textBetween(match[1], "LastModified")),
    size: Number(decodeXml(textBetween(match[1], "Size")) || 0)
  }));
}

function summarizeInfoJson(info) {
  const arrayCount = (value) => Array.isArray(value) ? value.length : null;
  return {
    topLevelKeys: Object.keys(info),
    workCode: info.workCode ?? null,
    subject: info.subject ?? null,
    evaluateType: info.evaluateType ?? null,
    paperType: info.paperType ?? null,
    printType: info.printType ?? null,
    totalSheetCount: info.totalSheetCount ?? null,
    paperOrientation: info.paperOrientation ?? null,
    answerSheetMode: info.answerSheetMode ?? null,
    studentImagesCount: arrayCount(info.studentImages),
    scanAnswersImagesCount: arrayCount(info.scanAnswersImages),
    questionImagesCount: arrayCount(info.questionImages),
    answerImagesCount: arrayCount(info.answerImages),
    groupItemsCount: arrayCount(info.groupItems)
  };
}

export function parseOssUrl(rawUrl) {
  const url = new URL(rawUrl);
  const hostParts = url.hostname.split(".");
  const bucket = hostParts[0];
  const key = decodeURIComponent(url.pathname.replace(/^\/+/, ""));
  const match = key.match(/(?:^|\/)work2images\/work3\/([^/]+)(?:\/|$)/);
  const workGuid = match ? match[1] : null;
  const relativePath = workGuid
    ? key.slice(key.indexOf(`/work3/${workGuid}/`) + `/work3/${workGuid}/`.length)
    : null;

  const queryNames = new Set([...url.searchParams.keys()].map((name) => name.toLowerCase()));
  // V1 URLs are signed only when the credential, expiry, and signature are all present.
  const hasV1Signature = queryNames.has("ossaccesskeyid") &&
    queryNames.has("expires") &&
    queryNames.has("signature");

  return {
    bucket,
    key,
    workGuid,
    relativePath,
    hasSignedQuery: hasV1Signature || [...queryNames].some((name) => name.startsWith("x-oss-"))
  };
}

function buildObjectKey(config, workGuid, relativePath = "", options = {}) {
  const cleanGuid = ensureWorkGuid(workGuid);
  const cleanRelative = cleanRelativePath(relativePath);
  const suffix = cleanRelative || "";
  const withSlash = options.directory && suffix && !suffix.endsWith("/") ? `${suffix}/` : suffix;
  return [config.workRoot || DEFAULT_WORK_ROOT, cleanGuid, withSlash].filter(Boolean).join("/");
}

function cleanRelativePath(value) {
  const clean = String(value || "").replace(/^\/+/, "");
  ensure(!clean.includes("\\"), "relative path must not contain backslashes");
  ensure(!clean.split("/").includes(".."), "relative path must not contain .. segments");
  ensure(!clean.startsWith(DEFAULT_WORK_ROOT), "relative path must be inside the workGuid root, not the full OSS key");
  return clean;
}

function ensureWorkGuid(value) {
  ensure(value, "workGuid is required");
  const workGuid = String(value);
  ensure(/^[A-Za-z0-9][A-Za-z0-9_-]{7,120}$/.test(workGuid), `invalid workGuid: ${workGuid}`);
  ensure(!workGuid.includes("/"), "workGuid must not contain slash");
  return workGuid;
}

function safeDownloadPath(outDir, relativePath) {
  const clean = cleanRelativePath(relativePath);
  const resolvedBase = path.resolve(outDir);
  const resolvedPath = path.resolve(resolvedBase, clean);
  ensure(resolvedPath === resolvedBase || resolvedPath.startsWith(`${resolvedBase}${path.sep}`), "download path escapes output directory");
  return resolvedPath;
}

function isTextPath(key) {
  return TEXT_EXTENSIONS.has(path.extname(key).toLowerCase());
}

function firstValue(...values) {
  return values.find((value) => value !== undefined && value !== null && String(value).trim() !== "");
}

function stripQuotes(value) {
  return String(value).replace(/^["']|["']$/g, "");
}

function trimSlash(value) {
  return String(value).replace(/\/+$/, "");
}

function encodeObjectPath(key) {
  return key.split("/").map(encodeURIComponent).join("/");
}

function canonicalizeQuery(searchParams) {
  return [...searchParams.entries()]
    .sort(([aKey, aValue], [bKey, bValue]) => aKey === bKey ? aValue.localeCompare(bValue) : aKey.localeCompare(bKey))
    .map(([key, value]) => `${encodeRfc3986(key)}=${encodeRfc3986(value)}`)
    .join("&");
}

function encodeRfc3986(value) {
  return encodeURIComponent(value).replace(/[!'()*]/g, (char) => `%${char.charCodeAt(0).toString(16).toUpperCase()}`);
}

function formatAmzDate(date) {
  return date.toISOString().replace(/[:-]|\.\d{3}/g, "");
}

function sha256Hex(value) {
  return crypto.createHash("sha256").update(value, "utf8").digest("hex");
}

function hmac(key, value) {
  return crypto.createHmac("sha256", key).update(value, "utf8").digest();
}

function signV4(secret, dateScope, region, stringToSign) {
  const dateKey = hmac(Buffer.from(`aliyun_v4${secret}`, "utf8"), dateScope);
  const regionKey = hmac(dateKey, region);
  const productKey = hmac(regionKey, "oss");
  const signingKey = hmac(productKey, "aliyun_v4_request");
  return crypto.createHmac("sha256", signingKey).update(stringToSign, "utf8").digest("hex");
}

function textBetween(xml, tagName) {
  const match = xml.match(new RegExp(`<${tagName}>([\\s\\S]*?)<\\/${tagName}>`));
  return match ? match[1] : "";
}

function decodeXml(value) {
  return String(value)
    .replace(/&lt;/g, "<")
    .replace(/&gt;/g, ">")
    .replace(/&amp;/g, "&")
    .replace(/&quot;/g, "\"")
    .replace(/&apos;/g, "'");
}

function redactUrl(url) {
  const safeUrl = new URL(url.toString());
  for (const name of [...safeUrl.searchParams.keys()]) {
    if (name.toLowerCase().includes("signature") || name.toLowerCase().includes("credential")) {
      safeUrl.searchParams.set(name, "[REDACTED]");
    }
  }
  return safeUrl.toString();
}

export function sanitizeError(error) {
  const message = redactSensitiveText(String(error && error.message ? error.message : error));
  const cause = sanitizeErrorCause(error && error.cause);
  return cause ? `${message}; cause: ${cause}` : message;
}

function sanitizeErrorCause(cause) {
  if (!cause) {
    return "";
  }

  const fields = [];
  for (const name of ["name", "code", "syscall", "hostname", "host", "port", "message"]) {
    const value = cause[name];
    if (value !== undefined && value !== null && String(value) !== "") {
      fields.push(`${name}=${redactSensitiveText(value)}`);
    }
  }
  return fields.join(", ");
}

function redactSensitiveText(value) {
  return String(value)
    .replace(/<Authorization>[\s\S]*?<\/Authorization>/gi, "<Authorization>[REDACTED]</Authorization>")
    .replace(/(AccessKeyId|AccessKeySecret|authorization|Credential|Signature)=([^,\s&]+)/gi, "$1=[REDACTED]")
    .replace(/x-oss-(credential|signature)=([^&\s]+)/gi, "x-oss-$1=[REDACTED]");
}

function ensure(condition, message) {
  if (!condition) {
    throw new Error(message);
  }
}

function writeJson(value) {
  console.log(JSON.stringify(value, null, 2));
}
