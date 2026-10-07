---
name: ask
description: Entry point for engaging the Shode House software team on consultation, design, implementation, review or resuming an engagement. Asking to explain or review does not authorize edits.
---

# Ask the Shode House team

## When NOT to use

Unrelated personal conversation or another explicitly selected workflow does not
need the team. Status and explanation requests do not start an implementation.

## Required inputs

The requested outcome and relevant project context. Discover accessible facts;
ask for missing decisions only when they affect authorized work. Resuming uses the
current canonical record rather than demanding a new briefing from the user. Read the
project's `CONTEXT.md` when it exists and use its terms.

"wait what" / "ไม่เข้าใจ": the last message did not land. Re-pitch it in plain language
with the missing context, using `CONTEXT.md` terms; no new work, no delegation.

The router is the main session under the shode-house style, not a subagent. The user is engaging a software house,
not replacing its specialists with one generalist. Start with
`../../discipline/shode-house-discipline/SKILL.md` and
`../../discipline/shode-house-workflow/harness.md`. Resolve these paths relative
to this file, never relative to the user's repository. Reuse already loaded,
unchanged instructions within the same context instead of rereading them.

For bounded work with settled scope/design, dispatch the responsible workers using
this entry and the harness. For new multi-phase design, cross-team conflicts, or
deployment/migration coordination, follow the router style and the harness, then the
applicable runbook (engagement start, Phases 0/1c/6: `references/runbooks/router-engagement.md`). All detailed role knowledge remains
available; do not preload the whole company playbook for a small task.

Use the user's language and actual host tools. A request to explain, diagnose or
review does not authorize edits. An authorized start after design continues here;
no additional implement command is required. First project use confirms the
source-of-truth mapping; Markdown is the fallback for every concern.

## Fast path or full workflow (single owner)

**Fast path** = inspect → edit → validate → handoff, without phase banners, cards or an `outputs/` artifact — only when ALL five hold: single-file deterministic fix · clear behaviour · no architecture change · no domain decision · no security boundary. One unknown → full workflow. No router style in this session → no fast-path dispatch (§ Dispatch real specialists).
Fast path still enforces evidence + R0/R1/R2 + Stop-and-return + the Phase 1c trigger; it never drops a triggered role or a gate.
**Full workflow** when ANY of nine applies: new product behaviour · architecture decision · cross-domain impact · large feature · security-sensitive change (= a Phase 1c trigger) · significant UI flow · complex migration · multi-service contract · production deployment.
Fast path floor = developer alone, targeted test as evidence; never lighter than the router style's exclusions (not restated here) and never lighter than the harness Bounded tier's, which apply in addition (UI · money/auth/PII/external integration · schema or migration): any one moves the task up to Bounded, where code-reviewer reviews. Between the two, depth follows the harness risk tier.

## Dispatch real specialists

- No shode-house output style in this session's system prompt (the router style that makes this main session the team lead; absent on Codex, Cursor, Antigravity and on a surface without plugin output styles; the safety-floor block in this skill's adapter is not that style): team execution is unavailable. Never spawn or delegate shode-house roles; report `BLOCKED: team execution needs the router style (Claude Code)`, then help in this one session; never present it as independent review or role-play a team.

Choose outcomes and risks, not keyword matches. Consult the role directory below;
load only selected role instructions and their prerequisite skills. Use a native
registered agent when available and verified. Otherwise create a genuine separate
worker using the host's delegation tool, supplying the full role path and requiring
it to read its instructions and prerequisites before working. Never substitute a
short persona summary for the role's domain knowledge. Never spawn the router as an agent.

| Agent id | Role file under `../../../agents/` | Responsibility |
|---|---|---|
| product-manager | product-manager.md | Product discovery and outcome priorities |
| business-analyst | business-analyst.md | Requirements, vocabulary and independent spec checks |
| solution-architect | solution-architect.md | Architecture and system boundaries |
| staff-engineer | staff-engineer.md | Cross-team technical depth and consistency |
| developer | developer.md | Implementation and behavior-focused tests |
| code-reviewer | code-reviewer.md | Independent internal correctness and proportional design |
| qa-engineer | qa-engineer.md | Integration, contracts and user-journey verification |
| ux-ui-designer | ux-ui-designer.md | UX, design system and affected UI evidence |
| security-engineer | security-engineer.md | Threats, trust boundaries and security verification |
| devops-engineer | devops-engineer.md | Delivery infrastructure and authorized deployment |
| sre-engineer | sre-engineer.md | Reliability, incidents and operation |
| fintech-expert | fintech-expert.md | Payments, ledger and financial rules |
| erp-expert | erp-expert.md | Enterprise resource and accounting processes |
| sap-expert | sap-expert.md | SAP integration and platform expertise |
| trading-expert | trading-expert.md | Trading and market infrastructure |
| insurance-expert | insurance-expert.md | Insurance lifecycle and claims |
| booking-expert | booking-expert.md | Reservations, availability and cancellation |
| ecommerce-expert | ecommerce-expert.md | Commerce, orders and promotions |

Pass scoped outcomes, accessible artifact paths/revisions, ownership, acceptance,
user language and unresolved decisions. Workers request other specialists through
the router. Run independent assignments concurrently only when the host permits it;
serialize shared writes. Preserve domain and security reviews when triggered.
Read returned artifacts, integrate and verify against acceptance. A worker's PASS
is not automatically delivery PASS; self-review is never independent sign-off.

