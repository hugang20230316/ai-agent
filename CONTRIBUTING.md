# Contributing

This repository stores shared agent rules and skills. Do not commit private
configuration, credentials, sessions, logs, caches, company project paths, or
personal environment files.

## Rule Changes

Hugang can commit directly to `main`.

Everyone else must change `AGENTS.md` or `rules/**` through a pull request. The
pull request must be reviewed by Hugang before it is merged.

Before opening the pull request, run:

```bash
python3 scripts/verify_agent_rules.py
```

In the pull request, explain:

- What rule changed.
- Why it changed.
- How it was checked.
