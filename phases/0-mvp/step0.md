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
- `src/thread_analysis/sns_types.py` — **leaf data shapes module** (`from __future__ import annotations` only, NO imports from `sns_analyzer` / `sns_client` / `sns_summarizer`):
  - `cli_main` is exported from `sns_analyzer` AND lives there as the CLI entry point.
  - But `sns_client` (data plane), `sns_summarizer` (pure logic), and `sns_analyzer` (CLI wiring) all import `Post` / `Summary` from this leaf. Putting the dataclasses here breaks what would otherwise be a circular import (`sns_analyzer` imports `sns_summarizer` for `summarize(...)`; `sns_summarizer` imports `Post` from `sns_analyzer` if `Post` lives there → cycle).
- `src/thread_analysis/sns_analyzer.py` — CLI module:
  - `cli_main(argv: list[str] | None = None) -> int` — entry point. Parses argv, returns 0 on success, non-zero on error. v0: must accept `--help` and exit 0, otherwise print "skill loaded — not yet implemented" and exit 0.
  - **Re-export** `Post`, `Summary`, `__all__ = ["cli_main", "Post", "Summary"]` from `sns_types` so the public surface (and step 0 AC1) keeps importing `from thread_analysis.sns_analyzer import cli_main, Post, Summary`.
  - `Post` and `Summary` are NOT defined here — they live in `sns_types` to break the import cycle.
- `.claude/skills/analyze-my-threads/SKILL.md` (and `scripts/analyze-my-threads.py` referenced from SKILL.md) — **the Claude Code skill entry point**. Without this file, `claude` cannot invoke `analyze-my-threads` as a Skill; the CLI works as a Python module but is not installable as a skill. The file MUST:
  - front-matter: `name: analyze-my-threads`, `description: <1-line>`.
  - body: short usage + the exact command `python -m thread_analysis.sns_analyzer --limit 20`.
- `pyproject.toml` — extend `[project.scripts]` with `analyze-my-threads = "thread_analysis.sns_analyzer:cli_main"` so `pip install -e .` registers the console script entry point.
- `tests/test_sns_analyzer.py` — at minimum:
  - `test_cli_help_exits_zero` — `cli_main(["--help"])` returns 0.
  - `test_cli_no_args_exits_zero` — `cli_main([])` returns 0 and prints "not yet implemented".
  - `test_post_and_summary_dataclasses_exist` — imports `Post` and `Summary` (from `sns_types`, OR re-exported from `sns_analyzer`) and asserts field names match the contract below.
- `tests/test_sns_types.py` — separate test file pinning the sns_types module:
  - `test_post_and_summary_field_contracts` — pin the dataclass fields, including `topic_counts` from step 1's M5 spec.

Do NOT touch:
- `src/thread_analysis/analyzer.py`
- `tests/test_analyzer.py`
- `pyproject.toml`'s runtime deps (the [project.scripts] addition is OK; deps are not)

Non-negotiable rules:
- TDD: tests first, watch them fail, then implement the minimum to pass.
- Idempotency: re-running the CLI multiple times is safe.
- No Threads API, no OAuth, no network calls in this step.
- `sns_types.py` MUST NOT import from any sibling sns_* module (it is a leaf; if you need field types, use stdlib only).

## Acceptance Criteria
```bash
# AC1: package still imports (existing + new)
python -c "import thread_analysis; from thread_analysis.sns_types import Post, Summary; from thread_analysis.sns_analyzer import cli_main; print('OK')" && echo OK

# AC2: sns_types contract test
pytest tests/test_sns_types.py -v

# AC3: new tests pass
pytest tests/test_sns_analyzer.py -v

# AC4: full suite still green (no regression on existing analyzer)
pytest tests/ -v

# AC5: CLI --help exits 0
python -c "from thread_analysis.sns_analyzer import cli_main; assert cli_main(['--help']) == 0" && echo OK

# AC6: SKILL.md exists and has the required frontmatter
test -f .claude/skills/analyze-my-threads/SKILL.md && head -3 .claude/skills/analyze-my-threads/SKILL.md | grep -q "^name: analyze-my-threads" && echo OK

# AC7: pyproject.toml registers the console script
grep -q "analyze-my-threads.*sns_analyzer" pyproject.toml && echo OK
```

## Verification & Status Update (REQUIRED before claiming done)
1. Run the AC commands above. Quote each exit code.
2. Update `phases/0-mvp/index.json` for THIS step (one of three outcomes):
   - **Success** → `"status": "completed"`, `"summary": "<one-line: files created/modified + key decisions>"`
   - **Unrecoverable failure** (3 retries exhausted) → `"status": "error"`, `"error_message": "<concrete error: which AC failed, with exit code + last 3 lines>"`
   - **External dependency** (API key, manual config, human approval) → `"status": "blocked"`, `"blocked_reason": "<what's needed>"`, then STOP — do not continue to the next step.
3. **Status reporting contract — v0 (in-repo, what THIS PR enforces):** the
   installed runner reads the step's status from the `phases/0-mvp/index.json` file written in step 2 above; it does not currently parse HTML-comment markers. See PRD §4.1 for the full forward-compatibility note. Sub-agents SHOULD still emit the `<!-- status: ... -->` and `<!-- summary: ... -->` markers as the last two lines of their reply.

## Don't
- Do NOT modify `src/thread_analysis/analyzer.py` — it analyzes thread *structures* (replies/participants), a different domain. Reason: scope leak.
- Do NOT add Threads API / OAuth / network deps in this step. Reason: dependency-first ordering; step 1 owns that surface.
- Do NOT add storage, scheduling, or Instagram support. Reason: non-goals NG3/NG4/NG1.
- Do NOT skip TDD — write tests first, watch them fail, then make them pass. tdd-guard will block otherwise.
- Do NOT place `Post` / `Summary` in `sns_analyzer.py` after this step. Reason: would re-introduce the import cycle with step 2's `sns_summarizer.py` and step 3's `cli_main` wiring.
