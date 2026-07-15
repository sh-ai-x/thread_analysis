# Step 2: Pure summary generator (topics, cadence, tone, top engagement)

## Status
**pending** — last update: 2026-07-15T00:00:00Z

## Read first
- `/PRD.md`
- `/CLAUDE.md`
- `/pyproject.toml`
- `/src/thread_analysis/sns_analyzer.py` (Post + Summary dataclasses from step 0)
- `/src/thread_analysis/sns_client.py` (ThreadsClient from step 1)
- `phases/0-mvp/step0.md` (Post/Summary contract)
- `phases/0-mvp/step1.md` (Post fields)

## Task
Implement a pure function that turns `list[Post]` into a `Summary`. **No I/O, no network, no LLM calls in this step** — pure, deterministic, fully unit-testable.

File paths to create:
- `src/thread_analysis/sns_summarizer.py` — module containing:
  - `def summarize(posts: list[Post], *, top_n_topics: int = 5, top_n_engagement: int = 3) -> Summary`
    - `top_topics`: top-N keywords by frequency, lowercased, stopwords filtered, length >= 3 chars. Sort: count desc, then alpha asc. Tie-break deterministic.
    - `avg_gap_hours`: mean gap between consecutive posts in hours. If <2 posts, return 0.0. Use `created_at` ordering (most-recent first, so reverse to chronological for the gap math).
    - `tone_tags`: fixed taxonomy of ≤5 tags chosen deterministically by simple heuristics on the corpus (e.g. high-reply ratio → "discussion"; short avg length → "punchy"; many questions → "ask-me-anything"). Document the heuristics in module docstring. No LLM.
    - `top_engagement`: top-N posts by `(like_count + 2*reply_count + 3*repost_count)`, tie-break by `created_at` desc.
    - `topic_counts`: `dict[str, int]` mapping each keyword in `top_topics` to its corpus frequency. Same ordering as `top_topics` (count desc, then alpha asc) reflected by the top-N subset; the underlying full corpus frequency is what `topic_counts` exposes.
  - `STOPWORDS: frozenset[str]` — small built-in English stopword set (~100 words). No NLTK download.
  - `def _tokenize(text: str) -> list[str]` — lowercase, regex `[a-z]{3,}`, return list. (No stemming in v0.)
  - `def _tone_tags(posts: list[Post]) -> list[str]` — heuristic; deterministic.

- `tests/test_sns_summarizer.py` — unit tests:
  - `test_empty_posts` — empty list → `Summary(post_count=0, top_topics=[], topic_counts={}, avg_gap_hours=0.0, tone_tags=[], top_engagement=[])`. (The `topic_counts={}` field is required since step 0 added it to the `Summary` dataclass; omitting it raises `TypeError` before any assertion runs.)
  - `test_single_post` — 1 post → `avg_gap_hours=0.0`, `top_engagement` contains it.
  - `test_avg_gap_hours_two_posts` — two posts 6 hours apart → `avg_gap_hours=6.0`.
  - `test_top_topics_frequency` — feed with repeated keywords → top topics sorted by count desc, alpha tiebreak asc.
  - `test_top_topics_stopwords_filtered` — common stopwords ("the", "and", "is") never appear.
  - `test_topic_counts_populated` — feed with repeated keywords → `summary.topic_counts` maps each `top_topics` keyword to its corpus frequency (== the count that placed it on the top-N list).
  - `test_top_engagement_weighted` — post with high reply_count beats one with high like_count at the same weight tier.
  - `test_tone_tags_deterministic` — same input → same output across two calls.
  - `test_short_texts_tone_tag` — short avg length → `"punchy"` present.
  - Use a `make_post(...)` factory for fixture data; no external files.

Non-negotiable rules:
- TDD: tests first.
- Pure: no `print`, no I/O, no network, no LLM. Deterministic.
- No external NLP libs (no NLTK, no spaCy). Stdlib only.
- Do NOT change `Post` or `Summary` dataclass shape.

## Acceptance Criteria
```bash
# AC1: imports
python -c "from thread_analysis.sns_summarizer import summarize, STOPWORDS; print('OK')"

# AC2: summarizer unit tests pass
pytest tests/test_sns_summarizer.py -v

# AC3: full suite green
pytest tests/ -v

# AC4: pure-function check — no forbidden imports AND no forbidden function calls
python -c "
import ast, pathlib
src = pathlib.Path('src/thread_analysis/sns_summarizer.py').read_text()
tree = ast.parse(src)

# (a) forbidden by import — must record both `ast.Import` and `ast.ImportFrom`
#     source modules. `from urllib.request import urlopen` would otherwise slip
#     past because `n.name` is just 'urlopen'.
forbidden_imports = {'requests', 'urllib', 'urllib3', 'httpx', 'subprocess'}
imports = set()
for x in ast.walk(tree):
    if isinstance(x, ast.Import):
        for n in x.names:
            imports.add(n.name.split('.')[0])          # 'import urllib.request' -> 'urllib'
    elif isinstance(x, ast.ImportFrom):
        src_mod = (x.module or '').split('.')[0]       # 'from urllib.request import …' -> 'urllib'
        if src_mod:
            imports.add(src_mod)
        for n in x.names:
            imports.add(n.name.split('.')[0])          # also catch 'from foo import bar' forbidden alias
imp_leak = imports & forbidden_imports
assert not imp_leak, f'forbidden import: {sorted(imp_leak)}'

# (b) forbidden by qualified function call (e.g. subprocess.run, os.system, pathlib.Path.write_text)
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

# (c) forbidden builtins used as bare-name calls (e.g. open(...), print(...))
forbidden_builtins = {'print', 'open', 'input'}
builtin_calls = {(None, x.func.id) for x in ast.walk(tree)
                 if isinstance(x, ast.Call) and isinstance(x.func, ast.Name) and x.func.id in forbidden_builtins}
assert not builtin_calls, f'forbidden builtin call: {sorted(builtin_calls)}'

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
- Do NOT call any external service, LLM, or network in this module. Reason: pure-function contract; side effects kill testability. AC4 enforces this statically (imports + calls + builtins).
- Do NOT add NLTK, spaCy, or other NLP libs. Reason: stdlib-only keeps the surface small and the install light.
- Do NOT change `Post` or `Summary` field shapes. Reason: backward compat with step 0.
- Do NOT add storage, scheduling, or Instagram support. Reason: non-goals NG1/NG3/NG4.
- Do NOT add randomness (e.g. `random.shuffle`) inside `summarize`. Reason: determinism is a test contract.
