# PRD — SNS Self-Analyzer (Threads)

> Solo creator self-analysis of own Threads posts. v0 scope.

## §1 Frame

- **goal**: Ship a Claude Code skill that connects to Threads, fetches the user's own last 20 posts, and prints a one-screen summary — top topics, posting cadence, tone tags, top-engagement posts.
- **target user**: Solo creator self-analysis (1 persona, 1 user, 1 platform).
- **situation**: Today, ~1h/week is spent scrolling + screenshotting + summarizing own ~20 posts/week by hand. No LLM-native, conversational surface exists for this workflow.

> Scope was originally proposed as 3 personas (solo creator, marketing analyst, researcher). User accepted narrowing to 1 persona as the trade-off for the missing market/community evidence. Marketing and researcher modes are deferred to non-goals (NG2) and to a separate post-MVP PRD.

## §2 Validate

| Metric | Value | Threshold | Pass |
|---|---|---|---|
| `value_score` | 10.0 | ≥ 3.0 | ✅ |
| `ambiguity_score` | 3 | ≤ 3 | ✅ |
| `evidence_count` | 1 | ≥ 3 (narrowed to 1 persona → 1 signal suffices) | ✅ (narrowed) |

### 2.1 — Value score (LTV × reachable / cost)

```
LTV_per_user           = $5,000/yr   (50h/year saved × $100/h creator-strategic rate)
reachable_users_year1  = 1           (personal use; post-MVP may share)
total_cost             = $500        (5h AI-assisted build × $100/h, no infra, no GTM)
value_score            = (5,000 × 1) / 500 = 10.0
```

### 2.2 — Evidence (1 concrete signal)

| # | Source | Claim | Date |
|---|---|---|---|
| 1 | Personal need (the user, scratch-your-own-itch) | ~1h/week scroll + summarize own ~20 posts/week. | 2026-07-15 |

> The other two original signals (market data, community ask) were skipped. The user accepted narrowing scope to 1 persona to compensate. See `.prd/decision-log.md` for the full Q&A trail.

### 2.3 — Ambiguity loop (10 → 3)

| Cycle | Knob | Decision | Δ |
|---|---|---|---|
| 1 | scope | Pull + summarize own last 20 posts. | 10 → 8 |
| 2 | metric | Time-to-summary (min) — target <2 min/run vs ~60 min manual. | 8 → 6 |
| 3 | data source | Threads only (Meta Graph API for Threads). | 6 → 4 |
| 4 | kill | Kill if used <2×/week after 4 weeks. | 4 → 3 |

## §3 Non-goals

| # | Non-goal | Rationale | Breach-response |
|---|---|---|---|
| **NG1** | No Instagram support. v0 covers Threads only. | Scope narrowed; 1 signal is for 1 platform. Instagram Graph API requires Business/Creator account + separate OAuth flow. | Phase 2 only after Threads adoption is stable; separate PRD for new OAuth + new rate-limit regime. |
| **NG2** | No cross-account / marketing-analyst mode. | 1 persona only (solo creator self). Cross-account comparison = different user, different value proposition. | Separate PRD when a concrete paying user or community ask appears. Defer to post-MVP. |
| **NG3** | No post storage / history. v0 is one-shot: pull + summarize, print, exit. | 1 user = no historical need yet. Storage adds schema-versioning, migration, privacy surface for no current value. | Append-only JSONL log in phase 2 once summary shape is stable; needs schema versioning + retention policy. |
| **NG4** | No reply / post generation. v0 analyzes only. | Generation has a different risk profile (LLM-authored public content); mixes reading and writing concerns. | Separate skill with content-policy + review-gate; not in this PRD's scope. |
| **NG5** | No scheduled / automated runs. v0 is user-invoked on demand. | Cron / launchd / scheduler = additional architecture (failure handling, retry, dedup) not justified at v0 volume. | Post-MVP if usage patterns show demand; needs scheduler design. |
| **NG6** | No multi-user / shared auth. v0 is 1 user, 1 Threads account, 1 OAuth token. | Secret management for >1 user needs keyring / 1Password / multi-tenant auth. | Post-MVP if sharing is requested; needs proper secret management. |

## §4 Phase plan

Phase: **`0-mvp`** — see `phases/0-mvp/index.json`.

