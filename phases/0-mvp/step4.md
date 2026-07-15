# Step 4: End-to-end AC verification — time-to-summary <2 min, output matches spec

## Status
**pending** — last update: 2026-07-15T00:00:00Z

## Read first
- `/PRD.md`
- `/CLAUDE.md`
- `/pyproject.toml`
- `/src/thread_analysis/sns_types.py` (Post / Summary from step 0)
- `/src/thread_analysis/sns_analyzer.py` (cli_main with `token_loader` + `posts_loader` seams from step 3)
- `/src/thread_analysis/sns_client.py` (ThreadsClient + ThreadsAuth from step 1)
- `/src/thread_analysis/sns_summarizer.py` (summarize from step 2)
- `/src/thread_analysis/sns_output.py` (format_text, format_json from step 3)
- `tests/test_sns_analyzer.py`, `tests/test_sns_client.py`, `tests/test_sns_summarizer.py`, `tests/test_sns_output.py`, `tests/test_sns_token_io.py`, `tests/test_sns_types.py`
- `phases/0-mvp/step0.md` … `step3.md`

## Task
Verify the full pipeline against the PRD's AC. Two-track verification:

Track A — **deterministic** (runs in CI without a real Threads account):
- Build a fixture of 20 representative `Post` records (mix of topics, lengths, engagement values, timestamps). Save as `tests/fixtures/sns_20_posts.json`. Schema matches `Post` field-for-field; `created_at` is ISO-8601 string.
- Add `tests/test_sns_e2e.py` that:
  1. Loads the fixture.
  2. Parses each record into a `Post` instance: `[Post(**{**r, "created_at": datetime.fromisoformat(r["created_at"])}) for r in raw]`. **`list_own_posts` MUST return `list[Post]`, not dicts — `summarize(posts)` accesses `post.text` / `post.created_at` attributes.**
  3. Injects `posts_loader=lambda limit: posts[:limit]` and `token_loader=lambda path: None`.
  4. Calls `cli_main(['--limit', '20', '--no-auth-bootstrap', '--token-path', '<tmp>/missing.json'], posts_loader=…, token_loader=…)` and asserts `rc == 0`.
  5. Asserts all 5 section headers + `Total posts analyzed: 20`.
  6. Asserts `format_text(summary)` round-trips `tests/fixtures/sns_expected_text.txt`.
- Wall-clock: `cli_main(['--limit', '20', '--no-auth-bootstrap', '--token-path', '<tmp>/missing.json'], posts_loader=…, token_loader=lambda p: None)` end-to-end < 5s.

Track B — **manual / live** (NOT in CI):
- `docs/SNS_RUNBOOK.md`: OAuth bootstrap, `python -m thread_analysis.sns_analyzer --limit 20`, `time …`, pass criterion <2 min.
- Failure response: **append a redacted YAML entry** to `docs/SNS_RUNBOOK.md` "incidents" section. **Do NOT paste raw stderr** — it carries the real access token.
  - Schema:
    ```yaml
    - at: <ISO-8601>
      command: python -m thread_analysis.sns_analyzer --limit 20
      wall_clock_seconds: <number>
      error_class: <NETWORK_TIMEOUT | AUTH_EXPIRED | RATE_LIMIT | PARSE_ERROR | UNKNOWN>
      stack_top_frame: <module:function:line, tokens redacted>
    ```
  - `scripts/log_incident.py` provides `append_incident(error_class: str, wall_clock: float, stderr: str) -> None`. It MUST `re.sub(r"[A-Za-z0-9_-]{10,}", "REDACTED_TOKEN", stderr)` before writing (M8 floor `{10,}` catches the short real Threads tokens, unlike the previous `{20,}`).

File paths to create:
- `tests/fixtures/sns_20_posts.json` — 20 Post records.
- `tests/fixtures/sns_expected_text.txt` — golden output.
- `tests/test_sns_e2e.py` — Track A test.
- `docs/SNS_RUNBOOK.md` — Track B runbook.
- `scripts/log_incident.py` — incident-log helper.
- `tests/test_log_incident.py` — **M5 redacted-round-trip test**: feed `scripts/log_incident.append_incident` a string containing a real-shape token (≥10 chars, e.g. `"THR_FAKE_TOKEN_0123456789AB"`), call the helper, read back the runbook section, assert the token is replaced with `REDACTED_TOKEN` AND that no token-shaped substring remains. This pins the M5 contract — the helper genuinely redacts rather than just naming `re.sub` in source.
- Update `README.md`.

Non-negotiable rules:
- TDD: Track A test first.
- Do NOT call the real Threads API in tests.
- Do NOT record a real access token in `docs/SNS_RUNBOOK.md`, fixtures, or the incident log.
- Do NOT change `cli_main` or `summarize` signatures in this step.
- Track A MUST run fully offline (`mktemp -d` + `--token-path <tmp>/missing.json` + `posts_loader`).
- Track B live <2-min enforcement in CI is un-actionable without a test Threads account (M6); Track A's <5s wall-clock covers the inside-CI bound. The runbook is the only sign-off on Track B; CI cannot gate on a live Threads round-trip.

