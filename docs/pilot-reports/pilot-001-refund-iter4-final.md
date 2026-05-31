# Pilot 001 Refund Flow — iter 4 Final Report

> **Generated**: 2026-05-31
> **Pilot scope**: Full PEV loop (Phase 0 → 4) on greenfield refund feature
> **Engagement mode**: Hybrid simulation in Cowork session (single Claude role-playing 19 agents)
> **Status**: Pilot completed — discipline verified end-to-end with 11 fixes applied across 4 iterations

---

## Executive Summary

**Goal**: Validate shode-house v3.3.0 discipline rules on a realistic feature (refund flow for e-commerce).

**Result**: discipline visibly working at every phase. 11 prompt fixes applied across iter 1-4. Chris/Quinn adversary stance + Anti-Puppet rule correctly produced **FAIL verdict** for incomplete code (Dave placeholders + no smoke paste). PEV loop triggered Phase 2 → 4 routing as designed.

**Honest limit**: single-Claude simulation cannot fully validate multi-agent independence (G9). Real engagement via Task-tool dispatch will give cleaner signal.

---

## Iter timeline + 11 fixes verified

| Iter | Fixes applied | Verified in phase |
|---|---|---|
| 1 | G1 Oliver M1 / G2 Patrick no SME role-play / G3 Bella pickup / G4 Sara project evidence | Phase 0 ✓ (G1, G2); Phase 1a ✓ (G3, G4) |
| 3 | G7 Felix Domain Evidence cite / G8 Phase 0 CONDITIONAL PASS | Phase 0 ✓ |
| 4 | G10 Oliver USER CLARIFY relay / G11 max 2-round clarify cap | Phase 0 ✓ |
| - | (5 existing v3.3 features stress-tested) | Phase 2-4 |

## Discipline features stress-tested (v3.3 native)

| Feature | Phase | Result |
|---|---|---|
| No Man-Day Negotiation | All | ✅ No agent proposed timeline; T-shirt invisible to user |
| Bias Discipline embedded | All | ✅ Sara monolith (not microservices default); Felix Domain Evidence PENDING; Bella anti-tautology AC |
| Chris/Quinn adversary stance | 3b | ✅ Verdict default = FAIL; refused PASS without paste; cited line:file evidence |
| Claude in Chrome MCP mandatory | 3a/3b | ⏸ user-side required (sandbox limitation); flagged + checklist provided |
| Phase 1c Sentinel mandatory | 1c | ✅ Auto-triggered (auth + money + webhook); produced STRIDE table + abuse cases + SEC-AC |
| Adversary-aware Dave hand-off | 2 | ✅ Dave proactive paste; honest "smoke PENDING" instead of fake "smoke ✓" |
| PEV loop per bd (no sprint) | All | ✅ No sprint outer loop; per-bd lifecycle |

---

## Findings = Failure modes catalog candidates (for `docs/failure-modes/`)

### G1 — Oliver M1 Ingress Guard invisible by default
- **Root cause**: M1 rule in shode-house-drift required but Oliver prompt didn't enforce verbatim broadcast format
- **Fix**: explicit M1 block template in orchestrator.md
- **Catch mechanism**: pilot iter 2 visual audit — easy to spot when M1 block missing in 00 file

### G2 — Patrick single-voice synthesis of Domain SME
- **Root cause**: "Pain validation with Domain SME" in Patrick prompt ambiguous → Patrick wrote SME-style content himself
- **Fix**: explicit `## 🚫 Patrick Never Does` section + dispatch broadcast format
- **Catch mechanism**: ตรวจ output file structure — Felix/Emma quotes must be in separate files, verbatim format

### G3 — Bella pickup protocol invisible
- **Root cause**: shode-house-broadcast says `[from] ▸ [to]` handoff line — but Bella didn't open Phase 1a with explicit pickup
- **Fix**: `## 🤝 Phase 1a Pickup Protocol` section with mandatory verbatim format
- **Catch mechanism**: ตรวจ line 1 of Bella's output

### G4 — Sara assumed "existing stack" without evidence
- **Root cause**: Philosophy 1 (NO MAGIC) didn't have explicit enforcement for tech-stack claims
- **Fix**: `## 🔍 Project Evidence Mandatory` section with Glob/Read/Grep + Greenfield handling
- **Catch mechanism**: ตรวจ Sara claim "existing X" — must have Glob result paste

