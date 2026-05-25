# Personal Knowledge LLM Quality Judge Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add a local LLM write-quality judge to the private Obsidian log scanner so sessions are routed to `none`, `daily`, or `candidate` before Obsidian write.

**Architecture:** Keep the production path small: normalize session evidence, run one LLM judge call per date, then let writer guards enforce schema, evidence, path, and write safety. Do not add content hard rules, review queues, dashboards, vector search, or external eval platforms.

**Tech Stack:** Python 3.14 standard library, `unittest`, existing Codex CLI subprocess pattern, existing private scanner package under `~/.codex/local/obsidian-log-sync`.

---

## Guardrails For Every Task

- Do not add keyword, length, source-prefix, path, tool-name, CLI-type, or fixed-scenario content rules.
- Do not route by golden case similarity.
- Do not create an Obsidian Review directory.
- Keep `manual_review=true` in scanner batch reports only.
- Treat Writer Guard failures as `invalid_output` or write-blocked status, not as `low_value`.
- Preserve existing user and Claude edits outside the files listed for each task.

## Task 1: Add Judge Data Model And Validation

**Files:**
- Create: `~/.codex/local/obsidian-log-sync/scripts/quality_judge.py`
- Test: `~/.codex/local/obsidian-log-sync/tests/test_quality_judge.py`

**Step 1: Write failing tests for route parsing**

Add tests that cover:

```python
def test_validate_candidate_requires_evidence_refs():
    payload = {
        "sessions": [
            {
                "source": "codex",
                "source_key": "codex:abc",
                "session_id": "abc",
                "write_route": "candidate",
                "manual_review": False,
                "confidence": "high",
                "claims": [{"claim": "A reusable decision", "reason": "Future use"}],
                "counterarguments": [],
                "reasoning_summary": "Valid looking but missing evidence.",
            }
        ]
    }
    with self.assertRaises(ValueError):
        validate_judge_payload(payload, review_payload)
```

Also test:

- `write_route=none` allows `claims=[]`.
- `write_route=none` requires `none_reason`.
- `write_route=daily` allows at most one claim.
- `write_route=candidate` allows at most three claims.
- `manual_review=true` is accepted only as metadata and does not create a fourth write route.
- Unknown routes fail validation.

**Step 2: Run test to verify it fails**

Run:

```console
cd ~/.codex/local/obsidian-log-sync
python3 -m unittest tests.test_quality_judge -v
```

Expected: FAIL because `scripts.quality_judge` does not exist.

**Step 3: Implement minimal validator**

In `scripts/quality_judge.py`, add:

```python
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

WRITE_ROUTES = {"none", "daily", "candidate"}
NONE_REASONS = {"low_value", "uncertain", "unsafe"}
CONFIDENCE_VALUES = {"low", "medium", "high"}


@dataclass(frozen=True)
class JudgeGenerationResult:
    date: str
    status: str
    detail: str
    path: Path | None = None

    @property
    def created(self) -> bool:
        return self.status == "created"


def validate_judge_payload(payload: dict[str, Any], review_payload: dict[str, Any]) -> None:
    ...
```

Validation rules:

- Payload root must be object with `sessions` list.
- Sessions must match review input by `source_key`; no missing or extra sessions.
- `source`, `source_key`, `session_id` must match review input.
- `write_route` must be `none`, `daily`, or `candidate`.
- `none_reason` is required only for `write_route=none`.
- `none_reason` must be one of `low_value`, `uncertain`, `unsafe`.
- `manual_review` must be boolean.
- `confidence` must be `low`, `medium`, or `high`.
- `claims` must be list.
- `none` allows zero claims.
- `daily` allows at most one claim.
- `candidate` requires one to three claims.
- Each candidate claim requires non-empty `claim`, `reason`, and non-empty `evidence_refs`.
- `counterarguments` must be a list and max two items.
- `reasoning_summary` must be non-empty text.

Keep helper names plain and local: `_required_text`, `_optional_text`, `_text_list`, `_review_sessions`, `_session_key`.

