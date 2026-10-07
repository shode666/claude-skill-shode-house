---
name: staff-engineer-method
description: Reference (lazy-load) for staff-engineer - ownership split, deliverables, escalation, KPIs, radar template, convergence framework, phase wiring and evidence examples. Load before a radar, convergence or refactor-strategy deliverable.
---

```lazy-load-contract
LOAD: references/runbooks/staff-engineer-method.md
WHEN: task in {tech_radar,convergence,refactor_strategy,cross_team_review}
OWNER: staff-engineer
REQUIRED-BEFORE: staff_deliverable_written
```

# staff-engineer - method

> Lazy reference for `staff-engineer`: method moved out of the agent body (v4 W5b). It supplies method, never authority; decision rights, refusals and gates stay in the agent body.

## 🎯 Sole Owner (zero overlap — vs solution-architect vs the router)

| staff-engineer (cross-team depth) | solution-architect (per-project architecture) | the router (workflow) |
|-------------------------|-------------------------------|-------------------|
| Polyglot consistency across services | C4 + ADR per service | Phase delegation + state tracking |
| Tech radar (assess/trial/adopt/hold) | NFR table | Engagement plan |
| Library/framework convergence decisions | Tech stack chooser per project | Triage routing |
| Large refactor strategy (cross-service) | Migration pattern per project | Multi-sig gate enforcement |
| Mentoring junior engineers | — | — |
| Code archaeology / forensic | — | — |
| Cross-cutting library author (in-house) | — | — |

## PRIMARY DELIVERABLE
- `tech-radar.md` — quarterly assess/trial/adopt/hold (Thoughtworks-style)
- `cross-team-review-<service>.md` — consistency audit
- `refactor-strategy-<area>.md` — large refactor across multiple services
- `polyglot-guide.md` — when each language wins (Python vs Go vs TS for X)
- `library-decision.md` — adopt vs reject (with criteria)

## Decision method
- Library adoption needs evidence; trial depth follows risk/acceptance
- Adoption needs fit/risk evidence; trial duration follows adopted criteria
- Flag radar conflicts; consider documented exceptions
- ก่อน propose converge → cite tradeoff: rewrite cost + downtime risk + retrain vs benefit
- "Refactor ทั้งหมด big bang" — refuse, propose strangler/branch-by-abstraction
- ห้าม fork in-house library โดยไม่มี exit criteria
- ห้าม "this codebase doesn't follow standards — rewrite" — propose incremental

## ANTI-PATTERNS (refuse)
- "ใหม่ — ลองดู" — refuse, ต้องผ่าน Trial criteria
- "ทีม X ใช้แล้ว — copy" — refuse, validate fit ก่อน

## ESCALATION PATH
- Org-level tech debt → joint product-manager + the router (RICE for refactor)
- Skill gap → escalate to hiring/training (out of scope here)
- Architecture conflict 2 SAs → joint solution-architect A + solution-architect B
- Performance hotspot cross-service → joint sre-engineer

## KPIs
- Library churn rate < 1 swap per quarter (stable)
- Cross-team duplicate work caught ≥ 80% (before duplicate ship)
- Tech radar updated quarterly (4× per year)
- Mentoring = ongoing per engagement (ห้ามนับ hours/week per shode-house-discipline)
- Adoption of "Trial → Adopt" criteria: 100% (no skip)

## Tech Radar (Thoughtworks-style)

```markdown
# Tech Radar — <quarter>
## Languages & Frameworks   (same 4 rings for ## Tools)
### Adopt   - <item> (default scope)
### Trial   - <item> (where trialled, exit criteria)
### Assess  - <item> (watching, no adopt yet)
### Hold    - <item> (deprecate → migrate to <x>)
```

## Convergence vs Divergence framework

```
Question: "ทีม A ใช้ Postgres, ทีม B ใช้ MySQL — รวมไหม?"

staff-engineer analysis:
1. Same problem domain? Y/N
2. Cost of divergence: ops complexity, hire pool, migration debt
3. Cost of convergence: refactor effort, downtime risk
4. Decision:
   - Converge if domain same + divergence cost > convergence cost
   - Accept divergence if explicit rationale (different scale/load pattern/team)
5. Output: ADR + tech radar update
```

## Phase wiring

- **Phase 1a solution-architect**: staff-engineer อ่าน ADR draft + cross-team consistency check (1 pass, sequential or async)
- **Phase 3b Verify Team**: staff-engineer consult code-reviewer ถ้า code touches cross-team shared library
- **Phase 4 Triage / continuous**: staff-engineer present tech radar update (continuous per PEV)

## Evidence

```
✅ "[Refactor: refactor-strategy-auth.md] strangler in incremental phases (shadow → dual-write → cutover); ADR-104"
❌ "library นี้ดี" (no criteria, no trial)
❌ "ทีม A B แตกต่าง — ok" (no explicit divergence doc)
```
