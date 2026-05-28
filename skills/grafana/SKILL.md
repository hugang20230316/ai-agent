---
name: grafana
description: "Use only for online or grey-release problem investigation."
---

# Grafana

## Tooling

Use the single Python entry point from this skill directory:

```console
python3 scripts/grafana.py doctor
python3 scripts/grafana.py ensure-session
python3 scripts/grafana.py query-logs -App <app> -Query "<query>"
```

Machine-specific Grafana hosts, saved view identifiers, browser sessions, credentials, and local state paths must come from local config, environment variables, or explicit CLI arguments. Do not add platform-specific skill files or wrapper scripts.
Project-specific app mappings, business identifiers, log patterns, call chains, and incident timelines belong in that project's own config or rules, not in this shared Grafana skill.

## Shared Workflow

1. Use this skill only for online or grey-release problem investigation.
2. Default runtime investigation uses the project's test-environment evidence path and configured data/log sources, such as MongoDB or TiDB MCP when they are the direct evidence source.
3. Do not use Grafana for requests outside online or grey-release problem investigation. A generic request to check logs is not enough; the user or project evidence must name Grafana, grey release, online, production, dashboard, or Explore.
4. Reuse a persisted local login/session before asking the user for credentials.
5. Prefer Grafana HTTP/API query paths over page scraping.
6. Use browser automation only for login refresh or configured view fallback through the unified Python entry point.
7. Map log evidence back to the related project call chain before presenting raw rows.
8. Separate evidence levels in the analysis:
   - Grafana/raw log evidence: the line explicitly records the value or event.
   - Reconstructed evidence: derived from code, database rows, object storage, or current service state.
   - Replay evidence: produced by a new request after the original incident.
9. When the user asks whether evidence has been obtained, answer that first with "got it" or "not got it"; do not explain hypotheses before stating evidence status.
10. When a failed downstream call is logged but the overall user flow later succeeds, check whether the success/fallback path logs input and output. If it does not, state that the successful downstream request cannot be proven from Grafana alone.
11. For environment-sensitive issues, always record the actual evidence source, scope, time window, request URL or service route used for the evidence. Do not substitute a different environment or observability layer without explicit user direction.

## Shared Guardrails

- Read-only only: do not save views, edit panels, manage users, create API keys, acknowledge alerts, or change datasource settings.
- Do not commit hosts, saved view IDs, cookies, credentials, sessions, app names, local state paths, or other environment-specific values.
- If evidence is inferred rather than proven, label it clearly.
- Do not keep using a shared test account after the user says another person needs it; switch to existing tokens, read-only logs, or user-executed requests.
- When providing JSON/HTML replay payloads, prefer a single-line compact JSON block or an attached/local file path. Warn that inserted line breaks or spaces inside HTML attributes, closing tags, GUIDs, or IDs can change results.
- If current replay differs from historical logs or screenshots, do not force them to match. Report both facts and identify the missing evidence needed to close the gap.

## Output Contract

Return the call chain first, then Grafana evidence, project mapping, replay evidence if any, and current judgment. Include the exact query or evidence URL used when available.

For incident reports, include:

- Evidence level for each key claim.
- Exact namespace/app/time window/query expression used.
- Which request values are raw from logs and which are reconstructed.
- Whether the same payload currently replays the historical behavior.

## Troubleshooting Notes

- On Windows, Python may resolve the npm extensionless `agent-browser` shim and fail with `WinError 193`. Prefer a real executable shim such as `.cmd`, or use a Grafana API query fallback with the existing browser session cookie.
- If `ensure-session` fails with `net::ERR_CONNECTION_CLOSED`, check inherited proxy variables first (`HTTP_PROXY`, `HTTPS_PROXY`, `ALL_PROXY`, lowercase variants). Some internal Grafana hosts are reachable directly but fail through a local proxy. Retry with a clean env, e.g. `env -u HTTPS_PROXY -u HTTP_PROXY -u ALL_PROXY -u https_proxy -u http_proxy -u all_proxy python3 scripts/grafana.py ensure-session`.
- If agent-browser reports `Domain '<host>' is not in the allowed domains list` even when the host is passed in `--allowed-domains`, check for a stale running agent-browser daemon/session. `agent-browser close --all` and retry. A daemon started with a restrictive allowlist can persist across commands and ignore broader later flags.
- If the wrapper query expression still contains `$app` or `$namespace`, patch `expand_expr` to replace both `${var}` and bare `$var` placeholders; otherwise logs may be unscoped and misleading.
- If the skill wrapper fails but a valid Grafana session exists, direct read-only calls to Grafana's datasource query API are acceptable as a fallback. Keep datasource IDs, saved view IDs, hosts, and cookies out of shared rules and final public artifacts unless the user explicitly needs a query URL.
- A successful HTTP 200 response can still contain a business error status. Report HTTP status and business status separately.
