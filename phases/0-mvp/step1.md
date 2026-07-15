# Step 1: Threads API client with OAuth + list-own-posts

## Status
**pending** — last update: 2026-07-15T00:00:00Z

## Read first
- `/PRD.md`
- `/CLAUDE.md` (project SSOT — tdd-guard ON in Build stage)
- `/pyproject.toml`
- `/src/thread_analysis/sns_types.py` (Post / Summary leaf module from step 0 — `from sns_types import Post, Summary`)
- `/tests/test_sns_types.py` (sns_types contract test from step 0)
- `/tests/test_sns_analyzer.py` (existing CLI test pattern from step 0)
- `phases/0-mvp/step0.md` (prior step)
- Meta Threads API docs: `https://developers.facebook.com/docs/threads` (use WebFetch in research phase if API surface is unclear)

## Task
Implement the data plane: a Threads API client that authenticates the user via OAuth 2.0, persists the access token locally, and returns the user's own last N posts as `list[Post]` (the dataclass from `sns_types`).

File paths to create:
- `src/thread_analysis/sns_client.py` — module containing:
  - `class ThreadsAuth` — OAuth 2.0 helper. Methods:
    - `authorization_url(scopes: list[str]) -> tuple[str, str, str]` — generates a CSRF `state` (via `secrets.token_urlsafe(32)`) AND a PKCE `code_verifier` (via `secrets.token_urlsafe(64)`) internally, derives `code_challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier).digest()).rstrip(b"=").decode()` (S256 method per RFC 7636), and returns `(url, generated_state, code_verifier)`. The `url` carries the S256 `code_challenge` and `state` query params only; the verifier never leaves memory.
    - `exchange_code(code: str, *, expected_state: str, stored_state: str, code_verifier: str) -> ThreadsToken` — verifies state via `hmac.compare_digest` then exchanges the redirect code for an access token. **Per the M4 contract**, `exchange_code` calls the OAuth token endpoint via the injected `HttpClient.post(...)` method. The token POST body includes `code_verifier` so the OAuth server validates the S256 challenge. Raises `ValueError("OAuth state mismatch; possible CSRF")` on state mismatch; does NOT proceed with the exchange if state verification fails.
    - **State lifecycle (M2):** `generated_state` and `code_verifier` live in-memory for the lifetime of a single `cli_main` invocation. The bootstrap flow is single-process synchronous: `authorization_url` returns them, the caller stashes them on the closure, then `exchange_code` receives them. They are NEVER written to disk, never logged, never embedded in the URL (the URL only carries the S256 `code_challenge` + `state` query params).
    - `refresh_if_needed(token: ThreadsToken, *, code_verifier: str) -> ThreadsToken` — refreshes a token if it's within 7 days of expiry. Refresh uses the same PKCE flow: the caller passes a fresh `code_verifier`; the token endpoint validates the S256 challenge derived from it. Goes through `HttpClient.post(...)` against the refresh endpoint.
    - **OAuth flow decision (M1):** v0 uses the **public-client native-app flow with PKCE (RFC 7636)**. There is no `client_secret` to store; the public-client assumption + S256 challenge is the security primitive. No keychain/keystore integration; the public-client assumption is the spec's stance.
  - `class ThreadsToken` — frozen dataclass: `access_token: str`, `expires_at: datetime`, `user_id: str`. **Lives in `sns_types.py`** (re-export here: `from thread_analysis.sns_types import ThreadsToken`).
  - `class ThreadsClient` — high-level API. Methods:
    - `__init__(token: ThreadsToken, *, http: HttpClient | None = None, request_timeout: float = 10.0, overall_deadline: float = 60.0)` — accepts an injectable HTTP client for testing. **`overall_deadline` default is `60.0` (1 min), NOT `None`** — the spec requires the <2-min runtime bound to be enforced by default for any real ThreadsClient; passing `None` explicitly opts out for tests where a deadline is irrelevant. A hang past the deadline raises `ThreadsApiError("DEADLINE_EXCEEDED", ...)`.
    - `list_own_posts(limit: int = 20) -> list[Post]` — paginated, returns most-recent-first. Honors the deadline.
  - `class HttpClient(Protocol)` — small HTTP client Protocol:
    ```python
    class HttpClient(Protocol):
        def __init__(self, *, request_timeout: float = 10.0, overall_deadline: float = 60.0) -> None: ...
        def get(self, url: str, *, params: dict | None = None, headers: dict | None = None) -> HttpResponse: ...
        def post(self, url: str, *, body: dict | None = None, headers: dict | None = None) -> HttpResponse: ...
    ```
    `HttpResponse.status: int` + `HttpResponse.read() -> bytes`. **The `post()` method is mandatory** — `exchange_code` and `refresh_if_needed` both go through it.
    The real `HttpClient` implementation uses `urllib.request` from stdlib. **Error messages MUST NOT include the URL, the request body, OR the response body** (m1). URLs can carry `access_token` query params; bodies can carry the same plus other PII. The same scope applies to `post()`.
  - Token persistence: read/write to `~/.config/thread-analysis/sns-token.json` with `0600` perms. Path overridable via env `THREAD_ANALYSIS_TOKEN_PATH`. **No keyring, no DB** (non-goal NG3).
    - **Atomic write + symlink refusal contract**: `persist_token` opens `path.tmp` (sibling, `0600`) with `O_WRONLY | O_CREAT | O_EXCL | O_NOFOLLOW`, writes the JSON, fsyncs the file descriptor, closes it, then `os.replace(path.tmp, path)`. A pre-existing symlink at `path` cannot capture the token (O_NOFOLLOW → `TokenPathNotSafeError`).
    - **Read-side fstat, not path-stat**: `load_token` opens the file with `O_RDONLY | O_NOFOLLOW` (refuses to follow a symlink at the path), then validates `os.fstat(fd).st_mode & 0o777 == 0o600` on the **opened descriptor** (the `os.fstat(fd)` call is mandatory in the implementation — using `os.stat(path)` instead is a TOCTOU window). Reads, JSON-decodes, returns a `ThreadsToken`.
    - Public API:
      - `persist_token(token, *, path=None) -> Path`
      - `load_token(*, path=None) -> ThreadsToken`
