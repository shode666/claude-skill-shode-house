# Repo invariants, detail — skills, agents, output styles

This file states no rule. The rules are in `AGENTS.md`, which is loaded on every session; each section here adds scope detail, rationale, history or examples to the section of that file named in its heading, and is meant to be read next to it. If anything here seems to differ from that file, that file is the rule. Linked from the index table there, not imported.

The rules under `AGENTS.md` § Handoff + Language, and under `AGENTS.md` § Commands, need no further detail and have no section here.

## Detail for `AGENTS.md` § Skills

What the five shipped buckets hold today, 20 skills in all (7 · 4 · 2 · 1 · 6; the domain experts of 4.0.0 are `references/domain/<domain>.md` loaded through `domain-core`, not skills):

| Bucket | Skills |
|--------|--------|
| `workflow/` | ask, dev-gate, automate-test, diagnose, data-migration, api-contract, decompose |
| `ops/` | incident, slo, secure, drain |
| `ui/` | ui-test, web-q |
| `style/` | caveman |
| `discipline/` | shode-house-discipline, -routing, -deliverable, -workflow, review-checklist, domain-core |

The four retired names come from the v3.17 merge; the table of old name → new owner is in the CHANGELOG.

`ask/SKILL.md` is the public entry point and the team orientation.

## Detail for `AGENTS.md` § Agents

**Review axes** (since v3.12; 4.0.1 types). The Standards axis is the `verify` standards review (7 dimensions) and asks *is it written correctly*; the Spec axis is a fresh `plan` spawn and asks *does it do what the spec asked for*. `verify` also serves the runtime axis and `plan` also serves the domain axis, each as its own named spawn, so a type shared by two axes never merges them. Example of the two verdicts diverging: code that passes every standard but does the wrong thing is Standards PASS / Spec FAIL.

**Preload budget.** The `skills:` cap of 3 limits how many skills are preloaded, not how large they are, which is why a separate byte cap exists. The per-agent keys run with grace 0.

**Catalog ≠ Evidence** (since v3.11). The catalog is palettes, pairings and patterns taken from CSV files that upstream itself labels `derived` / `needs-review`. Quoting a CSV figure as if it were tool output breaks the UX Evidence Protocol. The runtime steps (0-result retry and so on) are in `references/runbooks/design-phase-1b.md`.

**The `Skill` tool** (since v3.10). The two mechanisms do different jobs: `skills:` preloads (full content injected at spawn, cap 3), while `Skill` in `tools:` lets the agent load more at runtime. Leaving `Skill` out of an explicit `tools:` list blocks every skill, not only the ones that were not preloaded.

**Universal rules.** `shode-house-discipline` is preloaded by all 6 agent types, so every byte in it is paid 6 times (18 before 4.0.1). That cost is why a role's own rule is kept out of it and loaded by that role.

**`skills:` frontmatter** (since v3.8). A sub-agent starts in an empty context: it sees its agent body, the delegation message and the target project's CLAUDE.md, nothing else. Skills the router (the main session) has loaded do not travel with it. The cap of 3 keeps instruction density down (IFScale: more instructions, worse following). When `skills:` names a skill in a non-shipped bucket, Claude Code skips it quietly: debug log only, no error.

**Model frontmatter** (since v3.5). A copy of the model table in the routing skill drifted in v2.x, which is why the rule in `AGENTS.md` gives the table a single home. Fallback is the `fallbackModel` setting and the budget override is `CLAUDE_CODE_SUBAGENT_MODEL`; both are documented in the README.

**Bias Discipline**, as embedded per role in the agent prompts:

- `verify`: no PASS without the required evidence — a defect is FAIL, missing evidence is BLOCKED/PARTIAL (`agents/verify.md`, `review-checklist` §Adversary stance).
- the fintech and trading domain references: "ห้าม blindly accept vendor" (root lines in `skills/discipline/domain-core/SKILL.md` § Domain red lines).
- `secure`: hold on "low risk" when a trigger applies.

## Detail for `AGENTS.md` § Output styles

- `output-styles/` at the plugin root is the default scan path. An `outputStyles` manifest field would, besides replacing that scan, add Cowork-validator risk.
- Optional frontmatter: `keep-coding-instructions: true` keeps the original engineering prompt; `force-for-plugin: true` takes over the main session as soon as the plugin is enabled, overriding the user's `outputStyle`.
- An output style changes the system prompt of the main loop only; sub-agents are not affected. It takes effect after `/clear` or in a new session.
- `output-styles/` is an entry of `.pack-allowlist`.
- Why Cowork support is unconfirmed: the published docs cover the Claude Code CLI and the Code tab only.
