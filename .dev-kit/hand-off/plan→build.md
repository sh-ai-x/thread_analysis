# Hand-off: plan → build

## Idea
Claude Code skill for solo creator self-analysis of own Threads posts. v0 = "Pull + summarize own last 20 posts" with a one-screen text output.

## Plan summary
- **Scope**: 1 persona (solo creator), 1 platform (Threads), 1 user, 1 shot. No Instagram, no cross-account, no storage, no generation, no scheduler, no multi-user.
- **Frame**: §1 of `PRD.md`.
- **Validate**: value_score 10.0, ambiguity_score 3, evidence_count 1 (narrowed scope to 1 persona to compensate).
- **Non-goals**: NG1–NG6 in `PRD.md` §3.
- **Phase**: `0-mvp` (5 steps, dependency-first).

## Phase state
`phases/0-mvp/index.json` — all 5 steps registered with `status: pending`, ready for build-runner pickup.

| # | Step | Status |
|---|---|---|
| 0 | scaffold-cli-shell | pending |
| 1 | threads-api-client | pending |
| 2 | summary-generator | pending |
| 3 | cli-wire-and-format | pending |
| 4 | end-to-end-ac | pending |

## Build-runner entry point

```
/dev-kit:build
```

The runner will:
1. Read `phases/0-mvp/index.json`.
2. **Run on a single cumulative worktree** — checks out `plan/sns-thread-analysis` directly. After each step's AC passes and `index.json` is updated, the runner publishes the step's commits upstream (the same branch on origin) so step N+1 begins with a working tree that includes step N's commits. **See "Known limitations" below** for the carry-into-step-N+1 contract.
3. Execute the per-step TDD cycle from `phases/0-mvp/step<N>.md`.
4. Capture status markers, update `index.json`, advance to step N+1.

## Known limitations (cross-repo / build-time, not product non-goals)

These are **build-time concerns, not user-facing NG1–NG6**. They are documented here so the build runner / a follow-up PR can address them. They are NOT blockers per PRD §4.1 (which sets the runner-contract scope upstream of this repo), but they constrain how the runner must evolve for `0-mvp` to execute:

1. **C-1 / M-2 — Per-step worktree vs cumulative:**
   `~/.claude/plugins/cache/dev-kit/dev-kit/<v>/lib/execute.py:339` does `git worktree add -B <branch> <wt> origin/main` for every step. Each step's worktree branches from `origin/main`, NOT from the previous step's tip. Without a propagation mechanism, step N+1 cannot see step N's commits.

   The hand-off's "cumulative single worktree" guidance above is the **target** behavior; the current runner does not implement it. To make `0-mvp` executable end-to-end, the runner must either:
   - (a) be modified to integrate step N's branch into origin/main between step executions (a fetch-and-merge or fast-forward sync, ahead of step N+1's worktree creation), OR
   - (b) introduce a worktree-base override that respects `index.json["worktree"]` as a base ref (not just a name).

   This is a follow-up PR against dev-kit, NOT this PR. The plan continues to document the cumulative strategy because that is what `phases/0-mvp/index.json["worktree"]: "plan/sns-thread-analysis"` says. A runner that follows `index.json["worktree"]` semantics faithfully WILL pick up step N+1 from the prior step's tip (because every step N publishes back to that branch).

2. **M-6 — Live <2-min enforcement in CI:**
   The PRD's <2-min target is a live Threads account metric. CI cannot enforce it without a test Threads account + OAuth secret. Track A's <5s wall-clock covers the inside-CI bound; Track B's <2-min is a runbook-only sign-off. To gate Track B in CI: provision a fixture Threads account (test-account-oauth flow + reduced-quota sandbox) and add a `Track B live-time job` that requires `@repo:secrets:THREADS_TEST_TOKEN`.

## What the build runner MUST honor

- **methodology = tdd** (default per `CLAUDE.md` §2). Each step's `## Acceptance Criteria` block lists the verification commands; tdd-guard will block non-TDD PRs.
- **Scope discipline**: NG1–NG6. The runner should reject any step that grows instagram / cross-account / storage / generation surface.
- **Backward compat within the phase**: step 0's `cli_main(["--help"])` contract, the `Post` and `Summary` dataclass shapes (now in `sns_types` after the M11 split), and the `cli_main` exit-code contract from step 3 must be preserved end-to-end.
- **No real access tokens** in any test fixture or runbook. `secret-scan` will fail CI.
- **TDD**: tests first. step 1's `0600` perm + `os.fstat(fd)` test is non-negotiable.

## Files emitted by plan
- `PRD.md`
- `phases/0-mvp/index.json`
- `phases/0-mvp/step0.md` … `step4.md`
- `.prd/decision-log.md`
- `.dev-kit/loop-log.json`
- `.dev-kit/hand-off/plan→build.md` (this file)

## Open risks (informational, not blocking)
- **Threads API rate limits**: not measured. Step 4's runbook asks the user to record wall-clock and any rate-limit incidents.
- **OAuth UX**: bootstrap prints URL + prompts the user. Acceptable for v0.
- **Tone-tag heuristics**: chosen by simple rules, no LLM. May feel naïve; post-MVP can swap in an LLM call.

## Status: ready for build (with known build-time limitations per "Known limitations" section above).
