---
name: grafana
description: "Query read-only data from a configured Grafana instance with persistent local login reuse. Use only when the user explicitly asks for Grafana, production/online evidence, dashboard evidence, or log evidence that cannot be handled by local/test data sources."
---

# Grafana

## Tooling

Use the single Python entry point from this skill directory:

```console
python3 scripts/grafana.py doctor
python3 scripts/grafana.py ensure-session
python3 scripts/grafana.py query-logs -App <app> -Query "<query>"
python3 scripts/grafana.py analyze-workguid -WorkGuid <work-guid>
```

Machine-specific Grafana hosts, dashboard UIDs, browser sessions, credentials, and local state paths must come from local config, environment variables, or explicit CLI arguments. Do not add platform-specific skill files or wrapper scripts.

## Shared Workflow

1. Confirm the user explicitly wants Grafana, online logs, production logs, dashboard evidence, or Explore evidence.
2. Reuse a persisted local login/session before asking the user for credentials.
3. Prefer Grafana HTTP/API query paths over page scraping.
4. Use browser automation only for login refresh or dashboard structure fallback through the unified Python entry point.
5. Map log evidence back to the related project call chain before presenting raw rows.
6. Separate evidence levels in the analysis:
   - Grafana/raw log evidence: the line explicitly records the value or event.
   - Reconstructed evidence: derived from code, database rows, object storage, or current service state.
   - Reproduction evidence: produced by a new request after the original incident.
7. When a failed downstream call is logged but the overall user flow later succeeds, check whether the success/fallback path logs input and output. If it does not, state that the successful downstream request cannot be proven from Grafana alone.
8. For environment-sensitive issues, always record the actual namespace, app, time window, request URL or service route used for the evidence. Do not assume similar-looking gray, test, staging, UAT, or production endpoints are interchangeable.

## Shared Guardrails

- Read-only only: do not save dashboards, edit panels, manage users, create API keys, acknowledge alerts, or change datasource settings.
- Do not commit hosts, dashboard IDs, cookies, credentials, sessions, app names, local state paths, or other environment-specific values.
- If evidence is inferred rather than proven, label it clearly.
- Do not keep using a shared test account after the user says another person needs it; switch to existing tokens, read-only logs, or user-executed requests.
- When providing JSON/HTML reproduction payloads, prefer a single-line compact JSON block or an attached/local file path. Warn that inserted line breaks or spaces inside HTML attributes, closing tags, GUIDs, or IDs can change results.
- If current reproduction differs from historical logs or screenshots, do not force them to match. Report both facts and identify the missing evidence needed to close the gap.

## Shared Output

Return the call chain first, then Grafana evidence, project mapping, reproduction evidence if any, and current judgment. Include the exact query or dashboard URL used when available.

For incident reports, include:

- Evidence level for each key claim.
- Exact namespace/app/time window/query expression used.
- Which request values are raw from logs and which are reconstructed.
- Whether the same payload currently reproduces the historical behavior.

## Troubleshooting Notes

- On Windows, Python may resolve the npm extensionless `agent-browser` shim and fail with `WinError 193`. Prefer a real executable shim such as `.cmd`, or use a Grafana API query fallback with the existing browser session cookie.
- If the skill wrapper fails but a valid Grafana session exists, direct read-only calls to Grafana's datasource query API are acceptable as a fallback. Keep datasource IDs, dashboard IDs, hosts, and cookies out of shared rules and final public artifacts unless the user explicitly needs a query URL.
- A successful HTTP 200 response can still contain a business error status. Report HTTP status and business status separately.