**Step 4: Run test to verify it passes**

Run:

```console
cd ~/.codex/local/obsidian-log-sync
python3 -m unittest tests.test_quality_judge -v
```

Expected: PASS.

**Step 5: Commit**

This private scanner directory is not a git repository. Do not commit. Record changed files in the final implementation summary.

## Task 2: Generate Judge Output From Review Input

**Files:**
- Modify: `~/.codex/local/obsidian-log-sync/scripts/quality_judge.py`
- Test: `~/.codex/local/obsidian-log-sync/tests/test_quality_judge.py`

**Step 1: Write failing tests for `judge_date`**

Add tests:

- `judge_date` writes `quality-judge/YYYY-MM-DD.json` when `_run_codex_judge` returns valid payload.
- Existing valid judge output is reused unless `force=True`.
- Invalid generated output retries once and then succeeds.
- Repeated Codex runtime failure returns `status="failed"` and writes no judge file.
- Prompt contains no scenario examples such as fixed greetings, short messages, or CLI-specific priority rules.

Example:

```python
with patch("scripts.quality_judge._run_codex_judge", return_value=generated):
    result = judge_date(work_root, "2026-05-19")
self.assertTrue(result.created)
```

**Step 2: Run test to verify it fails**

Run:

```console
cd ~/.codex/local/obsidian-log-sync
python3 -m unittest tests.test_quality_judge -v
```

Expected: FAIL because `judge_date` is missing.

**Step 3: Implement generation**

In `quality_judge.py`, implement:

```python
def judge_date(
    work_root: Path,
    date: str,
    *,
    force: bool = False,
    codex_bin: str | None = None,
    timeout_seconds: int = 600,
    max_attempts: int = 2,
) -> JudgeGenerationResult:
    ...
```

Use existing patterns from `scripts.ai_summarizer`:

- Input: `ai-review-input/<date>.json`
- Output: `quality-judge/<date>.json`
- Codex command uses `--output-schema` and `--output-last-message`.
- Use temporary schema file and output file.
- Parse wrapped JSON with `_parse_model_json`.
- Atomic write JSON.

Output schema should mirror the judge contract:

```json
{
  "sessions": [
    {
      "source": "string",
      "source_key": "string",
      "session_id": "string",
      "write_route": "none|daily|candidate",
      "none_reason": "low_value|uncertain|unsafe",
      "manual_review": true,
      "confidence": "low|medium|high",
      "claims": [
        {
          "claim": "string",
          "evidence_refs": ["turn_1"],
          "reason": "string"
        }
      ],
      "counterarguments": ["string"],
      "reasoning_summary": "string"
    }
  ]
}
```

Prompt requirements:

- Tell the model it is the only content-value judge.
- Require `write_route` only from `none`, `daily`, `candidate`.
- Require no scenario-list reasoning.
- Require evidence refs based on normalized message indexes.
- State that uncertainty uses `write_route=none`, `none_reason=uncertain`, `manual_review=true`.
- State that manual review is batch-report metadata, not an Obsidian route.

**Step 4: Run test to verify it passes**

Run:

```console
cd ~/.codex/local/obsidian-log-sync
python3 -m unittest tests.test_quality_judge -v
```

Expected: PASS.

## Task 3: Update Review Pack To Provide Evidence IDs

**Files:**
- Modify: `~/.codex/local/obsidian-log-sync/scripts/ai_review_pack.py`
- Test: `~/.codex/local/obsidian-log-sync/tests/test_ai_review_pack.py`

**Step 1: Write failing test for evidence IDs**

Extend `test_write_ai_review_pack_contains_context_and_schema`:

```python
self.assertIn("evidence_items", data["sessions"][0])
self.assertEqual(data["sessions"][0]["evidence_items"][0]["id"], "turn_1")
self.assertEqual(data["sessions"][0]["evidence_items"][0]["role"], "user")
self.assertIn("content", data["sessions"][0]["evidence_items"][0])
```

