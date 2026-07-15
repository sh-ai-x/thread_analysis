# Step 4: End-to-end AC verification — time-to-summary <2 min, output matches spec

## Status
**pending** — last update: 2026-07-15T00:00:00Z

## Read first
- `/PRD.md`
- `/CLAUDE.md`
- `/pyproject.toml`
- `/src/thread_analysis/sns_analyzer.py` (cli_main)
- `/src/thread_analysis/sns_client.py` (ThreadsClient + ThreadsAuth)
- `/src/thread_analysis/sns_summarizer.py` (summarize)
- `/src/thread_analysis/sns_output.py` (format_text, format_json)
- `tests/test_sns_analyzer.py`, `tests/test_sns_client.py`, `tests/test_sns_summarizer.py`, `tests/test_sns_output.py`
- `phases/0-mvp/step0.md` … `step3.md`

## Task
Verify the full pipeline against the PRD's AC. Two-track verification:

Track A — **deterministic** (runs in CI without a real Threads account):
- Build a fixture of 20 representative `Post` records (mix of topics, lengths, engagement values, timestamps). Save as `tests/fixtures/sns_20_posts.json`.
- Add `tests/test_sns_e2e.py` that:
  1. Loads the fixture.
  2. Constructs a `ThreadsClient` whose `list_own_posts` returns the fixture (inject via the `http` client seam from step 1, OR by monkeypatching `ThreadsClient.list_own_posts` in the test — pick the one your step 1 implementation supports).
  3. Runs `cli_main(['--limit', '20'])` via the test seam and asserts exit 0.
  4. Asserts all 5 section headers present in the captured output, asserts `Total posts analyzed: 20`.
  5. Asserts `format_text(summary)` round-trips a known golden file `tests/fixtures/sns_expected_text.txt`. Update the golden if format changed during step 3; commit both.
- Wall-clock measurement: time `cli_main(['--limit', '20'])` end-to-end with the injected fixture, assert wall-clock < 5 seconds (loose upper bound — the real <2 min target is a manual run with live API). **Time the wired CLI, NOT just `summarize(posts)` in isolation** — a regression in cli orchestration / formatting / IO would be invisible otherwise.

Track B — **manual / live** (NOT in CI):
- Document in `docs/SNS_RUNBOOK.md` (new file):
  - How to bootstrap OAuth (one-time browser flow).
  - The exact command: `python -m thread_analysis.sns_analyzer --limit 20`.
  - How to capture wall-clock time (`time python -m thread_analysis.sns_analyzer --limit 20`).
  - Pass criterion: <2 minutes total.
  - Failure response: re-run; if still >2 min, log to `docs/SNS_RUNBOOK.md` "incidents" section with timestamp + last 3 lines of stderr.

File paths to create:
- `tests/fixtures/sns_20_posts.json` — 20 representative Post records.
- `tests/fixtures/sns_expected_text.txt` — golden output for the format test.
- `tests/test_sns_e2e.py` — Track A test.
- `docs/SNS_RUNBOOK.md` — Track B manual runbook.
- Update `README.md` with a "SNS Analyzer" section: 1-paragraph what-it-does, the command, link to `docs/SNS_RUNBOOK.md`.

Non-negotiable rules:
- TDD: Track A test first. Update golden only if the format change is intentional and documented.
- Do NOT call the real Threads API in tests. Reason: determinism.
- Do NOT record a real access token in `docs/SNS_RUNBOOK.md` or fixtures. Reason: secret-scan.
- Do NOT change `cli_main` or `summarize` signatures in this step — this is verification, not refactor.
- Do NOT add Instagram or any other platform (non-goal NG1).

## Acceptance Criteria
```bash
# AC1: e2e test passes
pytest tests/test_sns_e2e.py -v

# AC2: full suite green
pytest tests/ -v

# AC3: end-to-end cli_main with injected 20-post fixture completes in <5s
python -c "
import json, time
from datetime import datetime
from pathlib import Path
from thread_analysis.sns_analyzer import cli_main
from thread_analysis import sns_client

raw = json.loads(Path('tests/fixtures/sns_20_posts.json').read_text())
posts = [{**p, 'created_at': datetime.fromisoformat(p['created_at'])} for p in raw]

# Inject via monkeypatch: replace list_own_posts on the live class.
def _fake_list(self, limit=20):
    return posts[:limit]
sns_client.ThreadsClient.list_own_posts = _fake_list

t0 = time.perf_counter()
rc = cli_main(['--limit', '20'])
elapsed = time.perf_counter() - t0
assert rc == 0, f'cli_main exit={rc}'
assert elapsed < 5.0, f'too slow: {elapsed:.3f}s'
print(f'OK elapsed={elapsed:.3f}s')
"

# AC4: golden text file exists and is non-empty
test -s tests/fixtures/sns_expected_text.txt && echo "OK"

# AC5: runbook exists and contains the command
grep -q "python -m thread_analysis.sns_analyzer" docs/SNS_RUNBOOK.md && echo "OK"

# AC6: README has the SNS section
grep -q "SNS Analyzer" README.md && echo "OK"
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
- Do NOT embed a real access token anywhere (fixtures, runbook, README). Reason: secret-scan hook will fail CI.
- Do NOT change `cli_main` or `summarize` signatures in this step. Reason: this is verification, not refactor.
- Do NOT add storage, scheduling, or Instagram support. Reason: non-goals NG1/NG3/NG4.
- Do NOT skip the runbook. Reason: Track B is the only path that proves the PRD's <2-min target.
- Do NOT time `summarize(posts)` in isolation in AC3. Reason: cli orchestration / formatting / IO regressions would be invisible. The AC must time `cli_main` end-to-end with the injected fixture.
- Do NOT silently update the golden text file. If it changed, document the why in the step summary.