## Acceptance Criteria
```bash
# AC1: e2e test passes (posts_loader seam, offline)
pytest tests/test_sns_e2e.py -v

# AC2: full suite green
pytest tests/ -v

# AC3a: --no-auth-bootstrap + no token + injected token_loader=None exits with rc=1
tmp=$(mktemp -d)
python -c "
from datetime import datetime as _dt, timedelta as _td, timezone as _tz
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
[ "$ac_rc" -eq 0 ] && echo "OK (rc=1)" || { echo "FAIL"; exit 1; }

# AC3b: cli_main wall-clock <5s with posts_loader seam (offline)
tmp=$(mktemp -d)
python -c "
import json, time
from datetime import datetime
from pathlib import Path
from thread_analysis.sns_analyzer import cli_main
from thread_analysis.sns_types import Post
raw = json.loads(Path('tests/fixtures/sns_20_posts.json').read_text())
posts = [Post(**{**r, 'created_at': datetime.fromisoformat(r['created_at'])}) for r in raw]
t0 = time.perf_counter()
rc = cli_main(
    ['--limit', '20', '--no-auth-bootstrap', '--token-path', '$tmp/missing.json'],
    posts_loader=lambda limit: posts[:limit],
    token_loader=lambda path: None,
)
elapsed = time.perf_counter() - t0
import sys
sys.exit(0 if (rc == 0 and elapsed < 5.0) else 1)
"
ac_rc=$?
rm -rf "$tmp"
[ "$ac_rc" -eq 0 ] && echo "OK (elapsed)" || { echo "FAIL"; exit 1; }

# AC4: golden text file exists and is non-empty
test -s tests/fixtures/sns_expected_text.txt && echo "OK"

# AC5: runbook exists and contains the command
grep -q "python -m thread_analysis.sns_analyzer" docs/SNS_RUNBOOK.md && echo "OK"

# AC6: README has the SNS section
grep -q "SNS Analyzer" README.md && echo "OK"

# AC7: round-trip redaction test (M5) + incident helper actually redacts the {10,} floor (M8)
test -f scripts/log_incident.py && grep -q '\{10,\}' scripts/log_incident.py && echo "regex_floor_OK"
pytest tests/test_log_incident.py -v

# AC8: CI content scan of runbook + fixtures for any token-shaped strings (M9, m2)
python -c "
import re, pathlib
roots = [pathlib.Path('docs/SNS_RUNBOOK.md'),
         pathlib.Path('tests/fixtures/sns_20_posts.json'),
         pathlib.Path('tests/fixtures/sns_expected_text.txt')]
# m2: length+shape filter — any 16+ char [A-Za-z0-9_-]+ run that is NOT a known
# false positive (pytest assertion string, hex commit sha, ISO-8601 timestamp)
# is a candidate. Outside tests/test_* the candidate MUST NOT appear.
pattern = re.compile(r'[A-Za-z0-9_-]{16,}')
SAFE_LINE_FRAGMENTS = (
    'pytest', 'assert ', 'commit', 'tree ', 'object', 'author ',
    'T19:', 'T20:', 'datetime', 'isoformat', 'sns_', 'subprocess',
    'thread_analysis', 'O_EXCL', 'O_NOFOLLOW', 'hmac', 'secrets',
)
hits = []
for r in roots:
    if not r.exists():
        continue
    for ln in r.read_text().splitlines():
        for m in pattern.finditer(ln):
            tok = m.group(0)
            if any(safe in ln for safe in SAFE_LINE_FRAGMENTS):
                continue
            hits.append((str(r), ln[:80], tok))
assert not hits, f'token-shaped string in a non-test artifact: {hits[:3]}...'
print('OK (m2 length+shape content scan: no live-token-shaped strings)')
"
```

## Verification & Status Update (REQUIRED before claiming done)
1. Run the AC commands above. Quote each exit code.
2. Update `phases/0-mvp/index.json`.
3. **Status reporting contract — v0:** see PRD §4.1.

## Don't
- Do NOT call the real Threads API in tests or fixtures.
- Do NOT embed a real access token anywhere.
- Do NOT change `cli_main` or `summarize` signatures.
- Do NOT add storage, scheduling, or Instagram support.
- Do NOT skip the runbook.
- Do NOT time `summarize(posts)` in isolation in AC3b.
- Do NOT paste raw stderr into the runbook.
- Do NOT silently update the golden text file.
- Do NOT return raw dicts from `list_own_posts` in the fixture.
- Do NOT depend on the developer's `~/.config/thread-analysis/sns-token.json` for AC3a.
- Do NOT name `re.sub` in the helper source and call that "coverage" — AC7 also requires the round-trip test in `tests/test_log_incident.py` to assert the redacted file is genuinely free of token-shaped strings.
- Do NOT use `{20,}` in the regex; the M8 contract uses `{10,}` because real Threads tokens can be shorter than 20 chars.