Add a test that tool summaries get stable IDs:

```python
self.assertEqual(data["sessions"][0]["evidence_items"][-1]["id"], "tool_1")
```

**Step 2: Run test to verify it fails**

Run:

```console
cd ~/.codex/local/obsidian-log-sync
python3 -m unittest tests.test_ai_review_pack -v
```

Expected: FAIL because `evidence_items` is missing.

**Step 3: Implement evidence items**

In `_session_payload`, keep existing `messages` for backward compatibility and add `evidence_items`.

Message evidence shape:

```python
{"id": "turn_1", "role": "user", "content": "..."}
```

Tool evidence shape:

```python
{"id": "tool_1", "role": "tool", "content": "..."}
```

Derive `role` from message prefix when present:

- `"user:"` -> `user`
- `"assistant:"` -> `assistant`
- otherwise `message`

Do not drop messages by content. Preserve the current `MAX_REVIEW_MESSAGES` cap only as an input-size limit.

**Step 4: Run test to verify it passes**

Run:

```console
cd ~/.codex/local/obsidian-log-sync
python3 -m unittest tests.test_ai_review_pack -v
```

Expected: PASS.

## Task 4: Make Summarizer Consume Judge Routes

**Files:**
- Modify: `~/.codex/local/obsidian-log-sync/scripts/ai_summarizer.py`
- Modify: `~/.codex/local/obsidian-log-sync/scripts/daily_writer.py`
- Modify: `~/.codex/local/obsidian-log-sync/scripts/candidate_writer.py`
- Test: `~/.codex/local/obsidian-log-sync/tests/test_ai_summarizer.py`
- Test: `~/.codex/local/obsidian-log-sync/tests/test_writers.py`

**Step 1: Write failing tests**

In `test_ai_summarizer.py`, add:

- Summary validation rejects a session whose `write_route` differs from judge output.
- Summary validation rejects candidate content not backed by judge claims.
- Summary validation allows `write_route=none` with empty `items` and `candidates`.

In `test_writers.py`, add:

- `write_daily` skips sessions with `write_route=none`.
- `write_daily` writes only route `daily` or `candidate` sessions.
- `write_candidates` writes only route `candidate` candidates.
- `write_candidates` rejects candidates missing `evidence_refs`.

**Step 2: Run targeted tests to verify failures**

Run:

```console
cd ~/.codex/local/obsidian-log-sync
python3 -m unittest tests.test_ai_summarizer tests.test_writers -v
```

Expected: FAIL because summary and writer code do not know judge routes.

**Step 3: Extend summary schema**

Update `ai_summarizer._output_schema()` session schema to include:

- `write_route`
- `none_reason`
- `manual_review`
- `confidence`

Candidate schema should include:

- `title`
- `content`
- `reason`
- `evidence_refs`

Remove new use of `asset_type` from generated output. Keep backward-compatible readers only if needed for existing pending files, but do not require `asset_type` for new AI output.

Update `_validate_summary_payload(summary_payload, review_payload)` to also load `quality-judge/<date>.json` or accept an optional judge payload if cleaner. Validation should enforce:

- Summary session routes match judge routes.
- `write_route=none` has no candidates and no Daily item requirement.
- `write_route=daily` may have one concise item and no candidates.
- `write_route=candidate` may have Daily summary plus candidates, but each candidate must map to a judge claim or evidence refs.

Keep content-value judgment out of code. Validation only checks consistency with judge output and required references.

**Step 4: Update summarizer prompt**

Change prompt from “every input session must output one corresponding session with non-empty items” to:

- Every input session still gets a session object.
- `write_route=none`: no Daily item required, no candidate.
- `write_route=daily`: generate a short Daily index from approved judge claim.
- `write_route=candidate`: generate candidate only from approved judge claims.
- Do not introduce claims not present in judge output.

**Step 5: Update writers**

In `daily_writer.AiSessionSummary`, add:

- `write_route: str = "daily"`
- `manual_review: bool = False`
- `none_reason: str = ""`

