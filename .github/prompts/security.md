Load the /dev-kit:security skill from $HOME/.claude/plugins/marketplaces/dev-kit/skills/security/SKILL.md
(use the Read tool). Follow its protocol. After analysis, post the
security summary as a single PR comment via:
  gh pr comment "__PR_NUMBER__" --body "..."

The body MUST begin with a single line of exactly one of:
  Verdict: Approve
  Verdict: Changes Requested
  Verdict: Blocked
(Do not use the bold-wrapped form here; the gate's regex parses
only "Verdict: <value>" so trailing prose that echoes this example
won't accidentally satisfy the gate.)

Render the security summary (per-category breakdown table + Verdict).
The summary MUST begin with a single line exactly of the form:

  Verdict: Approve
  Verdict: Changes Requested
  Verdict: Blocked

(Do not use the bold-wrapped form here; the gate's regex parses
only "Verdict: <value>".)

Map verdict per spec:
  - critical >= 1              -> Verdict: Blocked
  - major >= 1, critical = 0   -> Verdict: Changes Requested
  - no critical, no major      -> Verdict: Approve
