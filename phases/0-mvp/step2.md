# Step 2: Pure summary generator (topics, cadence, tone, top engagement)

## Status
**pending** — last update: 2026-07-15T00:00:00Z

## Read first
- `/PRD.md`
- `/CLAUDE.md`
- `/pyproject.toml`
- `/src/thread_analysis/sns_types.py` (Post + Summary leaf dataclasses from step 0 — `from sns_types import Post, Summary`)
- `/src/thread_analysis/sns_client.py` (ThreadsClient from step 1 — only for understanding Post shape; do not import from here in pure summary code)
- `/tests/test_sns_types.py` (sns_types contract test from step 0)
- `phases/0-mvp/step0.md`
- `phases/0-mvp/step1.md`

## Task
Implement a pure function that turns `list[Post]` into a `Summary`. **No I/O, no network, no LLM calls in this step** — pure, deterministic, fully unit-testable.

File paths to create:
- `src/thread_analysis/sns_summarizer.py` — module containing:
  - `from thread_analysis.sns_types import Post, Summary` (NO import from sns_analyzer — would re-introduce the M11 import cycle).
  - `def summarize(posts: list[Post], *, top_n_topics: int = 5, top_n_engagement: int = 3) -> Summary`
    - `top_topics`: top-N keywords by frequency, lowercased, stopwords filtered, length >= 3 chars. Sort: count desc, then alpha asc.
    - `topic_counts`: `dict[str, int]` mapping each keyword in `top_topics` to its corpus frequency. Same ordering.
    - `avg_gap_hours`: mean gap between consecutive posts in hours. If <2 posts, return 0.0. Use `created_at` ordering (most-recent first, so reverse to chronological for the gap math).
    - `tone_tags`: fixed taxonomy of ≤5 tags chosen deterministically by simple heuristics (e.g. high-reply ratio → "discussion"; short avg length → "punchy"; many questions → "ask-me-anything").
    - `top_engagement`: top-N posts by `(like_count + 2*reply_count + 3*repost_count)`, tie-break by `created_at` desc.
  - `STOPWORDS: frozenset[str]`
  - `def _tokenize(text: str) -> list[str]`
  - `def _tone_tags(posts: list[Post]) -> list[str]`
- `tests/test_sns_summarizer.py`:
  - `test_empty_posts` — `Summary(post_count=0, top_topics=[], topic_counts={}, avg_gap_hours=0.0, tone_tags=[], top_engagement=[])`. **`topic_counts={}` is required** since `Summary` is a frozen dataclass — omitting it raises `TypeError` before any assertion.
  - `test_single_post`
  - `test_avg_gap_hours_two_posts`
  - `test_top_topics_frequency`
  - `test_top_topics_stopwords_filtered`
  - `test_top_engagement_weighted`
  - `test_tone_tags_deterministic`
  - `test_short_texts_tone_tag`
  - `test_topic_counts_populated` — `summary.topic_counts` maps each `top_topics` keyword to its corpus frequency (== the count that placed it on the top-N list).
  - `test_no_circular_import` — `from thread_analysis import sns_analyzer, sns_summarizer` succeeds (the M11 cycle is broken; sns_summarizer pulls `Post`/`Summary` from `sns_types`, NOT from `sns_analyzer`).

Non-negotiable rules:
- TDD: tests first.
- Pure: no `print`, no I/O, no network, no LLM. Deterministic.
- No external NLP libs. Stdlib only.
- **Do NOT import from `sns_analyzer` in this module.** Reason: would re-introduce the M11 circular dependency the leaf module was created to break.

## Acceptance Criteria
```bash
# AC1: imports
python -c "from thread_analysis.sns_summarizer import summarize, STOPWORDS; from thread_analysis.sns_types import Post, Summary; print('OK')"

# AC2: summarizer unit tests pass
pytest tests/test_sns_summarizer.py -v

# AC3: full suite green
pytest tests/ -v

# AC4: pure-function check — no forbidden imports AND no forbidden function calls
# AND the import set includes the SOURCE MODULE for any `from X import Y` statement
python -c "
import ast, pathlib
src = pathlib.Path('src/thread_analysis/sns_summarizer.py').read_text()
tree = ast.parse(src)

forbidden_imports = {'requests', 'urllib', 'urllib3', 'httpx', 'subprocess'}
imports = set()
for x in ast.walk(tree):
    if isinstance(x, ast.Import):
        for n in x.names:
            imports.add(n.name.split('.')[0])
    elif isinstance(x, ast.ImportFrom):
        src_mod = (x.module or '').split('.')[0]
        if src_mod:
            imports.add(src_mod)
        for n in x.names:
            imports.add(n.name.split('.')[0])
imp_leak = imports & forbidden_imports
assert not imp_leak, f'forbidden import: {sorted(imp_leak)}'

forbidden_calls = {
    ('subprocess', 'run'), ('subprocess', 'Popen'), ('subprocess', 'call'),
    ('os', 'system'), ('os', 'popen'), ('os', 'exec'),
    ('pathlib', 'write_text'), ('pathlib', 'write_bytes'),
}
calls = []
for x in ast.walk(tree):
    if isinstance(x, ast.Call) and isinstance(x.func, ast.Attribute):
        v, a = x.func.value, x.func.attr
        if isinstance(v, ast.Name):
            calls.append((v.id, a))
        elif isinstance(v, ast.Attribute) and isinstance(v.value, ast.Name):
            calls.append((v.value.id, a))
call_leak = set(calls) & forbidden_calls
assert not call_leak, f'forbidden call: {sorted(call_leak)}'

forbidden_builtins = {'print', 'open', 'input'}
builtin_calls = {(None, x.func.id) for x in ast.walk(tree)
                 if isinstance(x, ast.Call) and isinstance(x.func, ast.Name) and x.func.id in forbidden_builtins}
assert not builtin_calls, f'forbidden builtin call: {sorted(builtin_calls)}'

# M11 enforcement: must NOT import from sns_analyzer (which would re-introduce
# the cycle; sns_summarizer should import Post/Summary from sns_types).
for x in ast.walk(tree):
    if isinstance(x, ast.ImportFrom) and x.module and 'sns_analyzer' in x.module:
        raise AssertionError(f'sns_summarizer.py must NOT import from sns_analyzer (M11 cycle): {x.module}')

print('OK')
"
```

## Verification & Status Update (REQUIRED before claiming done)
1. Run the AC commands above. Quote each exit code.
2. Update `phases/0-mvp/index.json`.
3. **Status reporting contract — v0:** see PRD §4.1.

## Don't
- Do NOT import from `sns_analyzer` here. Reason: M11 circular dependency.
- Do NOT call any external service, LLM, or network.
- Do NOT add NLTK / spaCy.
- Do NOT change `Post` / `Summary` field shapes.
- Do NOT add storage, scheduling, or Instagram support.
- Do NOT add randomness.
