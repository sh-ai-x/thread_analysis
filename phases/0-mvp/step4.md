# Step 4: End-to-end AC verification — time-to-summary <2 min, output matches spec

## Status
**pending** — last update: 2026-07-15T00:00:00Z

## Read first
- `/PRD.md`
- `/CLAUDE.md`
- `/pyproject.toml`
- `/src/thread_analysis/sns_analyzer.py` (cli_main with seam signatures from step 3, including `posts_loader`)
- `/src/thread_analysis/sns_client.py` (ThreadsClient + ThreadsAuth from step 1)
- `/src/thread_analysis/sns_summarizer.py` (summarize from step 2)
- `/src/thread_analysis/sns_output.py` (format_text, format_json from step 3)
- `tests/test_sns_analyzer.py`, `tests/test_sns_client.py`, `tests/test_sns_summarizer.py`, `tests/test_sns_output.py`
- `phases/0-mvp/step0.md` … `step3.md`

## Task
Verify the full pipeline against the PRD's AC. Two-track verification:

Track A — **deterministic** (runs in CI without a real Threads account):
- Build a fixture of 20 representative `Post` records (mix of topics, lengths, engagement values, timestamps). Save as `tests/fixtures/sns_20_posts.json`. The JSON schema matches the `Post` dataclass field-for-field: `id`, `text`, `created_at` (ISO-8601 string), `like_count`, `reply_count`, `repost_count`.
- Add `tests/test_sns_e2e.py` that:
  1. Loads the fixture.
  2. **Parses each fixture record into a `Post` instance**: `[Post(**{**r, "created_at": datetime.fromisoformat(r["created_at"])}) for r in raw]`. `list_own_posts` MUST return `list[Post]`, not raw dicts — `summarize(posts)` accesses `post.text` / `post.created_at` attributes (not dict keys), so returning dicts raises `AttributeError` before any assertion runs.
  3. Constructs a fake `posts_loader` that returns the `list[Post]` for any limit. Injects via the new step-3 seam; no token, no HTTP client.
  4. Calls `cli_main(['--limit', '20', '--no-auth-bootstrap', '--token-path', '<tmp>/missing.json'], posts_loader=…)` and asserts `rc == 0`. The injection is end-to-end offline.
  5. Asserts all 5 section headers present in the captured output; asserts `Total posts analyzed: 20`.
  6. Asserts `format_text(summary)` round-trips a known golden file `tests/fixtures/sns_expected_text.txt`. Update the golden if the format changed during step 3; commit both.
- Wall-clock measurement: time `cli_main(['--limit','20','--no-auth-bootstrap','--token-path','<tmp>/missing.json'], posts_loader=…)` end-to-end with the injected fixture, assert wall-clock < 5 seconds. **Time the wired CLI, NOT just `summarize(posts)` in isolation** — a regression in cli orchestration / formatting / IO would be invisible otherwise.

Track B — **manual / live** (NOT in CI):
- Document in `docs/SNS_RUNBOOK.md` (new file):
  - How to bootstrap OAuth (one-time browser flow).
  - The exact command: `python -m thread_analysis.sns_analyzer --limit 20`.
  - How to capture wall-clock time (`time python -m thread_analysis.sns_analyzer --limit 20`).
  - Pass criterion: <2 minutes total.
  - Failure response: re-run; on still >2 min, append a **redacted error-class log entry** to `docs/SNS_RUNBOOK.md` "incidents" section — do NOT paste raw stderr. The entry schema is:
    ```yaml
    - at: <ISO-8601 timestamp>
      command: python -m thread_analysis.sns_analyzer --limit 20
      wall_clock_seconds: <number>
      error_class: <one of NETWORK_TIMEOUT | AUTH_EXPIRED | RATE_LIMIT | PARSE_ERROR | UNKNOWN>
      stack_top_frame: <module:function:line from traceback (redact oauth tokens via re.search sub)>
    ```
    A `scripts/log_incident.py` helper is provided to append a redacted entry; the script must redact any token-shaped string (`/[A-Za-z0-9_-]{20,}/`) before writing.

File paths to create:
- `tests/fixtures/sns_20_posts.json` — 20 representative Post records (one per line of the JSON, schema matches the dataclass).
- `tests/fixtures/sns_expected_text.txt` — golden output for the format test.
- `tests/test_sns_e2e.py` — Track A test (uses `posts_loader` to drive `cli_main` end-to-end offline).
- `docs/SNS_RUNBOOK.md` — Track B manual runbook.
- `scripts/log_incident.py` — helper that appends a redacted incident entry to `docs/SNS_RUNBOOK.md`.
- Update `README.md` with a "SNS Analyzer" section: 1-paragraph what-it-does, the command, link to `docs/SNS_RUNBOOK.md`.

Non-negotiable rules:
- TDD: Track A test first. Update golden only if the format change is intentional and documented.
- Do NOT call the real Threads API in tests. Reason: determinism.
- Do NOT record a real access token in `docs/SNS_RUNBOOK.md`, fixtures, or any incident log. Reason: secret-scan.
- Do NOT change `cli_main` or `summarize` signatures in this step — this is verification, not refactor.
- Do NOT add Instagram or any other platform (non-goal NG1).
- Track A MUST run fully offline (no token file, no network). AC3a + AC3b enforce this via `--no-auth-bootstrap` + `--token-path <tmp>/missing.json` + injected `posts_loader`.

