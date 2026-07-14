# Step 3: Wire API + summary into `analyze-my-threads` CLI command with formatted output

## Status
**pending** — last update: 2026-07-15T00:00:00Z

## Read first
- `/PRD.md`
- `/CLAUDE.md`
- `/pyproject.toml`
- `/src/thread_analysis/sns_analyzer.py` (cli_main from step 0)
- `/src/thread_analysis/sns_client.py` (ThreadsClient + ThreadsAuth from step 1)
- `/src/thread_analysis/sns_summarizer.py` (summarize from step 2)
- `/tests/test_sns_analyzer.py` (existing CLI test pattern)
- `phases/0-mvp/step0.md`
- `phases/0-mvp/step1.md`
- `phases/0-mvp/step2.md`

## Task
Wire the API client (step 1) and the summary generator (step 2) into `cli_main` from step 0. The CLI command:
- Default behavior: read token from `~/.config/thread-analysis/sns-token.json`; if absent, run the OAuth bootstrap (print `authorization_url`, prompt the user, exchange code, write token, then re-enter the flow). Bootstrap is interactive — in tests, inject a pre-built token.
- Flags:
  - `--limit N` (default 20) — how many recent posts to summarize.
  - `--no-auth-bootstrap` — fail with a clear error if no token exists. Useful for CI / scripted runs.
  - `--output {text, json}` (default `text`) — output format.
  - `--help` — show usage, exit 0.
- Output (`text`):
  - Section 1: `Top topics` (one per line, with count)
  - Section 2: `Posting cadence` (avg gap in hours, formatted as `~Xh`)
  - Section 3: `Tone tags` (comma-separated)
  - Section 4: `Top engagement` (N posts, each with text excerpt ≤ 80 chars + like/reply/repost counts)
  - Section 5: `Total posts analyzed: N`
- Output (`json`): the raw `Summary` object, JSON-serialized.
- Exit codes: 0 on success, 1 on auth error, 2 on API error, 64 on usage error (`--help`-style).

File paths to create / modify:
- `src/thread_analysis/sns_analyzer.py` — extend `cli_main` to:
  - parse argv (use `argparse`)
  - load or bootstrap token via `ThreadsAuth`
  - construct `ThreadsClient`, call `list_own_posts(limit=args.limit)`
  - call `summarize(posts)`
  - render output per `--output` choice
  - return the right exit code
- `src/thread_analysis/sns_output.py` (new) — `format_text(summary: Summary) -> str`, `format_json(summary: Summary) -> str`. Pure functions. Unit-testable.
- `tests/test_sns_output.py` (new) — unit tests for both formatters.
- `tests/test_sns_analyzer.py` (extend) — add `test_cli_with_injected_token` that constructs a fake `ThreadsClient` returning a fixture post list, asserts `cli_main([])` returns 0, asserts the output contains all five section headers.
- Inject seams: `cli_main` should accept an optional `client_factory` and `token_loader` callable so tests can avoid real I/O. Document this in the docstring.

Non-negotiable rules:
- TDD: tests first. Cover the formatters + the wired CLI with injected fakes.
- Idempotency: re-running produces the same output (no timestamps, no random IDs in the formatter output).
- Do NOT add a JSONL log, DB, or scheduled runs (non-goal NG3/NG4).
- Do NOT add Instagram support (non-goal NG1).
- Backward compat: `cli_main(["--help"])` from step 0 must still exit 0 (regression test required).

## Acceptance Criteria
```bash
# AC1: imports
python -c "from thread_analysis.sns_analyzer import cli_main; from thread_analysis.sns_output import format_text, format_json; print('OK')"

# AC2: formatter unit tests pass
pytest tests/test_sns_output.py -v

# AC3: extended CLI tests pass (including --help regression from step 0)
pytest tests/test_sns_analyzer.py -v

# AC4: full suite green
pytest tests/ -v

# AC5: --help still exits 0
python -m thread_analysis.sns_analyzer --help >/dev/null; echo "exit=$?"

# AC6: --no-auth-bootstrap with no token exits non-zero (sanity)
python -m thread_analysis.sns_analyzer --no-auth-bootstrap --limit 1 2>&1 | head -3; echo "(expected non-zero + auth error)"
```

## Verification & Status Update (REQUIRED before claiming done)
1. Run the AC commands above. Quote each exit code.
2. Update `phases/0-mvp/index.json` for THIS step (one of three outcomes):
   - **Success** → `"status": "completed"`, `"summary": "<one-line: files created/modified + key decisions>"`
   - **Unrecoverable failure** (3 retries exhausted) → `"status": "error"`, `"error_message": "<concrete error: which AC failed, with exit code + last 3 lines>"`
   - **External dependency** (API key, manual config, human approval) → `"status": "blocked"`, `"blocked_reason": "<what's needed>"`, then STOP — do not continue to the next step.
3. Emit EXACTLY these two HTML-comment markers as the **last two lines** of the final reply. The build runner parses them with the regex in `lib/execute.py:parse_status_marker()`:

```
<!-- status: completed | error | blocked -->
<!-- summary: <one-line outcome> | error_message: <concrete error> | blocked_reason: <what's needed> -->
```

   The marker value MUST match the `status` field written to `index.json` in step 2. If the marker is missing or malformed, the runner falls back to the index.json status (so the contract is best-effort, not blocking).

## Don't
- Do NOT call the real Threads API in unit tests. Reason: determinism + cost.
- Do NOT add storage (JSONL, sqlite, keyring). Reason: non-goal NG3.
- Do NOT add scheduled / cron runs. Reason: non-goal NG4.
- Do NOT add reply / post generation. Reason: non-goal NG5.
- Do NOT add Instagram or any other platform. Reason: non-goal NG1.
- Do NOT break the step-0 contract: `cli_main(["--help"])` MUST still exit 0. Reason: backward compat within the phase.
- Do NOT print timestamps or random IDs in the formatter output. Reason: idempotency + deterministic tests.