| # | Title | File |
|---|---|---|
| 0 | Scaffold skill directory + CLI shell | `phases/0-mvp/step0.md` |
| 1 | Threads API client with OAuth + list-own-posts | `phases/0-mvp/step1.md` |
| 2 | Pure summary generator (topics, cadence, tone, top engagement) | `phases/0-mvp/step2.md` |
| 3 | Wire API + summary into `analyze-my-threads` CLI command with formatted output | `phases/0-mvp/step3.md` |
| 4 | End-to-end AC verification: time-to-summary <2 min, output matches spec | `phases/0-mvp/step4.md` |

Worktree base: `plan/sns-thread-analysis` (cumulative single branch — the runner checks out this branch directly; see `.dev-kit/hand-off/plan→build.md` for the rationale over a per-step-worktree strategy that cannot carry step N-1's commits without an extra merge layer).

Ordering rationale: dependency-first. Data shapes (step 0) → data plane (step 1) → pure logic (step 2) → wiring (step 3) → end-to-end verification (step 4).

## §5 AC list (1:1 with step AC)

| AC | Step | Verification |
|---|---|---|
| AC1 | step 0 | `python -c "import thread_analysis; from thread_analysis.sns_analyzer import cli_main, Post, Summary"` exits 0; `pytest tests/test_sns_analyzer.py -v` passes; `pytest tests/ -v` (full suite) green; `cli_main(["--help"])` returns 0. |
| AC2 | step 1 | `pytest tests/test_sns_auth.py -v` and `pytest tests/test_sns_client.py -v` pass; full suite green; token-file 0600 perm helper test passes. |
| AC3 | step 2 | `pytest tests/test_sns_summarizer.py -v` passes; full suite green; static AST check confirms no `open`/`urlopen`/`requests`/`urllib`/`subprocess`/`print` in `sns_summarizer.py`. |
| AC4 | step 3 | `pytest tests/test_sns_output.py -v` and `pytest tests/test_sns_analyzer.py -v` pass; full suite green; `python -m thread_analysis.sns_analyzer --help` exits 0; `--no-auth-bootstrap` with no token exits non-zero + auth error. |
| AC5 | step 4 | `pytest tests/test_sns_e2e.py -v` passes; full suite green; wall-clock of `summarize` on 20-post fixture < 5s; golden text file non-empty; runbook contains the command; README has the "SNS Analyzer" section. |

Track B (manual, not in CI): run `time python -m thread_analysis.sns_analyzer --limit 20` against a real Threads account; pass criterion: <2 minutes. See `docs/SNS_RUNBOOK.md` (created in step 4).

## §6 Hand-off

Next invocation: **`/dev-kit:build`** — converts `phases/0-mvp/step<N>.md` into per-step implementation via harness-runner.

Preconditions for `/dev-kit:build`:
- `.dev-kit/ci-config.json` exists (per `dev-kit:ci-setup` requirement) — already present in repo.
- `phases/0-mvp/index.json` + 5 step files in place — done.
- This PRD.md in place — done.
- `.prd/decision-log.md` captures full Q&A trail — done.
- `.dev-kit/loop-log.json` records the 5 narrowing cycles — done.

Stage transition: `state_codec.transition_stage(root, "build")` will be applied automatically by the build runner on invocation.

## §4.1 Build-system note: runner contract scope

The dev-kit plugin's build runner (`~/.claude/plugins/cache/dev-kit/dev-kit/<v>/lib/execute.py`) is **out of scope for this PRD's product surface**. The product is the SNS analyzer; the runner is the harness that drives sub-agents through the phase steps.

In v0, the runner reads each step's status from `phases/0-mvp/index.json` plus the sub-agent's exit code. It does **not** parse HTML-comment markers; that capability (`parse_status_marker`) ships in a separate follow-up PR against the dev-kit plugin, not in this repository. Phase files document the marker format for forward compatibility only.

Why this matters for reviewers:
- "non-goal NG1–NG6" in §3 are user-facing scope fences (no Instagram, no cross-account, no storage, no generation, no scheduler, no multi-user).
- The runner-contract scope is a build-time fence: `lib/execute.py:parse_status_marker` is owned upstream of this repo and not deliverable here.
