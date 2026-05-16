# Project Call Chain

This is the shared call-chain mapping contract. Project-specific details belong in local config or the target project repository, not in this skill repository.

## Shared Order

1. Identify the entry API, route, job, queue message, or dashboard app from Grafana evidence.
2. Map the evidence to code using the configured repository root.
3. Prefer the full path: entry API -> business/service -> downstream RPC/service -> async consumer -> storage or external dependency.
4. Separate proven nodes from inferred nodes.

## Shared Output

Start with the call chain, then list the exact Grafana evidence that supports each node.