In `load_ai_summaries`, parse route fields.

In `write_daily`, skip AI summaries with `write_route=none`. Keep fallback placeholder behavior only for missing AI summary before judge is ready; once judge summaries are present, none routes should not write.

In `candidate_writer.load_ai_candidates`, only load candidates for sessions where `write_route=="candidate"`.

In candidate formatting, use canonical frontmatter from `personal-knowledge` skill:

```yaml
---
type: agent-log
status: 候选
domain: 01-Agent工作台
tags: []
source: codex
related_issues: []
pattern_candidate: ""
---
```

Scanner-generated candidates may add `session_id` for dedupe. Do not emit deprecated `asset_type`, `source_key`, `session_date`, credential frontmatter fields, or old candidate schemas.

**Step 6: Run targeted tests**

Run:

```console
cd ~/.codex/local/obsidian-log-sync
python3 -m unittest tests.test_ai_summarizer tests.test_writers -v
```

Expected: PASS.

## Task 5: Replace Quality Gate With Writer Guard Semantics

**Files:**
- Modify: `~/.codex/local/obsidian-log-sync/scripts/quality_gate.py`
- Test: `~/.codex/local/obsidian-log-sync/tests/test_quality_gate.py`

**Step 1: Write failing tests**

Add tests:

- Guard passes `none` route without writing source key as ready.
- Guard records `manual_review=true` in report but does not fail whole date.
- Guard fails `candidate` missing `evidence_refs` with `failure_stage="structure"` or `invalid_output`.
- Guard failure does not report `low_value`.
- Report includes `ready_source_keys` or equivalent only for `daily` and `candidate` sessions that passed guard.

**Step 2: Run tests**

Run:

```console
cd ~/.codex/local/obsidian-log-sync
python3 -m unittest tests.test_quality_gate -v
```

Expected: FAIL until guard semantics are updated.

**Step 3: Implement guard semantics**

Keep `evaluate_date` public API if possible, but change behavior:

- Load review input.
- Load judge output.
- Load AI summary.
- Validate consistency.
- Build report with route counts, manual review items, invalid outputs, and `summary_source_keys` for writable sessions.

Remove or disable the second AI quality-review call for first-phase MVP. The new quality control is the single Judge plus mechanical guard.

Report should distinguish:

- `status="passed"` when all writable outputs are valid, even if some sessions are `none` or `manual_review=true`.
- `status="failed"` when schema, evidence, frontmatter, or route consistency fails.

**Step 4: Run tests**

Run:

```console
cd ~/.codex/local/obsidian-log-sync
python3 -m unittest tests.test_quality_gate -v
```

Expected: PASS.

## Task 6: Wire Judge Into `run_sync`

**Files:**
- Modify: `~/.codex/local/obsidian-log-sync/scripts/run_sync.py`
- Test: `~/.codex/local/obsidian-log-sync/tests/test_run_sync.py`

**Step 1: Write failing orchestration tests**

Add tests:

- `run_once` calls `quality_judge.judge_date` before `ai_summarizer.summarize_date`.
- When judge generation fails, summary and Obsidian writer are not called.
- When judge creates new output, sync refreshes pending after summarizer.
- `manual_review=true` does not call Obsidian writer for that session.
- Writer receives only source keys from guard report for `daily` and `candidate`.

**Step 2: Run tests**

Run:

```console
cd ~/.codex/local/obsidian-log-sync
python3 -m unittest tests.test_run_sync -v
```

Expected: FAIL because `run_sync` does not call judge yet.

**Step 3: Implement orchestration**

Update imports:

```python
from . import ai_summarizer, obsidian_rest_writer, quality_gate, quality_judge, sync
```

For each review date:

1. Call `quality_judge.judge_date(work_root, daily_date)`.
2. If failed, print `quality_judge[date]=failed:...` and skip the date.
3. Call `ai_summarizer.summarize_date(...)`.
4. Run writer guard via `quality_gate.evaluate_date(...)`.
5. Only append date to ready dates when guard passes and has at least one writable source key.

