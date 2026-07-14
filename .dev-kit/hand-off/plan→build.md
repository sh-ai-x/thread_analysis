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
2. For each step in order, cut a worktree `<worktree_base>-step<N>` (= `plan/sns-thread-analysis-step0` ... `step4`).
3. Execute the per-step TDD cycle from `phases/0-mvp/step<N>.md`.
4. Capture status markers, update `index.json`, advance.

## What the build runner MUST honor

- **methodology = tdd** (default per `CLAUDE.md` §2). Each step's `## Acceptance Criteria` block lists the verification commands; tdd-guard will block non-TDD PRs.
- **Scope discipline**: NG1–NG6. The runner should reject any step that grows Instagram / cross-account / storage / generation surface.
- **Backward compat within the phase**: step 0's `cli_main(["--help"])` contract, the `Post` and `Summary` dataclass shapes, and the `cli_main` exit-code contract from step 3 must be preserved end-to-end.
- **No real access tokens** in any test fixture or runbook. secret-scan will fail CI.
- **TDD**: tests first. step 1's `0600` perm test is non-negotiable.

## Files emitted by plan
- `PRD.md`
- `phases/0-mvp/index.json`
- `phases/0-mvp/step0.md` … `step4.md`
- `.prd/decision-log.md`
- `.dev-kit/loop-log.json`
- `.dev-kit/hand-off/plan→build.md` (this file)

## Open risks (informational, not blocking)
- **Threads API rate limits**: not measured. Step 4's runbook asks the user to record wall-clock and any rate-limit incidents. If <2 min fails on real account, the spec survives but the kill criterion (used <2×/week) becomes the real test.
- **OAuth UX**: bootstrap prints URL + prompts the user. In a fully scripted environment, this is a UX gap. Acceptable for v0 (1 user, 1 setup).
- **Tone-tag heuristics**: chosen by simple rules, no LLM. May feel naïve. If so, post-MVP can swap in an LLM call (out of v0 scope per non-goals).

## Status: ready for build.
