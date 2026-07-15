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
    - `__init__(token: ThreadsToken, *, http: HttpClient | None = None, request_timeout: float = 10.0, overall_deadline: float | None = None)` — accepts an injectable HTTP client for testing; propagates `request_timeout` and `overall_deadline` to the injected `http` instance so a stalled endpoint cannot bypass the <2-min runtime bound.
    - `list_own_posts(limit: int = 20) -> list[Post]` — paginated, returns most-recent-first. Honors the deadline: a hung HTTPS endpoint raises `ThreadsApiError("DEADLINE_EXCEEDED", elapsed=…, timeout=…)` whose message is sanitized (no URL, no token).
  - Token persistence: read/write to `~/.config/thread-analysis/sns-token.json` with `0600` perms. Path overridable via env `THREAD_ANALYSIS_TOKEN_PATH`. **No keyring, no DB** (non-goal NG3).
    - **Atomic write + symlink refusal contract**: `persist_token` opens `path.tmp` (sibling, `0600`) with `O_WRONLY | O_CREAT | O_EXCL | O_NOFOLLOW`, writes the JSON, fsyncs the file descriptor, closes it, then `os.replace(path.tmp, path)`. Guarantees:
      1. A pre-existing symlink at `path` cannot capture the access token (O_NOFOLLOW raises OSError → `TokenPathNotSafeError`).
      2. The rename is atomic on POSIX; concurrent readers see either old or new, never a partial write.
      3. The persisted file is `0600` (perms on the .tmp file; rename carries them over).
    - **Read-side defense**: `load_token` opens with `O_RDONLY | O_NOFOLLOW` (refuses to follow a symlink), validates `os.fstat(fd).st_mode & 0o777 == 0o600` on the **opened descriptor** (not via path-string stat — a TOCTOU attacker can swap the file between stat and open), reads, JSON-decodes, returns a `ThreadsToken`. Raises `FileNotFoundError` if missing; raises `TokenPathNotSafeError` on symlink or wrong mode.
    - Public API:
      - `persist_token(token: ThreadsToken, *, path: Path | None = None) -> Path` — atomic write per contract above. `path=None` falls back to env override, then the default.
      - `load_token(*, path: Path | None = None) -> ThreadsToken` — read per contract above. `path=None` falls back to env override, then the default.
  - All HTTP via a small `HttpClient` protocol so tests can inject `FakeHttpClient`. Use `urllib.request` from stdlib (no extra deps unless justified).
    - **Timeout contract**: every `HttpClient.get(url)` MUST set a per-request socket timeout AND honor a module-level monotonic deadline. Constructor signature:
      ```python
      class HttpClient(Protocol):
          def __init__(self, *, request_timeout: float = 10.0, overall_deadline: float | None = None) -> None: ...
          def get(self, url: str, *, params: dict | None = None, headers: dict | None = None) -> HttpResponse: ...
      ```
      `overall_deadline` is a monotonic timestamp. On breach, `get` raises `ThreadsApiError("DEADLINE_EXCEEDED", elapsed=…, timeout=…)` — the message MUST NOT include the URL (URLs can carry `access_token` query params). Default `request_timeout=10.0`, `overall_deadline=None` (no deadline).
- `tests/test_sns_auth.py` — unit tests for `ThreadsAuth` with a `FakeHttpClient`:
  - `test_authorization_url_returns_state`
  - `test_exchange_code_state_match`
  - `test_exchange_code_state_mismatch_raises` — `expected_state != stored_state` → raises `ValueError` BEFORE any HTTP call.
  - `test_exchange_code_state_match_uses_constant_time` — patched `hmac.compare_digest` is invoked (not `==`).
  - `test_refresh_if_needed_within_7_days` and `test_refresh_if_needed_outside_7_days`.
- `tests/test_sns_client.py` — unit tests for `ThreadsClient.list_own_posts`:
  - `test_list_own_posts_returns_fixture`
  - `test_list_own_posts_under_deadline`
  - `test_list_own_posts_deadline_exceeded` — fake http that sleeps past the deadline; expect `ThreadsApiError("DEADLINE_EXCEEDED", ...)` whose message does NOT contain the URL or any token.
- `tests/test_sns_token_io.py` — unit tests for `persist_token` and `load_token`:
  - `test_persist_creates_0600`
  - `test_persist_atomic_replace`
  - `test_persist_refuses_symlink_target`
  - `test_load_round_trips`
  - `test_load_refuses_wider_umask`
  - `test_load_refuses_symlink`

Non-negotiable rules:
- TDD: tests first. Mock all HTTP. Do not call real Threads API in unit tests.
- Token file MUST be created with `0600` perms on POSIX. Assert in a test.
- `load_token` MUST refuse to read a wider-umask OR symlinked file. Assert in tests.
- OAuth state MUST be generated via `secrets.token_urlsafe(32)`.
- OAuth state verification MUST use `hmac.compare_digest` (constant-time).
- HTTP client MUST honor `request_timeout` and `overall_deadline`. A hung endpoint converts to a sanitized `ThreadsApiError` within the deadline.
- Do NOT add keyring, DB, or encryption (non-goal NG3 — out of scope for v0).
- Do NOT add Instagram or any other platform (non-goal NG1).
- Backward compat: do not change the `Post` dataclass from step 0.
- Secrets: the test suite must never embed a real access token. Use clearly-fake strings like `"FAKE_TOKEN_..."`.

## Acceptance Criteria
```bash
# AC1: imports
python -c "from thread_analysis.sns_client import ThreadsAuth, ThreadsClient, ThreadsToken, persist_token, load_token; from thread_analysis.sns_client import ThreadsApiError, TokenPathNotSafeError; print('OK')"

# AC2: auth unit tests pass
pytest tests/test_sns_auth.py -v

# AC3: client unit tests pass
pytest tests/test_sns_client.py -v

# AC4: token I/O unit tests pass (atomic + symlink refusal)
pytest tests/test_sns_token_io.py -v

# AC5: full suite green
pytest tests/ -v

# AC6: token persist helper writes a fake token with mode 0600 (atomic, no symlink target)
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
- Do NOT skip the 0600 perm / atomic / symlink tests. Reason: token-handling regressions silently expose a credential.
- Do NOT use string-equality (`==`) for OAuth state comparison. Reason: timing oracle → CSRF.
- Do NOT generate OAuth state via non-cryptographic randomness. Reason: predictable → CSRF.
- Do NOT emit the URL (or anything containing an `access_token` query param) inside the deadline-exceeded error message. Reason: a stalled endpoint leaks the token via stderr / log lines.
