# Step 0: Scaffold skill directory + CLI shell

## Status
**pending** — last update: 2026-07-15T00:00:00Z

## Read first
- `/PRD.md`
- `/CLAUDE.md` (project SSOT — Iron Laws, methodology=tdd, hook matrix)
- `/pyproject.toml` (existing build config — Python 3.11+, pytest, src/ layout)
- `/src/thread_analysis/analyzer.py` (existing thread-structures analyzer — DO NOT MODIFY, different domain from SNS)
- `/tests/test_analyzer.py` (existing test pattern to mirror)
- `phases/0-mvp/step{0..N-1}.md` (none — this is step 0)

## Task
Create a CLI shell for the new SNS analyzer skill that co-exists with the existing `thread_analysis` package (which analyzes thread *structures* — a different domain; do not touch it).

File paths to create:
- `src/thread_analysis/sns_analyzer.py` — module containing:
  - `cli_main(argv: list[str] | None = None) -> int` — entry point. Parses argv, returns 0 on success, non-zero on error. v0: must accept `--help` and exit 0, otherwise print "skill loaded — not yet implemented" and exit 0.
  - `__all__ = ["cli_main", "Post", "Summary"]` — exports the data shapes that steps 1+ will populate.
  - `Post` and `Summary` as `dataclass(frozen=True)` stubs with the fields below (so step 1/2 can extend without renaming):
    - `Post`: `id: str`, `text: str`, `created_at: datetime`, `like_count: int`, `reply_count: int`, `repost_count: int`
    - `Summary`: `post_count: int`, `top_topics: list[str]`, `topic_counts: dict[str, int]`, `avg_gap_hours: float`, `tone_tags: list[str]`, `top_engagement: list[Post]`
- `tests/test_sns_analyzer.py` — at minimum:
  - `test_cli_help_exits_zero` — `cli_main(["--help"])` returns 0.
  - `test_cli_no_args_exits_zero` — `cli_main([])` returns 0 and prints "not yet implemented".
  - `test_post_and_summary_dataclasses_exist` — imports `Post` and `Summary` and asserts field names match the contract above.

Do NOT touch:
- `src/thread_analysis/analyzer.py`
- `tests/test_analyzer.py`
- `pyproject.toml` (unless a runtime dep is unavoidable; if so, add a one-line comment explaining why)

Non-negotiable rules:
- TDD: write tests first, watch them fail, then implement the minimum to pass.
- Idempotency: re-running the CLI multiple times is safe.
- No Threads API, no OAuth, no network calls in this step.

## Acceptance Criteria
```bash
# AC1: package still imports (existing + new)
python -c "import thread_analysis; from thread_analysis.sns_analyzer import cli_main, Post, Summary" && echo OK

# AC2: new tests pass
pytest tests/test_sns_analyzer.py -v

# AC3: full suite still green (no regression on existing analyzer)
pytest tests/ -v

# AC4: CLI --help exits 0
python -c "from thread_analysis.sns_analyzer import cli_main; assert cli_main(['--help']) == 0" && echo OK
```

## Verification & Status Update (REQUIRED before claiming done)
1. Run the AC commands above. Quote each exit code.
2. Update `phases/0-mvp/index.json` for THIS step (one of three outcomes):
   - **Success** → `"status": "completed"`, `"summary": "<one-line: files created/modified + key decisions>"`
   - **Unrecoverable failure** (3 retries exhausted) → `"status": "error"`, `"error_message": "<concrete error: which AC failed, with exit code + last 3 lines>"`
   - **External dependency** (API key, manual config, human approval) → `"status": "blocked"`, `"blocked_reason": "<what's needed>"`, then STOP — do not continue to the next step.
3. **Status reporting contract — v0 (in-repo, what THIS PR enforces):** the
   installed runner (the dev-kit plugin's `lib/execute.py`) reads the
   step's status from the `phases/0-mvp/index.json` file written in step 2
   above. It does **not** currently parse the HTML-comment markers below;
   that capability (`parse_status_marker`) ships in a separate follow-up PR
   against the dev-kit plugin, **not** in this repository. Until that
   lands, status comes from the JSON file plus the sub-agent's exit code;
   the HTML-comment markers below are documented for forward compatibility
   only.

   Sub-agents SHOULD still emit these markers on the last two lines of
   their reply so that, once the runner catches up, no plan amendments
   are required:

```
<!-- status: completed | error | blocked -->
<!-- summary: <one-line outcome> | error_message: <concrete error> | blocked_reason: <what's needed> -->
```

   When the marker parser lands, the marker value MUST match the `status`
   field written to `index.json` in step 2. If they disagree, the runner
   falls back to the index.json status (so the contract is best-effort).

## Don't
- Do NOT modify `src/thread_analysis/analyzer.py` — it analyzes thread *structures* (replies/participants), a different domain. Reason: scope leak.
- Do NOT add Threads API / OAuth / network deps in this step. Reason: dependency-first ordering; step 1 owns that surface.
- Do NOT add storage, scheduling, or Instagram support. Reason: non-goals NG3/NG4/NG1.
- Do NOT skip TDD — write tests first, watch them fail, then make them pass. tdd-guard will block otherwise.
- Do NOT modify `pyproject.toml` runtime deps unless absolutely necessary; if you must, add a one-line comment in the dep declaration explaining why.
