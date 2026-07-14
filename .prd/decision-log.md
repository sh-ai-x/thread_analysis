# frame

- **goal**: Ship a Claude Code skill that connects to Threads and/or Instagram, fetches posts (own feed or specified public accounts), and analyzes them — supporting three personas (solo creator self-analysis, marketing/strategy analyst, researcher/cultural analyst) with persona-adaptive output routing.
- **target user**: Three personas, all served by one skill with adaptive mode selection:
  1. **Solo creator** — analyzing own posts for topics, cadence, tone, what resonates.
  2. **Marketing/strategy analyst** — comparing multiple accounts for engagement, themes, posting rhythm.
  3. **Researcher/cultural analyst** — studying public figures / industry accounts for themes, sentiment, discourse over time.
- **situation**: Today, no conversational/LLM-native surface exists for Threads/Instagram analysis. Users either scroll-screenshot-summarize by hand, or use dashboard-shaped third-party tools (Sprout, Later, native Insights) that are not integrated with Claude and not adaptive to intent.

# gate-2 cycle 1 (scope narrowed to solo creator only)

- **evidence_count = 1** (personal itch: ~1h/week scroll + summarize own ~20 posts/week). Gate threshold = 3.
- **Resolution**: User chose to narrow scope to solo creator only (1 signal is sufficient for 1 persona). Marketing-analyst and researcher modes are deferred to non-goals / post-MVP.
- **LTV** = $5,000/yr (50h/year saved × $100/h creator-strategic rate — user-declared default, not specified).
- **reachable_users_year1** = 1 (personal use, post-MVP could share).
- **total_cost** = $500 (5h AI-assisted build × $100/h, no infra, no GTM — user-declared default).
- **value_score** = (5,000 × 1) / 500 = **10.0** → PASSES 3.0.
- **next**: ambiguity loop — ask highest-leverage unknown (smallest 2-week version).

# gate-2 cycle 2 (ambiguity loop)

- **scope** (highest-leverage unknown after frame): User chose **"Pull + summarize own last 20 posts"** as the smallest 2-week version. CLI subcommand `analyze-my-threads` that fetches user's own last 20 posts and prints a one-screen summary (top topics, posting cadence, tone tags, what got most engagement). No storage, no history in v0.
- **score**: 10 → 8 (-2, scope narrows the surface area sharply).

# gate-2 cycle 3 (metric)

- **metric** (success): User chose **Time-to-summary (min)**. Target: <2 minutes per run, vs ~60 minutes manual today.
- **score**: 8 → 6 (-2, makes success falsifiable).

# gate-2 cycle 4 (data source)

- **data source**: User chose **Threads only** (Meta Graph API for Threads). One OAuth flow, one rate-limit regime.
- **score**: 6 → 4 (-2, eliminates dual-API scope creep).

# gate-2 cycle 5 (kill criteria)

- **kill**: User chose **"Kill if used <2×/week after 4 weeks"**. If the skill doesn't get reached for, the code working doesn't matter.
- **score**: 4 → 3 (-1, at threshold).

# gate-2 convergence

- evidence_count = 1 (user narrowed scope to 1 persona — 1 user = 1 signal, not 3).
- value_score = 10.0 (≥ 3.0) ✓
- ambiguity_score = 3 (≤ 3) ✓
- **status: converged**.

# scope-narrowing rationale (1 signal / 1 persona)

- 1 persona × 1 user × 1 platform (Threads) = single-loop build. No need for 3 evidence sources across 3 personas.
- The deal: user accepted "narrow to solo creator only" as the trade-off for the missing market/community signals. Marketing-analyst and researcher modes are **out of scope** for v0 (deferred to non-goals).