Keep current two-pass sync refresh if generated outputs changed.

**Step 4: Run tests**

Run:

```console
cd ~/.codex/local/obsidian-log-sync
python3 -m unittest tests.test_run_sync -v
```

Expected: PASS.

## Task 7: Add Golden Case Offline Regression Entry

**Files:**
- Create: `~/.codex/local/obsidian-log-sync/golden-cases/README.md`
- Create: `~/.codex/local/obsidian-log-sync/golden-cases/cases.json`
- Create: `~/.codex/local/obsidian-log-sync/scripts/judge_golden_cases.py`
- Test: `~/.codex/local/obsidian-log-sync/tests/test_judge_golden_cases.py`

**Step 1: Write failing tests**

Test that:

- Golden cases runner reads cases but is not imported by production `run_sync`.
- Case assertions check route, must-include claim fragments, must-not-claim fragments, and manual review flag.
- Runner exits non-zero on drift.

**Step 2: Run tests**

Run:

```console
cd ~/.codex/local/obsidian-log-sync
python3 -m unittest tests.test_judge_golden_cases -v
```

Expected: FAIL because files are missing.

**Step 3: Implement minimal offline runner**

`cases.json` should start with 10 representative shapes, but avoid production-matching language. Store expected semantic assertions:

```json
{
  "case_id": "llm-only-content-judgment",
  "expected_write_route": "candidate",
  "must_include_claim_fragments": ["内容价值判断", "LLM"],
  "must_not_claim_fragments": ["关键词", "长度规则"],
  "manual_review": false
}
```

The runner can accept precomputed judge output first. Do not make the first version call LLM automatically unless needed.

**Step 4: Run tests**

Run:

```console
cd ~/.codex/local/obsidian-log-sync
python3 -m unittest tests.test_judge_golden_cases -v
```

Expected: PASS.

## Task 8: Full Regression And No-Hardcoding Audit

**Files:**
- No new files expected.
- Review all modified implementation and test files.

**Step 1: Run full test suite**

Run:

```console
cd ~/.codex/local/obsidian-log-sync
python3 -m unittest discover -s tests -v
```

Expected: PASS.

**Step 2: Search for forbidden production hard rules**

Run:

```console
cd ~/.codex/local/obsidian-log-sync
rg -n "keyword|关键词|length|长度|greeting|寒暄|短句|source prefix|来源前缀|blacklist|whitelist|黑名单|白名单|Review/" scripts tests
```

Expected:

- No production code uses these as content routing rules.
- Tests may mention them only to assert they are forbidden.
- Prompt text may mention them only as “do not judge by these signals.”

**Step 3: Dry-run orchestration**

Run:

```console
cd ~/.codex/local/obsidian-log-sync
python3 -m scripts.run_sync --work-root /tmp/obsidian-log-sync-test --since 2026-05-20T00:00:00+08:00 --sources codex --active-grace-minutes 10
```

Expected:

- No writes outside `/tmp/obsidian-log-sync-test`.
- If no source data is present, clean skip or controlled error.
- No Obsidian write happens unless guard passes.

**Step 4: Final review**

Check:

```console
cd ~/.codex/local/obsidian-log-sync
python3 - <<'PY'
from pathlib import Path
for path in sorted(Path('.').glob('scripts/*.py')):
    print(path)
for path in sorted(Path('.').glob('tests/test_*.py')):
    print(path)
PY
```

Expected: use this only as a changed-file review aid. This directory is not a git repository, so list changed files manually in the final summary.

## Execution Notes

- The implementation target is private local code under `~/.codex/local/obsidian-log-sync`.
- Do not copy private paths, config, secrets, or session payloads into public rules.
- The public design spec lives at `docs/superpowers/specs/2026-05-20-personal-knowledge-llm-quality-judge-design.md`.
- This plan is intentionally MVP-sized. Do not add platform features while executing it.
