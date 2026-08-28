---
name: aliyun-oss
description: Use when inspecting Aliyun OSS, OSS Browser files, teacher-ai workGuid objects, templates, student uploads, info.json, signed OSS URLs, or bucket/object paths.
---

# Aliyun OSS

Use this skill to inspect OSS objects quickly and safely. Prefer the bundled read-only script before giving manual OSS Browser steps.

## Boundaries

- Treat AccessKey, Secret, signed URL query values, STS tokens, cookies, and Authorization headers as secrets.
- Never expose raw AccessKey or Secret. Return a short-lived signed URL only for an explicit object-access request in the current private conversation; do not copy it into durable logs, docs, commits, or skill files.
- Default to read-only operations. Use temp downloads for internal inspection; use a user-accessible directory only for an object-access fallback.
- Do not upload, delete, overwrite, make public, change ACL/policy, or generate long-lived public links unless the user explicitly asks and approves the target.
- If a user provides a signed URL, parse the bucket and object key from host/path; ignore query params except to note that a signature was present.

## Workflow

1. Identify the target from a workGuid, `oss://` path, HTTP OSS URL, or bucket/key pair.
2. For teacher-ai work files, read `references/teacher-ai.md` before deriving paths.
3. For an object-access request, run `scripts/oss_workguid.mjs url <logical-bucket/object-key>`. Return an anonymously verified public URL when available, otherwise a verified short-lived signed URL; fall back to a user-accessible local download only when neither URL verifies.
4. Run the other `scripts/oss_workguid.mjs` commands for deterministic teacher-ai workGuid lookups.
5. Return concise evidence: bucket, prefix/key, access type, verification status, expiry for signed URLs, important file names, and local path for fallback downloads.
6. Never present an object key, an unverified URL, or a temp-only cache path as an accessible final deliverable.

## Script Quick Start

Run from this skill directory or by absolute path:

```bash
node scripts/oss_workguid.mjs from-url "<oss-url>"
node scripts/oss_workguid.mjs url "<logical-bucket/object-key>" [--expires 7200] [--out DIR]
node scripts/oss_workguid.mjs list <workGuid> [subdir]
node scripts/oss_workguid.mjs info <workGuid>
node scripts/oss_workguid.mjs read <workGuid> templete/info.json
node scripts/oss_workguid.mjs download <workGuid> templete/<file>
```

Useful defaults:

- `list` shows all objects under `edumaterials/work2images/work3/<workGuid>/` unless a subdir is supplied.
- `info` reads `templete/info.json` and prints a compact JSON summary.
- `read` prints small text-like files only unless `--force` is provided.
- `download` writes to `/tmp/oss-workguid/<workGuid>/` unless `--out <dir>` is supplied.
- `url` first verifies an unsigned public URL, then a signed URL valid for two hours by default, and finally downloads under `~/Downloads/oss/` when URL access fails.

## When the Script Cannot Run

- If local config or credentials are missing, report the missing source without exposing partial values.
- If OSS returns 403, say authorization failed for the bucket/key; do not ask the user to paste secrets into chat.
- If OSS returns 404, report the exact bucket/key and try listing the nearest safe prefix.
- If public or signed URL verification fails but authenticated download succeeds, return the verified local download path and state that URL access failed.
- If the task is not teacher-ai workGuid based, use official OSS Browser/ossutil/MCP only when object-level access is available, still following the same redaction rules.
