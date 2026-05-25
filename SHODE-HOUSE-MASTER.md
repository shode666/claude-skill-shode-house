# shode-house — Master Handoff (May 20, 2026)

> 1 ไฟล์รวม — current state + v2.x done + backlog + audits + risks
> เปิดอ่านไฟล์เดียวก่อนเริ่ม session ใหม่

---

# 📌 PART 1 — Current State

**Plugin**: `shode-house` v2.8.2 (Review Audit Trail — bd-native primary, no markdown duplicate)
**Workspace**: `~/development/shode-house/`
**Package**: `shode-house-v2.8.2.plugin` (157K)
**Repo**: https://github.com/shode666/claude-skill-shode-house

**Composition**:
- 15 expert agents — Uma now has **Bash** tool (critical v2.8.1 fix)
- 1 foundation skill (`meeting`) — ~45K (v2.8.1 + UX Evidence Protocol + Anti-Puppet UX/UI + 13 Universal UX/UI Quality rules)
- 8 slash commands — implement.md has auto-trigger Phase 3a detection
- Lazy-load references

## Version history summary

| Version | Date | Highlight |
|---------|------|-----------|
| 2.5.1 | May 8 | FS-inspired + Cowork validator fix |
| 2.6.0 | May 16 | Lean Credibility (Disclaimer + Domain Evidence + Reframe) |
| 2.6.1 | May 16 | UX Gate Closure (7-point Uma gate fix) |
| 2.7.0 | May 16 | Coop Workflow (3 macro-phase + loop) |
| 2.8.0 | May 17 | Smart Coop + Sprint (best-of-best lean refactor) |
| 2.8.1 | May 20 | Uma Hardened (UX teeth — Bash tool + Anti-Puppet UX + Universal UX rules) |
| **2.8.2** | **May 20** | **Review Audit Trail (bd-native primary, no markdown duplicate)** |

## v2.8.1 Uma Hardened — what changed + why

**User pain**: "Uma ทำงานแย่, UI บิด ๆ เบี้ย ๆ, verify หลัง dev ชอบหลุด ไม่ทำงาน"

**Root cause #1 ใหญ่ที่สุด**: Uma YAML ก่อนหน้านี้ไม่มี `Bash` tool → rule บอก "screenshot + diff + axe" แต่ technically ทำไม่ได้ → Uma skip silent / hallucinate ผ่าน

**8-point fix (v2.8.1)**:
1. **🔴 `Bash` tool ใน Uma YAML** — single line YAML edit, biggest impact
2. **UX Evidence Protocol** — UX claim ต้อง cite tool output (`[axe report: path]`, `[Chromatic: URL]`, `[screenshot: path]`)
3. **Anti-Puppet UX/UI extension** — ห้าม "UI ดูดี / a11y ok" — ต้อง paste Bash output (Playwright/axe/rg/manual paste)
4. **13 Universal UX/UI Quality Rules** — semantic token mandatory, 8-pt grid, focus order = visual order, contrast ≥ 4.5:1, touch ≥ 44×44, 7 atomic states, mobile-first 320px, no `tabindex>0`, no `outline:none` w/o alt, no flash w/o reduce-motion, i18n text +30%, color ≠ sole status, heading no skip
5. **Uma Phase 1b mandatory Bash baseline** — `pnpm playwright test --update-snapshots` + paste path; ห้าม placeholder
6. **Uma Phase 3a 11-step mandatory Bash invocation** — capture → diff → rg hardcoded → axe → contrast → states → content → AC bullet (ทุก step paste tool output)
7. **Dave Phase 2 screenshot mandatory** ถ้า frontend changed — ไม่มี = no hand-off Uma
8. **Auto-trigger Phase 3a detection** — implement.md Bash `git diff | grep .vue|.tsx|...` → MANDATORY Uma POST. ห้าม Oliver "skip เพราะ minor"

**Result**: Uma claim PASS ได้เฉพาะตอน paste tool output จริง; ห้าม hallucinate; Dave provide screenshot ก่อน hand-off; Oliver detect auto ห้าม skip

---

# 🎯 PART 2 — v2.8.1 (✅ DONE — May 20, 2026)

## Pending after package (user run terminal)

```bash
cd ~/development/shode-house

# clean up old packages
rm -f shode-house-v2.6.0.plugin shode-house-v2.6.1.plugin shode-house-v2.7.0.plugin shode-house-v2.8.0.plugin

# Manual one-paste:
git add -A
git commit -m "v2.8.1 Uma Hardened (Bash tool + Anti-Puppet UX + Universal UX rules)"
git tag -a v2.8.1 -m "Uma Hardened"
git push origin main && git push origin v2.8.1
gh release create v2.8.1 --title "v2.8.1 Uma Hardened" --notes-file CHANGELOG.md shode-house-v2.8.1.plugin
```

---

# 📋 PART 3 — Backlog (DO NOT implement now)

> Wait for v2.8.1 done + 2-3 real engagements (รวม frontend feature) ก่อน adopt backlog

## 🥇 Top

- **EC-3 SessionStart/End hooks** — auto-resume sprint state + iter count
- **EC-1 `.claude/research/`** — Phase 1a speedup (parallel research sub-agents)
- **EC-2 Red/Blue/Auditor security** — Phase 3b extension
- **FS-1 Guardrails Architecture** — Felix/Iris/Tara subagent role split

## 🟡 Medium

