# Step 3: Wire API + summary into `analyze-my-threads` CLI command with formatted output

## Status
**pending** — last update: 2026-07-15T00:00:00Z

## Read first
- `/PRD.md`
- `/CLAUDE.md`
- `/pyproject.toml`
- `/src/thread_analysis/sns_types.py` (Post + Summary leaf module from step 0)
- `/src/thread_analysis/sns_client.py` (ThreadsClient + ThreadsAuth from step 1)
- `/src/thread_analysis/sns_summarizer.py` (summarize from step 2)
- `/tests/test_sns_analyzer.py` (existing CLI test pattern from step 0)
- `phases/0-mvp/step0.md`
- `phases/0-mvp/step1.md`
- `phases/0-mvp/step2.md`

## Task
Wire the API client (step 1) and the summary generator (step 2) into `cli_main` from step 0. The CLI command:
- Default behavior: read token from `~/.config/thread-analysis/sns-token.json`; if absent, run the OAuth bootstrap (print `authorization_url`, prompt the user, exchange code, write token, then re-enter the flow). Bootstrap is interactive — in tests, inject a pre-built token.
- Flags:
  - `--limit N` (default 20)
  - `--no-auth-bootstrap` — fail with a clear error if no token exists at the resolved `--token-path`.
  - `--token-path PATH` — override the token persistence location (env `THREAD_ANALYSIS_TOKEN_PATH` also accepted).
  - `--output {text, json}` (default `text`)
  - `--help` — show usage, exit 0.
- Output (`text`):
  - Section 1: `Top topics` — one per line, formatted as `<topic> (<count>)`, drawn from `Summary.topic_counts`.
  - Section 2: `Posting cadence` (avg gap in hours, `~Xh`)
  - Section 3: `Tone tags` (comma-separated)
  - Section 4: `Top engagement` (N posts, text excerpt ≤ 80 chars + counts)
  - Section 5: `Total posts analyzed: N`
- Output (`json`): raw `Summary`, JSON-serialized.
- Exit codes: 0 on success, 1 on auth error, 2 on API error, 64 on usage error (invalid flag; `--help` exits 0).
  - **argparse translate**: `argparse.parse_args` raises `SystemExit(0)` for `--help` and `SystemExit(2)` for usage errors; `cli_main` MUST wrap and translate: `e.code == 0` → return 0; `e.code == 2` → print usage to stderr, return 64.

File paths to create / modify:
- `src/thread_analysis/sns_analyzer.py` — extend `cli_main`. Imports from `sns_types`, `sns_client`, `sns_summarizer` (NOT `sns_analyzer` from any of those — that's the M11 leaf split).
  - **M11 note**: `sns_analyzer` owns `cli_main` AND re-exports `Post`/`Summary` from `sns_types`. Do NOT define `Post`/`Summary` here; they're in `sns_types`.
  - **M7 note**: `cli_main` constructs `ThreadsClient` with `overall_deadline=60.0` (no override). Tests pass `None` explicitly to disable.
  - **Inject seams** with these exact signatures (m-12: only the ones step 4 actually exercises):
    ```python
    def cli_main(
        argv: list[str] | None = None,
        *,
        token_loader: Callable[[Path | None], ThreadsToken | None] | None = None,
        posts_loader: Callable[[int], list[Post]] | None = None,
    ) -> int
    ```
    **m-12 decision**: drop `client_factory` and `token_persister`. Rationale: step 4's offline AC3b uses `posts_loader` (which bypasses `ThreadsClient` entirely); step 3's AC6 uses `token_loader`. `client_factory` is unreachable from any AC; `token_persister` is for the OAuth bootstrap flow that no step covers. Removing them keeps the seam surface minimal-and-testable.
- `src/thread_analysis/sns_output.py` (new) — `format_text(summary: Summary) -> str`, `format_json(summary: Summary) -> str`. Pure functions.
- `tests/test_sns_output.py` (new) — unit tests for both formatters; Section 1 renders `(count)` from `topic_counts`.
- `tests/test_sns_analyzer.py` (extend) — add `test_cli_with_injected_token`, `test_cli_help_exits_zero_via_translate`, `test_cli_invalid_flag_exits_64`, `test_cli_no_auth_bootstrap_returns_1`.

Non-negotiable rules:
- TDD: tests first.
- Idempotency: re-running produces the same output (no timestamps, no random IDs).
- Backward compat: `cli_main(["--help"])` from step 0 still exits 0.
- `--no-auth-bootstrap` exits with code 1 when no token file exists at the resolved `--token-path`.
- `cli_main` defines 4 injectable seams (`token_loader`, `token_persister`, `client_factory`, `posts_loader`) — **only `token_loader` and `posts_loader` ship in v0** (m-12). `client_factory` and `token_persister` are not exposed (they would clutter the surface without AC coverage; if needed later, add in a follow-up).

## Acceptance Criteria
```bash
# AC1: imports
python -c "from thread_analysis.sns_analyzer import cli_main; from thread_analysis.sns_output import format_text, format_json; from thread_analysis.sns_types import Post, Summary; print('OK')"

# AC2: formatter unit tests pass
pytest tests/test_sns_output.py -v

# AC3: extended CLI tests pass
pytest tests/test_sns_analyzer.py -v

# AC4: full suite green
pytest tests/ -v

# AC5: --help still exits 0 (argparse default, translated through SystemExit catch)
python -m thread_analysis.sns_analyzer --help >/dev/null
rc=$?
[ "$rc" -eq 0 ] && echo "OK" || { echo "FAIL: rc=$rc"; exit 1; }

# AC6: --no-auth-bootstrap with NON-EXISTENT --token-path exits 1 (machine-state-independent)
tmp=$(mktemp -d)
python -m thread_analysis.sns_analyzer --no-auth-bootstrap --token-path "$tmp/missing.json" --limit 1 2>&1 | head -3
rc=${PIPESTATUS[0]}
rm -rf "$tmp"
[ "$rc" -eq 1 ] && echo "OK (rc=1)" || { echo "FAIL: rc=$rc"; exit 1; }
```

## Verification & Status Update (REQUIRED before claiming done)
1. Run the AC commands above. Quote each exit code.
2. Update `phases/0-mvp/index.json`.
3. **Status reporting contract — v0:** see PRD §4.1.

## Don't
- Do NOT call the real Threads API in unit tests.
- Do NOT add storage (NG3), generation (NG4), scheduler (NG5), Instagram (NG1).
- Do NOT break the step-0 contract: `cli_main(["--help"])` MUST still exit 0.
- Do NOT lose `rc` from the python invocation in AC6.
- Do NOT tie AC6 to the developer's `~/.config/thread-analysis/sns-token.json` — use `mktemp -d` + `--token-path`.
- Do NOT let `argparse.parse_args` propagate `SystemExit` raw — must translate.
- Do NOT add back `client_factory` or `token_persister` in this step (m-12). They were removed; if AC coverage demands them later, add in a follow-up.
- Do NOT define `Post` / `Summary` in `sns_analyzer.py`. Reason: M11 import cycle.