## Acceptance Criteria
```bash
# AC1: e2e test passes (uses posts_loader seam; offline)
pytest tests/test_sns_e2e.py -v

# AC2: full suite green
pytest tests/ -v

# AC3a: --no-auth-bootstrap with no token + injected token_loader=None exits with rc=1 (auth error)
# (Machine-state-independent: uses mktemp -d for the token path, not ~/.config.)
tmp=$(mktemp -d)
python -c "
from datetime import datetime as _dt, timedelta as _td, timezone as _tz
from pathlib import Path
from thread_analysis.sns_analyzer import cli_main

rc = cli_main(
    ['--no-auth-bootstrap', '--token-path', '$tmp/missing.json', '--limit', '1'],
    token_loader=lambda path: None,
)
import sys
sys.exit(0 if rc == 1 else 1)
"
ac_rc=$?
rm -rf "$tmp"
[ "$ac_rc" -eq 0 ] && echo "OK (rc=1, expected auth error)" || { echo "FAIL: expected rc=1 on missing token, got ac_rc=$ac_rc"; exit 1; }

# AC3b: cli_main end-to-end wall-clock <5s, with injected posts_loader returning list[Post]
tmp=$(mktemp -d)
python -c "
import json, time
from datetime import datetime
from pathlib import Path
from thread_analysis.sns_analyzer import cli_main
from thread_analysis.sns_analyzer import Post

raw = json.loads(Path('tests/fixtures/sns_20_posts.json').read_text())
posts = [Post(**{**r, 'created_at': datetime.fromisoformat(r['created_at'])}) for r in raw]

t0 = time.perf_counter()
rc = cli_main(
    ['--limit', '20', '--no-auth-bootstrap', '--token-path', '$tmp/missing.json'],
    posts_loader=lambda limit: posts[:limit],
)
elapsed = time.perf_counter() - t0
import sys
sys.exit(0 if (rc == 0 and elapsed < 5.0) else 1)
"
ac_rc=$?
rm -rf "$tmp"
[ "$ac_rc" -eq 0 ] && echo "OK (elapsed check)" || { echo "FAIL: cli_main did not complete cleanly within 5s budget"; exit 1; }

# AC4: golden text file exists and is non-empty
test -s tests/fixtures/sns_expected_text.txt && echo "OK"

# AC5: runbook exists and contains the command
grep -q "python -m thread_analysis.sns_analyzer" docs/SNS_RUNBOOK.md && echo "OK"

# AC6: README has the SNS section
grep -q "SNS Analyzer" README.md && echo "OK"

# AC7: incident-log helper exists and redacts token-shaped strings
test -f scripts/log_incident.py && grep -q 're\.sub' scripts/log_incident.py && echo "OK"
```

## Verification & Status Update (REQUIRED before claiming done)
1. Run the AC commands above. Quote each exit code.
2. Update `phases/0-mvp/index.json` for THIS step (one of three outcomes):
   - **Success** → `"status": "completed"`, `"summary": "<one-line: files created/modified + key decisions>"`
   - **Unrecoverable failure** (3 retries exhausted) → `"status": "error"`, `"error_message": "<concrete error: which AC failed, with exit code + last 3 lines>"`
   - **External dependency** (API key, manual config, human approval) → `"status": "blocked"`, `"blocked_reason": "<what's needed>"`, then STOP — do not continue to the next step.
3. **Status reporting contract — v0 (in-repo, what THIS PR enforces):** the
   installed runner reads the step's status from the JSON file written in
   step 2 above; it does not currently parse HTML-comment markers. See
   `step0.md` for the full forward-compatibility note. Sub-agents SHOULD
   still emit the `<!-- status: ... -->` and `<!-- summary: ... -->`
   markers as the last two lines of their reply.

## Don't
- Do NOT call the real Threads API in tests or in fixtures. Reason: determinism + secret-scan.
- Do NOT embed a real access token anywhere (fixtures, runbook, README, incident log). Reason: secret-scan hook will fail CI.
- Do NOT change `cli_main` or `summarize` signatures in this step. Reason: this is verification, not refactor.
- Do NOT add storage, scheduling, or Instagram support. Reason: non-goals NG1/NG3/NG4.
- Do NOT skip the runbook. Reason: Track B is the only path that proves the PRD's <2-min target.
- Do NOT time `summarize(posts)` in isolation. Reason: cli orchestration / formatting / IO regressions would be invisible. The AC must time `cli_main` end-to-end with the injected fixture.
- Do NOT paste raw stderr into `docs/SNS_RUNBOOK.md`. Reason: stderr can carry a real access token; secret-scan will fail.
- Do NOT silently update the golden text file. If it changed, document the why in the step summary.
- Do NOT return raw dicts from `list_own_posts` in the fixture. Reason: `summarize` accesses `post.text` / `post.created_at` attributes (not dict keys); raw dicts raise `AttributeError` before any assertion runs. Build `Post(**...)` instances from the fixture.
- Do NOT depend on the developer's `~/.config/thread-analysis/sns-token.json` for AC3a. Reason: a real token on the dev's machine makes the test pass vacuously. Use `mktemp -d` for `--token-path`.
