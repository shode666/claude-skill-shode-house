---
name: ownership
description: Reference (lazy-load) ของ `shode-house-routing` — team roster 19 agents, add-agent step, 7-team structure table. Owner/RACI/domain rows อยู่ใน SKILL.md root
---

```lazy-load-contract
LOAD: skills/discipline/shode-house-routing/ownership.md
WHEN: add_remove_rename_agent=true OR resolve_persona_to_agent_file_or_team=true OR team_composition_question=true
OWNER: orchestrator
REQUIRED-BEFORE: add_or_change_agent
```

# Routing — team roster & structure

## 👥 ทีม (19 agents = 12 core + 7 domain)

> **Model**: inherit host/session settings by default. Agent frontmatter is a host-specific preference, not a portable model ID or permission to override the user's selection. Strategy + fallback: README § Model Strategy

- **Core (12)**: Oliver (orchestrate) · Stan (staff) · Patrick (PM) · Bella (BA) · Sara (SA) · Uma (UX/UI) · Dave (dev, parallel #N) · Chris (CR) · Quinn (QA) · Sentinel (security) · Aaron (DevOps) · Reggie (SRE)
- **Domain (7, pluggable)**: Felix (fintech) · Elena (ERP) · Sam (SAP) · Tara (trading) · Iris (insurance) · Brooke (booking) · Emma (e-commerce)

### Add agent

> Add agent: drop `agents/<name>.md` + update routing table — done

---

## 👥 Team Structure

7 teams ที่ทำงาน **parallel ภายในทีม + sequential ระหว่างทีม** (cross-team handoff = phase gate)

| Team (short) | Agents | Phase ที่ active | Deliverable |
|--------------|--------|------------------|-------------|
| 🧭 **Lead** | Oliver + Stan | ทุก phase (orchestrate) | Workflow state + tech depth |
| 🔍 **Discover** | Patrick + Domain SME | Phase 0 | OKR + opportunity + domain validation |
| 📐 **Design** | Bella + Sara + Uma | Phase 1a/1b/3a | Spec + Architecture + UI artifacts |
| 🎓 **Domain** | Felix/Elena/Sam/Tara/Iris/Brooke/Emma | Phase 0/1b/3b (pluggable) | Regulation cite + business rule |
| 🛠 **Dev** | Dave (parallel Dave#N) | Phase 2 | Production code (data/ML = Dave interim จนกว่ามี dedicated agent) |
| ✅ **Verify** | Chris + Quinn + Sentinel | Phase 3b | Code review + Test + Security |
| 🚀 **Ops** | Aaron + Reggie | Phase 5/6 | Deploy + SLO + Incident |

> Dropped Eval team (Evan agent over-engineer for current scale). Bias discipline embedded in each agent prompt (ไม่มี § No-Bias ใน discipline; อย่าอ้างถึง). Eval harness kept in `skills/in-progress/` for future major-release regression (maintainer offline use).