- Audit references/* (stamp May 2025 — version drift)
- Meeting skill diet (~45K → 20K via lazy-load references/agent-patterns.md)
- Sample project repo `shode-house-example/`
- Loop Iter Telemetry (bd metric — avg iter, gate bypass count)
- **🔴 v2.8.1 NEW backlog**: Uma Chrome MCP integration (live browser preview — beyond Playwright headless)
- **🔴 v2.8.1 NEW backlog**: Pre-commit hook ที่ block hardcoded color/spacing (Aaron scaffold ใน init.md)
- RAG Knowledge Skills (per domain)
- Eval Harness (golden Q&A per domain)

## ❌ NOT to adopt
- 48 agents / 182 skills (Affaan style — opposite of lean)
- Cross-harness portability — Claude Code native พอ
- Computer-use/browser-use MCPs ใน core
- Full MCP marketplace integration
- Dual deployment Cowork + Managed API

---

# 🗂️ PART 4 — Decision Notes (ตัดสินแล้ว)

- ✅ v2.5.0 → v2.5.1: description ≤ 200 chars ASCII safe (Cowork strict)
- ✅ v2.6.0: Lean Credibility ตอบ "expert ไม่รู้จริง"
- ✅ v2.6.1: UX Gate Closure ตอบ "Dave skip Uma"
- ✅ v2.7.0: Coop Workflow ตอบ "team ต้อง parallel + loop"
- ✅ v2.8.0: Smart Coop + Sprint ตอบ "best-of-best"
- ✅ **v2.8.1: Uma Hardened** ตอบ "Uma verify หลุด + UI บิด ๆ" — Bash tool + Anti-Puppet UX + Universal UX rules

---

# 📁 PART 5 — Key Files

```
shode-house/
├── .claude-plugin/
│   ├── plugin.json              # v2.8.1
│   └── marketplace.json         # v2.8.1
├── skills/meeting/SKILL.md      # ~45K — v2.8.1 + UX Evidence + Anti-Puppet UX + 13 Universal UX rules
├── agents/                       # 15 agents
│   ├── orchestrator.md          # Oliver — Smart Coop + Sprint + 10 gates
│   ├── business-analyst.md      # Bella — Phase 1a Foundation (parallel)
│   ├── solution-architect.md    # Sara (opus) — Phase 1a Foundation (parallel)
│   ├── developer.md             # Dave — bd + Phase 3a screenshot mandatory (v2.8.1)
│   ├── code-reviewer.md         # Chris — Phase 3b parallel AFTER Uma POST
│   ├── qa-engineer.md           # Quinn — Phase 3b parallel AFTER Uma POST
│   ├── devops-engineer.md       # Aaron — Phase 5 batched deploy
│   ├── ux-ui-designer.md        # 🔴 Uma — Bash tool (v2.8.1!) + Phase 1b mandatory Bash baseline + Phase 3a 11-step Bash invocation + verdict format
│   └── 7 domain experts (Felix/Iris/Tara/Elena/Sam/Brooke/Emma) — v2.6.0 AI Co-pilot persona
├── commands/                     # 8 slash commands
│   ├── design-system.md         # v2.8 Smart 3-step
│   ├── implement.md             # v2.8.1 — Step 0 auto-trigger + Step 4 Dave screenshot + Step 5 Uma 11-step
│   └── sprint.md                # v2.8 sprint mgmt
├── CHANGELOG.md                  # [2.8.1] + history
└── README.md                     # v2.8.1 badge
```

---

# ⚠️ PART 6 — Risks

1-13: ดู v2.8.0 master (ไม่เปลี่ยน)
14. **🔴 v2.8.1 — UI tool dependency** — Phase 1b/3a บังคับ Playwright + axe-cli + Chromatic. ถ้า project ยังไม่มี → init.md Phase 2 ต้อง scaffold ก่อน (Aaron already scaffold Playwright + axe). Project legacy ที่ไม่มี = Uma route ไป Aaron ก่อน
15. **🔴 v2.8.1 — Anti-Puppet enforcement** — rule บนกระดาษ; Uma อาจยังเขียน "PASS" โดย skip Bash. ต้อง real engagement ตรวจ + Oliver enforce verdict format mandatory paste

---

# 🚀 PART 7 — Quick Reference

## เริ่ม session ใหม่

```
อ่าน /Users/shode/development/SHODE-HOUSE-MASTER.md
แล้วทำ [task]
```

## v2.8.1 — Tasks ที่สั่งได้

**Immediate**:
- terminal รัน `git commit + tag + push + gh release` ตาม Part 2
- drag `shode-house-v2.8.1.plugin` install Cowork
- เปิด session ใหม่ → test frontend feature (Uma ใช้ Bash จริงไหม?)

**Real engagement**:
1. `/sprint pre` — Pre-Sprint planning
2. `/design-system bd-<id>` — Phase 1a (Bella ∥ Sara) → Phase 1b (Uma + Domain)
   - Uma: paste `pnpm playwright test --update-snapshots` baseline path
3. `/implement bd-<id>` — Phase 2 → 3a (Uma 11-step Bash) → 3b → 4 Triage
   - Dave: paste screenshot path ถ้า frontend
   - Oliver: Bash `git diff` auto-detect frontend trigger
4. `/sprint close` — deploy + retro

**Backlog**:
- "ทำ EC-3 SessionStart/End hooks"
- "ทำ Loop Iter Telemetry"
- "ทำ EC-1 .claude/research/"
- "ทำ pre-commit hook block hardcoded color/spacing"

---

# 📚 PART 8 — Audit Sources

- Anthropic FS: https://github.com/anthropics/financial-services
- Affaan everything-claude-code: https://github.com/affaan-m/everything-claude-code
- dev-flow.md (user-provided, May 17 — inspired v2.8.0 Sprint+Smart Coop)
- User real engagement feedback (May 20 — Uma ทำงานแย่ → inspired v2.8.1 Uma Hardened)

---

*Generated: May 8, 2026 — single-file master handoff*
*Updated: May 20, 2026 — v2.8.1 Uma Hardened shipped*
