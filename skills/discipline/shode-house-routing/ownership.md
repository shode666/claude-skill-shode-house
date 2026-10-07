---
name: ownership
description: Reference (lazy-load) ของ `shode-house-routing` — team roster (18 agents + router style), formerly table (3.x persona → agent id), add-agent step, 7-team structure table. Owner/RACI/domain rows อยู่ใน SKILL.md root
---

```lazy-load-contract
LOAD: skills/discipline/shode-house-routing/ownership.md
WHEN: add_remove_rename_agent=true OR resolve_persona_to_agent_file_or_team=true OR team_composition_question=true
OWNER: router
REQUIRED-BEFORE: add_or_change_agent
```

# Routing — team roster & structure

## 👥 Team (18 agents = 11 core + 7 domain, plus the router)

> **Model**: inherit host/session settings by default. Agent frontmatter is a host-specific preference, not a portable model ID or permission to override the user's selection.

- **Router**: the main session under `output-styles/shode-house.md`; routes, gates, relays and closes. It is not a spawnable agent.
- **Core (11)**: staff-engineer · product-manager · business-analyst · solution-architect · ux-ui-designer · developer (parallel #N) · code-reviewer · qa-engineer · security-engineer · devops-engineer · sre-engineer
- **Domain (7, pluggable)**: fintech-expert · erp-expert · sap-expert · trading-expert · insurance-expert · booking-expert · ecommerce-expert
- Spawn every agent as `shode-house:<id>`; a bare id is served by a project agent of that name.

## Formerly

3.x records, task notes and tag prefixes used persona names. Resume them with this table; new text uses the agent id only.

| Formerly (3.x persona) | Agent id (4.0) |
|---|---|
| Oliver | router (main-session style; agent `orchestrator` retired) |
| Patrick | product-manager |
| Bella | business-analyst |
| Sara | solution-architect |
| Stan | staff-engineer |
| Sentinel | security-engineer |
| Dave | developer |
| Chris | code-reviewer |
| Quinn | qa-engineer |
| Aaron | devops-engineer |
| Uma | ux-ui-designer |
| Reggie | sre-engineer |
| Felix | fintech-expert |
| Elena | erp-expert |
| Sam | sap-expert |
| Tara | trading-expert |
| Iris | insurance-expert |
| Brooke | booking-expert |
| Emma | ecommerce-expert |

### Add agent

> Add agent: drop `agents/<name>.md` + update routing table — done

---

## 👥 Team Structure

7 teams ที่ทำงาน **parallel ภายในทีม + sequential ระหว่างทีม** (cross-team handoff = phase gate)

| Team (short) | Agents | Phase ที่ active | Deliverable |
|--------------|--------|------------------|-------------|
| 🧭 **Lead** | router + staff-engineer | ทุก phase (orchestrate) | Workflow state + tech depth |
| 🔍 **Discover** | product-manager + Domain SME | Phase 0 | OKR + opportunity + domain validation |
| 📐 **Design** | business-analyst + solution-architect + ux-ui-designer | Phase 1a/1b/3a | Spec + Architecture + UI artifacts |
| 🎓 **Domain** | fintech-expert/erp-expert/sap-expert/trading-expert/insurance-expert/booking-expert/ecommerce-expert | Phase 0/1b/3b (pluggable) | Regulation cite + business rule |
| 🛠 **Dev** | developer (parallel developer#N) | Phase 2 | Production code (data/ML = developer interim จนกว่ามี dedicated agent) |
| ✅ **Verify** | code-reviewer + qa-engineer + security-engineer | Phase 3b | Code review + Test + Security |
| 🚀 **Ops** | devops-engineer + sre-engineer | Phase 5/6 | Deploy + SLO + Incident |

> Dropped Eval team (Evan agent over-engineer for current scale). Bias discipline embedded in each agent prompt (ไม่มี § No-Bias ใน discipline; อย่าอ้างถึง). Eval harness is not shipped; maintainers keep it for major-release regression (offline use).