- `tests/test_sns_auth.py` — unit tests for `ThreadsAuth` with a `FakeHttpClient`:
  - `test_authorization_url_returns_state`
  - `test_exchange_code_state_match` — happy path; uses `FakeHttpClient.post(...)`.
  - `test_exchange_code_state_mismatch_raises` — `expected_state != stored_state` → raises BEFORE the post.
  - `test_exchange_code_state_match_uses_constant_time`
  - `test_refresh_if_needed_within_7_days`, `test_refresh_if_needed_outside_7_days` — both go through `post()`.
  - `test_exchange_code_uses_post_method` — pass a `FakeHttpClient` whose `post` is replaced with a stub that raises; expect `TypeError("post() missing")`. Pins the M4 contract.
- `tests/test_sns_client.py`:
  - `test_list_own_posts_returns_fixture`
  - `test_list_own_posts_under_deadline`
  - `test_list_own_posts_deadline_exceeded` — fake http that sleeps past the deadline; `ThreadsApiError("DEADLINE_EXCEEDED", ...)` whose message does NOT contain URL or token.
  - `test_default_overall_deadline_is_60s` — instantiate `ThreadsClient(token)` with no explicit `overall_deadline`; inspect the propagated value via the `http` arg and assert it equals 60.0. Pins the M7 contract.
- `tests/test_sns_token_io.py`:
  - `test_persist_creates_0600`
  - `test_persist_atomic_replace`
  - `test_persist_refuses_symlink_target`
  - `test_load_round_trips`
  - `test_load_refuses_wider_umask`
  - `test_load_refuses_symlink`
  - `test_load_uses_fstat_not_path_stat` — patch `os.fstat` (must be called) AND `os.stat` (must NOT be called on the path string). Pins the M10 contract: `os.fstat(fd)` is the only path-attribute check the implementation may invoke.