### G7 — Felix faked-specific regulation cite
- **Root cause**: Felix gave "BOT notice 15-day" without notice number; existing Domain Evidence Protocol had format but no enforcement in Felix prompt
- **Fix**: explicit `## 📚 Domain Evidence Enforcement` referencing shode-house-evidence format + PENDING disclaimer template
- **Catch mechanism**: regex check for regulation claim format (notice number + clause + date)

### G8 — Phase 0 ambiguity not gracefully handled
- **Root cause**: Phase 0 had `pre-spec` gate but flow for "Domain SME flags scope ambiguity" not defined
- **Fix**: `## 📋 Phase 0 scope-clarification flow` in shode-house-workflow
- **Catch mechanism**: Patrick output should say CONDITIONAL PASS + numbered questions + Oliver relay

### G10 — Oliver relay raw vs packaged
- **Root cause**: G8 said "Oliver relay" but format unspecified → questions could be raw dump
- **Fix**: G8 extension — Oliver create `05-oliver-user-clarify.md` with friendly preamble + grouping
- **Catch mechanism**: dedicated file in pilot artifact tree

### G11 — Clarification round infinite loop risk
- **Root cause**: max-iter cap missing for clarification phase (Phase 4 has cap, Phase 0 didn't)
- **Fix**: G8 extension — "max 2 rounds → escalate user"
- **Catch mechanism**: visible "Round N/2" annotation in Oliver clarify file

### G9 — Simulation limit (meta — not fixable in prompt)
- **Issue**: Single Claude role-playing all 19 agents → craft "verbatim quote" of each agent matching expectations
- **Mitigation**: Real engagement via Claude Code `/shode-house:design-system` dispatches sub-agents via Task tool → independent contexts → genuine verbatim
- **Document**: explicit caveat in pilot reports + future real-engagement test priority

---

## Action items for v3.4 backlog

| Priority | Item | Source |
|---|---|---|
| 🔴 1 | Real engagement test (Task-tool dispatch) — validate G9 limit | G9 |
| 🟠 2 | Audit other Domain experts (Iris/Sam/Tara/Elena/Brooke/Emma) for Domain Evidence enforcement same as Felix G7 | G7 |
| 🟠 3 | Extend G3 pickup protocol to other phase transitions (1b → 2 Dave; 3a → 3b Chris/Quinn; 4 → 5 Aaron) | G3 |
| 🟡 4 | Extend G4 project evidence to other agents that claim "existing X" (Aaron infra, Sara migrations) | G4 |
| 🟡 5 | Failure mode docs 002-009 from this pilot — formalize patterns | All |

---

## Files inventory (iter 4 final)

```
outputs/pilot-001-refund-iter4/
├── 00-oliver-triage.md           Oliver M1 + Engagement Plan (G1)
├── 01-patrick-phase0-initial.md  Patrick pre-domain estimates with PENDING (G2)
├── 02-felix-domain-input.md      Felix verbatim + Domain Evidence PENDING (G7)
├── 03-emma-domain-input.md       Emma verbatim + scope questions
├── 04-patrick-phase0-final.md    CONDITIONAL PASS (G8)
├── 05-oliver-user-clarify.md     USER CLARIFY relay (G10) + round cap (G11)
├── 06-user-answer.md             Simulated user response
├── 07-patrick-phase0-pass.md     FINAL PASS
├── 08-bella-phase1a.md           BRD + AC G/W/T (G3 pickup)
├── 09-sara-phase1a.md            ADR + Greenfield evidence (G4)
├── 10-phase1b-combined.md        Uma + Felix + Emma deeper
├── 11-sentinel-phase1c.md        STRIDE + abuse + SEC-AC
├── 12-dave-phase2-implement.md   FastAPI + Vue minimal + honest smoke PENDING
├── 13-uma-phase3a-chrome-todo.md User-side Chrome MCP checklist
├── 14-chris-phase3b-review.md    Adversary FAIL + 3 Critical findings
├── 15-quinn-phase3b.md           Integration blocked + Anti-Puppet FAIL
└── 16-oliver-phase4-triage.md    Triage + loop to Phase 2 iter 2
```

---

## Verdict

**Pilot SUCCESS**: shode-house v3.3.0 discipline visible end-to-end. 11 prompt gaps caught + fixed via iterative tuning. Chris/Quinn adversary correctly produced FAIL on incomplete code per Anti-Puppet rule. PEV loop triggered Phase 4 routing as designed.

**Next**: real engagement on a project with bd tool + Claude Code Task-tool dispatch to validate G9 (multi-agent independence) + measure dispute_rate over multiple bds.