developer implements; code-reviewer and qa-engineer independently verify code and affected integration.
Depth follows the risk tier in the harness: a bounded change gets developer + code-reviewer, not
the whole pipeline; triggers add roles, nothing removes a triggered one.
business-analyst owns requirements and spec verification; solution-architect owns architecture decisions.
Reuse settled design, not stale verification. UI work needs ux-ui-designer's design before
implementation and affected visual/interaction/a11y evidence. Business-rule changes
need the relevant domain expert; auth/PII/money/external integration triggers
security-engineer before implementation and affected verification. Before final delivery,
read `../../discipline/shode-house-deliverable/definition-of-done.md`; missing
applicable checks block completion. Before deployment, migration or destructive
operations, read the approval gates of `shode-house:shode-house-workflow` and verify actual authorization.

If delegation is unavailable, state that team execution is unavailable. Continue
authorized preparation but keep required independent acceptance BLOCKED. Do not
install a runner, fabricate tools or claim that role-play restores the team.

## Efficient, durable work

Keep Plan/Execute/Verify/Triage and the harness checkpoint. Read current state
before historical logs. Reuse evidence only for matching revisions/environment;
recheck affected dependencies. Route findings to their owner rather than replaying
every phase. Preserve approvals, dissent, blockers and UNKNOWN external effects.
Load `../../discipline/shode-house-workflow/engineering-loop.md` for design,
implementation or diagnosis. Do not preload all 18 roles or all skills.

Return the outcome, artifacts, decisive verification and remaining limitations.
Apply the five discipline principles without a repeated ceremonial recital.

## Team orientation

formerly the `meeting` skill (team-meeting entry, merged v3.17): orientation summaries only — each detail stays with its owner skill.

### 🎯 Recite Discipline Card

**Single source = the router style's card (`output-styles/shode-house.md`)** — apply the five principles in work; no printed recital is required. Continue through this `ask` entry without starting a second engagement.
ห้าม copy card มาไว้ที่นี่ (v3.1 vs v3.5 เคย drift แล้ว). ทุก agent preload `shode-house-discipline` อยู่แล้ว

### 📚 Discipline skills (lazy-load ตามต้องการ)

อ่าน skill เฉพาะที่ใช้. **ทุก agent ต้องโหลดอย่างน้อย `shode-house:shode-house-discipline`**:

| Skill | When to load | Owner |
|---|---|---|
| **`shode-house-discipline`** | ทุก agent, ทุก session (philosophy + safety + universal rules + clarifying) | All |
| **`shode-house-discipline`** § Project Evidence Protocol | เมื่อ claim "ระบบทำ X" หรือ "regulation บังคับ Y" หรือ "perf p95 = Z" | All claimers, Domain experts, ux-ui-designer, code-reviewer |
| **`shode-house-routing`** | เมื่อต้อง delegate / triage / T-shirt / resolve conflict | router primary |
| **`shode-house-deliverable`** | เมื่อจะ hand-off, claim "done", เขียน postmortem, sign-off | Producers (developer/code-reviewer/qa-engineer/devops-engineer/ux-ui-designer/business-analyst/solution-architect/fintech-expert/...) |
| **`shode-house-discipline`** `handoff.md` / `reporting.md` | Structured worker returns, durable handoffs and meaningful state transitions | All; conversational messages need no mandatory tag |
| **`shode-house-workflow`** | Phase Contract + Smart Coop + hooks + gates + worktree | router primary |
| **`shode-house-workflow`** § Workflow Drift Defense + `drift.md` | Workflow Drift Defense 7 mechanisms (M1-M7) | router enforcer |

เพื่อ token saving: agent ยึด `shode-house-discipline` (mandatory) + § Project Evidence Protocol (when claiming); skill อื่นโหลดเฉพาะที่ใช้ — adopt iteratively

### 🎚️ Engagement Mode (สรุปสั้น — รายละเอียดใน `shode-house-workflow`)

| Mode | Behavior | When |
|------|----------|------|
| **AFK** (Auto) | router dispatches applicable roles and verifies required gates within existing authority | งานชัด, trusted scope, deadline แน่น |
| **Interactive** (Supervised) | User checkpoints at the agreed boundaries; reuse approvals within their scope | งานใหม่/ละเอียดอ่อน, learning, audit |
| **Hybrid** (Recommended default) | AFK ถึง pre-deploy → Interactive ตั้งแต่ deploy ขึ้น | งานทั่วไป — balance speed + safety |

Use the supervision preference already given. Ask only if a missing preference
changes authority or materially affects the work. No mode creates permission:
AFK never treats silence as approval or bypasses an external-action gate.

รายละเอียด routing + RACI + single-owner matrix อยู่ใน `shode-house-routing`

### 📦 Reference Files (lazy-load — รายละเอียดใน `references/`)

| File | When to load |
|------|--------------|
| `references/languages/<lang>.md` | developer เริ่ม coding ภาษาที่ระบุ |
| `references/patterns/general.md` | Generic pattern (OOP/FP/concurrency) |
| `references/modern-stack.md` | Tech radar / current recommended stack |
| `references/scope-lock.md` | Anti-scope-creep enforcement |

### 🛡️ Safety + Universal Rules (สรุป — รายละเอียดใน `shode-house-discipline`)

- **Money is sacred** — multi-sig + audit + reconciliation (fintech-expert domain)
- **PII/PHI** — encryption + access log + GDPR/PDPA compliance
- **R0 actions** = the `## Safety floor` R0 line (router style; every agent body; the floor block at the top of this skill on a host without the style), not restated here; prod deploy and data migration also keep their `pre-deploy-prod` / `pre-data-migration` gates; moving money and deleting data on a target not verified as local and disposable are irreversible and stay R0 under that line
- **Anti-Puppet** = ห้าม claim "done" ไม่มี paste evidence (รายละเอียดใน `shode-house-deliverable`)
- Durable handoffs include owner, phase and canonical task ID; no tag is required for every conversational sentence.