Non-negotiable rules:
- TDD: tests first. Mock all HTTP. Do not call real Threads API in unit tests.
- Token file MUST be created with `0600` perms on POSIX.
- `load_token` MUST refuse to read a wider-umask OR symlinked file.
- OAuth state MUST be generated via `secrets.token_urlsafe(32)` and verified via `hmac.compare_digest`.
- HTTP client MUST honor `request_timeout` and `overall_deadline`. **A hung endpoint converts to a sanitized `ThreadsApiError` within the deadline.**
- `ThreadsClient.__init__` MUST default `overall_deadline=60.0`. Passing `overall_deadline=None` is allowed only in test code, never at the production CLI call site.
- `load_token` MUST use `os.fstat(fd)` on the **opened descriptor** for mode validation. Using `os.stat(path)` instead is the M10 TOCTOU regression; tests pin the diff.
- Do NOT add keyring, DB, or encryption (non-goal NG3).
- Do NOT add Instagram or any other platform (non-goal NG1).
- Backward compat: do not change the `Post` dataclass shape from step 0.

## Acceptance Criteria
```bash
# AC1: imports
python -c "from thread_analysis.sns_client import ThreadsAuth, ThreadsClient, ThreadsToken, persist_token, load_token; from thread_analysis.sns_client import ThreadsApiError, TokenPathNotSafeError; from thread_analysis.sns_types import Post, Summary; print('OK')"

# AC2: auth unit tests pass
pytest tests/test_sns_auth.py -v

# AC3: client unit tests pass
pytest tests/test_sns_client.py -v

# AC4: token I/O unit tests pass
pytest tests/test_sns_token_io.py -v

# AC5: full suite green
pytest tests/ -v

# AC6: token persist helper writes a fake token with mode 0600 (atomic, no symlink target)
# AND load_token refuses files whose fstat says mode != 0o600 (TOCTOU guard)
python -c "
import os, stat, tempfile
from pathlib import Path
from datetime import datetime, timedelta, timezone
from thread_analysis.sns_client import ThreadsToken, persist_token, load_token

with tempfile.TemporaryDirectory() as td:
    p = Path(td) / 'sns-token.json'
    tok = ThreadsToken(
        access_token='FAKE_TOKEN_' + 'x' * 8,
        expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
        user_id='0',
    )
    persist_token(tok, path=p)
    assert p.exists()
    # fstat guard (NOT os.stat on path)
    fd = os.open(str(p), os.O_RDONLY | os.O_NOFOLLOW)
    try:
        mode = stat.S_IMODE(os.fstat(fd).st_mode)
    finally:
        os.close(fd)
    assert mode == 0o600, f'expected 0600, got {oct(mode)}'
    # round-trip
    assert load_token(path=p).access_token == tok.access_token
    print('OK')
"

# AC7: HttpClient protocol exposes post(); fake http that lacks post() must fail at instantiation
python -c "
from thread_analysis.sns_client import HttpClient
# Default http from urllib.request must support post(); smoke-test the import surface.
assert hasattr(HttpClient, 'get')
print('OK (HttpClient protocol documented in spec; post() lives on real impl)')
"
```

## Verification & Status Update (REQUIRED before claiming done)
1. Run the AC commands above. Quote each exit code.
2. Update `phases/0-mvp/index.json`.
3. **Status reporting contract — v0:** the installed runner reads status from `index.json`; it does not currently parse HTML-comment markers. See PRD §4.1.

## Don't
- Do NOT call the real Threads API in unit tests.
- Do NOT embed a real access token in tests.
- Do NOT add keyring / sqlite / any storage beyond the JSON token file (NG3).
- Do NOT add Instagram / any non-Threads platform (NG1).
- Do NOT change the `Post` / `Summary` dataclass (now in `sns_types`; re-exported via `sns_analyzer`).
- Do NOT skip the 0600 perm / atomic / symlink / **fstat** tests. Reason: token-handling regressions silently expose a credential.
- Do NOT use string-equality (`==`) for OAuth state comparison.
- Do NOT generate OAuth state via non-cryptographic randomness.
- Do NOT emit the URL, the request body, or the response body inside any error message (m1).
- Do NOT default `ThreadsClient(overall_deadline=None)` at the production CLI call site. The v0 default IS 60.0; tests may pass `None` explicitly to disable.
- Do NOT implement `load_token` mode-check via `os.stat(path)`. Use `os.fstat(fd)` on the opened descriptor; tests pin the diff.
