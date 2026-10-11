---
name: ownership
description: Reference (lazy-load) ของ `shode-house-routing` — team roster (6 agent types + router style), Formerly table (3.x persona and 4.0.0 id → 4.0.1 type), add-agent step, team structure table. Owner/RACI/domain rows อยู่ใน SKILL.md root
---

```lazy-load-contract
LOAD: skills/discipline/shode-house-routing/ownership.md
WHEN: add_remove_rename_agent=true OR resolve_retired_agent_id=true OR resolve_persona_to_agent_file_or_team=true OR team_composition_question=true
OWNER: router
REQUIRED-BEFORE: add_or_change_agent
```

# Routing — team roster & structure

## 👥 Team (6 agent types, plus the router)

> **Model**: inherit host/session settings by default. Agent frontmatter is a host-specific preference, not a portable model ID or permission to override the user's selection.
>
> 4.0.1: `secure` and `design` are pinned to the fable tier by their frontmatter; tier overrides for `plan` and `build` are passed per dispatch by the router.

- **Router**: the main session under `output-styles/shode-house.md`; routes, gates, relays and closes. It is not a spawnable agent.
- `plan` — discover (Why + What) · requirements + AC · architecture/ADR/NFR · the spec review axis · domain consult and the domain review axis (a `references/domain/<domain>.md` reference loaded through `shode-house:domain-core`)
- `build` — implementation (parallel `build#N`) · refactor · behaviour tests · staff-grade briefs (cross-team consistency, tech radar, refactor strategy)
- `verify` — the standards axis and the runtime axis (always two separate spawns)
- `operate` — CI/CD, IaC, deploy (Phase 5) · SLO, incident, runbook, postmortem (Phase 6)
- `secure` — Phase 1c threat model · the security axis · secrets, pen test
- `design` — UX, design system, WCAG · the ui axis (Phase 3a) · design-run requests (no Bash)
- **Domain (7, pluggable)**: `references/domain/<domain>.md` for fintech · erp · sap · trading · insurance · booking · ecommerce, loaded by a `plan` spawn through `shode-house:domain-core` (no domain agent exists).
- Spawn every agent as `shode-house:<id>`; a bare id is served by a project agent of that name, so a failed spawn is never retried bare.

## Formerly

3.x records, task notes and tag prefixes used persona names; 4.0.0 records and spawns used the 18 agent ids. Neither resolves as a spawn target any more (no stub agent files). Resume old records with this table; new text uses the 4.0.1 type only. A retired id is never spawned or retried as a bare type.

| Formerly (3.x persona) | Formerly (4.0.0 id) | Type (4.0.1) and how it is reached |
|---|---|---|
| Oliver | router (the 3.x agent `orchestrator`, retired in 4.0.0) | the router (main-session style) |
| Patrick | product-manager | `plan`, discover mode |
| Bella | business-analyst | `plan`, requirements mode; the spec axis is a fresh `plan` spawn that never wrote the AC |
| Sara | solution-architect | `plan`, architecture mode, router passes `model: "fable"` |
| Stan | staff-engineer | `build`, staff-grade brief, router passes `model: "fable"` (research for a radar is a `plan` brief) |
| Sentinel | security-engineer | `secure` |
| Dave | developer | `build` |
| Chris | code-reviewer | `verify`, standards axis |
| Quinn | qa-engineer | `verify`, runtime axis |
| Aaron | devops-engineer | `operate`, deploy mode |
| Reggie | sre-engineer | `operate`, reliability mode |
| Uma | ux-ui-designer | `design` |
| Felix | fintech-expert | `plan` + `references/domain/fintech.md`, `model: "opus"` |
| Elena | erp-expert | `plan` + `references/domain/erp.md`, type default (sonnet), `opus` if high-stakes |
| Sam | sap-expert | `plan` + `references/domain/sap.md`, `model: "opus"` |
| Tara | trading-expert | `plan` + `references/domain/trading.md`, `model: "opus"` |
| Iris | insurance-expert | `plan` + `references/domain/insurance.md`, `model: "opus"` |
| Brooke | booking-expert | `plan` + `references/domain/booking.md`, type default (sonnet), `opus` if high-stakes |
| Emma | ecommerce-expert | `plan` + `references/domain/ecommerce.md`, type default (sonnet), `opus` if high-stakes |

Domain tier: `opus` for fintech, sap, trading, insurance; erp, booking, ecommerce run at the type default (sonnet) and get `opus` only for high-stakes work, the reason recorded in the dispatch.

Review axes after the change: standards = `verify` · spec = `plan` · runtime = `verify` · security = `secure` · domain = `plan` + domain reference · ui = `design`, each a separate fresh spawn.

### Add agent

> Add agent: drop `agents/<name>.md` + update routing table — done
>
> Since 4.0.1 also: the review card if the type reviews, the roster test and the registries. A new type needs a tool, model or isolation difference that no existing type provides.

---

## 👥 Team Structure

7 teams ที่ทำงาน **parallel ภายในทีม + sequential ระหว่างทีม** (cross-team handoff = phase gate)

| Team (short) | Agents | Phase ที่ active | Deliverable |
|--------------|--------|------------------|-------------|
| 🧭 **Lead** | router + `build` (staff-grade brief) | ทุก phase (orchestrate) | Workflow state + tech depth |
| 🔍 **Discover** | `plan` (discover mode) + Domain SME | Phase 0 | OKR + opportunity + domain validation |
| 📐 **Design** | `plan` (requirements mode) + `plan` (architecture mode) + `design` | Phase 1a/1b/3a | Spec + Architecture + UI artifacts |
| 🎓 **Domain** | `plan` | Phase 0/1b/3b (pluggable) | Regulation cite + business rule |
| 🛠 **Dev** | `build` (parallel `build`#N) | Phase 2 | Production code (data/ML = `build` interim จนกว่ามี dedicated agent) |
| ✅ **Verify** | `verify` (standards axis) + `verify` (runtime axis) + `secure` | Phase 3b | Code review + Test + Security |
| 🚀 **Ops** | `operate` (deploy mode) + `operate` (reliability mode) | Phase 5/6 | Deploy + SLO + Incident |

The Domain team is a `plan` spawn that loads `shode-house:domain-core` and the domain's `references/domain/<domain>.md`; the Verify team's spec axis is a separate fresh `plan` spawn.

> Dropped Eval team (Evan agent over-engineer for current scale). Bias discipline embedded in each agent prompt (ไม่มี § No-Bias ใน discipline; อย่าอ้างถึง). Eval harness is not shipped; maintainers keep it for major-release regression (offline use).
