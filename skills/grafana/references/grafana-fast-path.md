# Grafana Fast Path

This is the shared fast-path contract.

## Shared Order

1. Reuse the local Grafana login/session.
2. Load or refresh dashboard metadata through `python3 scripts/grafana.py`.
3. Query logs through Grafana APIs before using a rendered page.
4. Keep the first query narrow: one app, one identifier, and the smallest useful time range.
5. Use browser fallback only for login refresh or dashboard structure drift.

## Shared Output

Return the query expression, time range, dashboard URL when available, and the call-chain node each result supports.
