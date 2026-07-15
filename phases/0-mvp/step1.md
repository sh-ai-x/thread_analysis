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
    - `authorization_url(scopes: list[str]) -> tuple[str, str]` — generates a CSRF `state` internally via `secrets.token_urlsafe(32)` and returns `(url, generated_state)`. The caller MUST persist `generated_state` for later verification in `exchange_code`. The `url` is what the user opens in a browser.
    - `exchange_code(code: str, *, expected_state: str, stored_state: str) -> ThreadsToken` — exchanges the redirect code for an access token. Verifies `expected_state` (the state echoed back in the redirect) matches `stored_state` (the state from the prior `authorization_url` call) via **`hmac.compare_digest`** (constant-time). Raises `ValueError("OAuth state mismatch; possible CSRF")` on mismatch. Does NOT proceed with the exchange if state verification fails.
    - `refresh_if_needed(token: ThreadsToken) -> ThreadsToken` — refreshes a token if it's within 7 days of expiry.
  - `class ThreadsToken` — frozen dataclass: `access_token: str`, `expires_at: datetime`, `user_id: str`.
  - `class ThreadsClient` — high-level API. Methods:
    - `__init__(token: ThreadsToken, *, http: HttpClient | None = None)` — accepts an injectable HTTP client for testing.
    - `list_own_posts(limit: int = 20) -> list[Post]` — paginated, returns most-recent-first.
  - Token persistence: read/write to `~/.config/thread-analysis/sns-token.json` with `0600` perms. Path overridable via env `THREAD_ANALYSIS_TOKEN_PATH`. **No keyring, no DB** (non-goal NG3).
    - Public API:
      - `persist_token(token: ThreadsToken, *, path: Path | None = None) -> Path` — writes the token JSON with `0600` perms and returns the path actually written. `path=None` falls back to env override, then the default `~/.config/thread-analysis/sns-token.json`.
      - `load_token(*, path: Path | None = None) -> ThreadsToken` — reads the persisted token JSON, asserts the file mode is `0o600` on POSIX (refuses to load a wider-umask file), returns a `ThreadsToken`. `path=None` falls back to env override, then the default. Raises `FileNotFoundError` if no token exists.
  - All HTTP via a small `HttpClient` protocol so tests can inject `FakeHttpClient`. Use `urllib.request` from stdlib (no extra deps unless justified).
- `tests/test_sns_auth.py` — unit tests for `ThreadsAuth` with a `FakeHttpClient`:
  - `test_authorization_url_returns_state` — `authorization_url([...])` returns a `(url, state)` tuple where `state` is non-empty, url-safe-base64-shaped, and the URL contains the same `state` query param.
  - `test_exchange_code_state_match` — happy path: state matches, returns a `ThreadsToken`.
  - `test_exchange_code_state_mismatch_raises` — `expected_state != stored_state` → raises `ValueError` BEFORE any HTTP call to the token endpoint.
  - `test_exchange_code_state_match_uses_constant_time` — patched `hmac.compare_digest` is invoked (not `==`).
  - `test_refresh_if_needed_within_7_days` — refresh issued; token in `ThreadsToken` returned.
  - `test_refresh_if_needed_outside_7_days` — no refresh; original returned.
- `tests/test_sns_client.py` — unit tests for `ThreadsClient.list_own_posts` with a fixture Threads API response (JSON captured from a real or mocked request).
- `tests/test_sns_token_io.py` — unit tests for `persist_token` and `load_token`:
  - `test_persist_creates_0600`
  - `test_load_round_trips`
  - `test_load_refuses_wider_umask` — set mode to `0o644`, call `load_token`, expect `PermissionError`.

Non-negotiable rules:
- TDD: tests first. Mock all HTTP. Do not call real Threads API in unit tests.
- Token file MUST be created with `0600` perms on POSIX. Assert in a test.
- `load_token` MUST refuse to read a token file whose POSIX mode is wider than `0o600`. Assert in a test.
- OAuth state MUST be generated via `secrets.token_urlsafe(32)` (256 bits entropy).
- OAuth state verification MUST use `hmac.compare_digest` (constant-time).
- Do NOT add keyring, DB, or encryption (non-goal NG3 — out of scope for v0).
- Do NOT add Instagram or any other platform (non-goal NG1).
- Backward compat: do not change the `Post` dataclass from step 0.
- Secrets: the test suite must never embed a real access token. Use clearly-fake strings like `"FAKE_TOKEN_..."`.
- Forbidden substring scans (`'token' in response`) are NOT a substitute for the constant-time state compare and 0600 perm check.

## Acceptance Criteria
```bash
# AC1: imports
python -c "from thread_analysis.sns_client import ThreadsAuth, ThreadsClient, ThreadsToken, persist_token, load_token; print('OK')"

# AC2: auth unit tests pass
pytest tests/test_sns_auth.py -v

# AC3: client unit tests pass
pytest tests/test_sns_client.py -v

# AC4: token I/O unit tests pass
pytest tests/test_sns_token_io.py -v

# AC5: full suite green (no regression)
pytest tests/ -v

# AC6: token persist helper writes a fake token with mode 0600
python -c "
import os, stat, tempfile
from pathlib import Path
from datetime import datetime, timedelta, timezone
from thread_analysis.sns_client import ThreadsToken, persist_token

with tempfile.TemporaryDirectory() as td:
    p = Path(td) / 'sns-token.json'
    tok = ThreadsToken(
        access_token='FAKE_TOKEN_' + 'x' * 8,
        expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
        user_id='0',
    )
    persist_token(tok, path=p)
    assert p.exists(), 'token file not created'
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
3. **Status reporting contract — v0 (in-repo, what THIS PR enforces):** the
   installed runner reads the step's status from the JSON file written in
   step 2 above; it does not currently parse HTML-comment markers. See
   `step0.md` for the full forward-compatibility note. Sub-agents SHOULD
   still emit the `<!-- status: ... -->` and `<!-- summary: ... -->`
   markers as the last two lines of their reply.

## Don't
- Do NOT call the real Threads API in unit tests. Reason: determinism, cost, and test isolation.
- Do NOT embed a real access token in tests. Reason: secret-scan hook will fail CI.
- Do NOT add keyring, sqlite, or any storage beyond the JSON token file. Reason: non-goal NG3.
- Do NOT add Instagram or any non-Threads platform. Reason: non-goal NG1.
- Do NOT change the `Post` dataclass from step 0. Reason: backward compat within the phase.
- Do NOT skip the 0600 perm test (AC6) or the load-refuses-wider-umask test. Reason: token-file perm regression would silently expose a credential.
- Do NOT use string-equality (`==`) for OAuth state comparison. Reason: timing oracle → CSRF.
- Do NOT generate OAuth state via non-cryptographic randomness (random.random, time.time, uuid4). Reason: predictable → CSRF.
