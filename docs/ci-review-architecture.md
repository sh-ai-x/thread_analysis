# CI Review Architecture

This document explains how the GitHub Actions CI review works in this
repository, in particular the `claude-code-action@v1` self-protection
guard and how we work around it.

## Why review.yml is byte-stable

`anthropics/claude-code-action@v1` runs the LLM agent from a GitHub
Actions step. To prevent a malicious PR from rewriting the workflow
file to leak secrets through the prompt, the action validates that
the **PR head's** workflow file is byte-identical to the **main
branch's** version. If they differ, the action refuses to run:

```
##[warning]Skipping action due to workflow validation: Workflow
validation failed. The workflow file must exist and have identical
content to the version on the repository's default branch.
```

This means: **any PR that modifies `.github/workflows/review.yml`
gets a silent `Verdict: Approve` from the fallback script, not a
real LLM review.**

## How prompts are loaded

To keep `review.yml` byte-stable while still letting prompt content
evolve, the actual prompt bodies live in `.github/prompts/review.md`
and `.github/prompts/security.md`. The workflow has two `Load
<skill> prompt` steps that read these files at runtime and pass the
content to the action via `${{ steps.load_<skill>_prompt.outputs.prompt }}`.

Modifying a `.md` file does not modify any `.yml` workflow file, so
the action's self-protection guard is satisfied and the LLM runs
end-to-end.

## What changes are safe

- Modifying `.github/prompts/review.md` or `.github/prompts/security.md`
  -> LLM reviews the change.
- Modifying non-workflow source files (e.g., `src/`, `tests/`, `docs/`)
  -> LLM reviews the change.
- Modifying `.github/workflows/*.yml` -> LLM does NOT run on this PR;
  the human reviewer is the gate. After merge, future PRs that don't
  touch workflow files will get real reviews again.

## Pre-flight checklist for PRs

Before opening a PR, run `actionlint .github/workflows/*.yml` locally
(see `scripts/ci-local.sh`). If your PR modifies a workflow file,
expect the LLM review to be skipped -- that is by design.

## History

- **0.3.x -> 0.3.33**: review.yml shipped with inline prompts; every
  CI change forced the silent fallback.
- **0.3.33+**: prompts extracted to `.github/prompts/*.md`; review.yml
  is byte-stable across releases. CI modifications still trigger the
  fallback, but prompt tweaks and code changes do not.
