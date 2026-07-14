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
  - `STOPWORDS: frozenset[str]` — small built-in English stopword set (~100 words). No NLTK download.
  - `def _tokenize(text: str) -> list[str]` — lowercase, regex `[a-z]{3,}`, return list. (No stemming in v0.)
  - `def _tone_tags(posts: list[Post]) -> list[str]` — heuristic; deterministic.

- `tests/test_sns_summarizer.py` — unit tests:
  - `test_empty_posts` — empty list → `Summary(post_count=0, top_topics=[], avg_gap_hours=0.0, tone_tags=[], top_engagement=[])`.
  - `test_single_post` — 1 post → `avg_gap_hours=0.0`, `top_engagement` contains it.
  - `test_avg_gap_hours_two_posts` — two posts 6 hours apart → `avg_gap_hours=6.0`.
  - `test_top_topics_frequency` — feed with repeated keywords → top topics sorted by count desc, alpha tiebreak asc.
  - `test_top_topics_stopwords_filtered` — common stopwords ("the", "and", "is") never appear.
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

# AC4: pure-function check (no obvious side effects)
python -c "
import ast, pathlib
src = pathlib.Path('src/thread_analysis/sns_summarizer.py').read_text()
tree = ast.parse(src)
forbidden = {'open', 'urlopen', 'requests', 'urllib', 'subprocess', 'print'}
imports = {n.name.split('.')[0] for x in ast.walk(tree) if isinstance(x, (ast.Import, ast.ImportFrom)) for n in x.names}
leak = imports & forbidden
assert not leak, f'leaky import: {leak}'
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
- Do NOT call any external service, LLM, or network in this module. Reason: pure-function contract; side effects kill testability.
- Do NOT add NLTK, spaCy, or other NLP libs. Reason: stdlib-only keeps the surface small and the install light.
- Do NOT change `Post` or `Summary` field shapes. Reason: backward compat with step 0.
- Do NOT add storage, scheduling, or Instagram support. Reason: non-goals NG1/NG3/NG4.
- Do NOT add randomness (e.g. `random.shuffle`) inside `summarize`. Reason: determinism is a test contract.
