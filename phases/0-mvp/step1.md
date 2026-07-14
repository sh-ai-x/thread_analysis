# Step 1: Threads API client with OAuth + list-own-posts

## Status
**pending** — last update: 2026-07-15T00:00:00Z

## Read first
- `/PRD.md`
- `/CLAUDE.md` (project SSOT — tdd-guard ON in Build stage)
- `/pyproject.toml`
- `/src/thread_analysis/sns_analyzer.py` (Post dataclass from step 0 — extend, don't rename)
- `/tests/test_sns_analyzer.py` (test pattern from step 0)
- `phases/0-mvp/step0.md` (prior step)
- Meta Threads API docs: `https://developers.facebook.com/docs/threads` (use WebFetch in research phase if API surface is unclear)

## Task
Implement the data plane: a Threads API client that authenticates the user via OAuth 2.0, persists the access token locally, and returns the user's own last N posts as `list[Post]` (the dataclass from step 0).

File paths to create:
- `src/thread_analysis/sns_client.py` — module containing:
  - `class ThreadsAuth` — OAuth 2.0 helper. Methods:
    - `authorization_url(state: str, scopes: list[str]) -> str` — returns the URL the user opens in a browser.
    - `exchange_code(code: str) -> ThreadsToken` — exchanges the redirect code for an access token.
    - `refresh_if_needed(token: ThreadsToken) -> ThreadsToken` — refreshes a token if it's within 7 days of expiry.
  - `class ThreadsToken` — frozen dataclass: `access_token: str`, `expires_at: datetime`, `user_id: str`.
  - `class ThreadsClient` — high-level API. Methods:
    - `__init__(token: ThreadsToken, *, http: HttpClient | None = None)` — accepts an injectable HTTP client for testing.
    - `list_own_posts(limit: int = 20) -> list[Post]` — paginated, returns most-recent-first.
  - Token persistence: read/write to `~/.config/thread-analysis/sns-token.json` with `0600` perms. Path overridable via env `THREAD_ANALYSIS_TOKEN_PATH`. **No keyring, no DB** (non-goal NG3).
  - All HTTP via a small `HttpClient` protocol so tests can inject `FakeHttpClient`. Use `urllib.request` from stdlib (no extra deps unless justified).
- `tests/test_sns_auth.py` — unit tests for `ThreadsAuth` with a `FakeHttpClient` (mock token exchange, refresh).
- `tests/test_sns_client.py` — unit tests for `ThreadsClient.list_own_posts` with a fixture Threads API response (JSON captured from a real or mocked request).

Non-negotiable rules:
- TDD: tests first. Mock all HTTP. Do not call real Threads API in unit tests.
- Token file MUST be created with `0600` perms on POSIX. Assert in a test.
- Do NOT add keyring, DB, or encryption (non-goal NG3 — out of scope for v0).
- Do NOT add Instagram or any other platform (non-goal NG1).
- Backward compat: do not change the `Post` dataclass from step 0.
- Secrets: the test suite must never embed a real access token. Use clearly-fake strings like `"FAKE_TOKEN_..."`.

## Acceptance Criteria
```bash
# AC1: imports
python -c "from thread_analysis.sns_client import ThreadsAuth, ThreadsClient, ThreadsToken; print('OK')"

# AC2: auth unit tests pass
pytest tests/test_sns_auth.py -v

# AC3: client unit tests pass
pytest tests/test_sns_client.py -v

# AC4: full suite green (no regression)
pytest tests/ -v

# AC5: token file perms — sanity check the helper writes 0600
python -c "
import os, tempfile
from thread_analysis.sns_client import ThreadsToken
from datetime import datetime, timedelta, timezone
p = tempfile.mkstemp(prefix='sns-tok-')[1]
os.chmod(p, 0o600)
# helper should NOT loosen this perm
import stat
mode = stat.S_IMODE(os.stat(p).st_mode)
assert mode == 0o600, f'expected 0600, got {oct(mode)}'
print('OK')
"
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
- Do NOT call the real Threads API in unit tests. Reason: determinism, cost, and test isolation.
- Do NOT embed a real access token in tests. Reason: secret-scan hook will fail CI.
- Do NOT add keyring, sqlite, or any storage beyond the JSON token file. Reason: non-goal NG3.
- Do NOT add Instagram or any non-Threads platform. Reason: non-goal NG1.
- Do NOT change the `Post` dataclass from step 0. Reason: backward compat within the phase.
- Do NOT skip the 0600 perm test. Reason: token file is the only secret in v0; sloppy perms = compromise.
