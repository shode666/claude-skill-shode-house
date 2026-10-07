---
name: business-analyst-method
description: Reference (lazy-load) for business-analyst - Phase 1a pickup and foundation, duties, best practices, AC-writing checks and routing. Load before writing BRD/FRD/AC.
---

```lazy-load-contract
LOAD: references/runbooks/business-analyst-method.md
WHEN: phase in {0,1a} AND deliverable in {brd,frd,ac,stories}
OWNER: business-analyst
REQUIRED-BEFORE: brd_or_ac_written
```

# business-analyst - method

> Lazy reference for `business-analyst`: method and catalogue moved out of the agent body (v4 W5a). It supplies method, never authority; the safety and domain rules stay in the agent body.

## AC-writing checks

- ห้าม reuse leading question — reframed AC = G/W/T ที่เป็นกลาง ไม่ฝังคำตอบที่คำถามเดิมชี้นำ
- เจอ tautology AC ("user save then save") → flag + propose 2-3 alternatives

## 🤝 Phase 1a Pickup Protocol

When Phase 0 supplied an opportunity, record its revision and relevant decisions once. Example:
```
[product-manager ▸ business-analyst : Phase 1a opportunity validated (bd-<id>) ✓]
Accepted: outputs/opportunity-<feature>.md (path)
Validated kill criteria: <bullet list — copy from Phase 0 output>
Validated OKR alignment: <%>
```

Reuse validated requirements. If Phase 0 is not applicable under the harness tier, record that reason; a missing pickup recital does not block BRD/AC. Missing required product decisions go to the router.

## 🤝 Phase 1a Foundation (v2.8 — TRUE parallel กับ solution-architect)

business-analyst and solution-architect own independent scopes. Parallelize when supported and independent;
sequential independent contexts are valid. Avoid copying intermediate conclusions.

### Pattern (Phase 1a)
1. Read the confirmed canonical task and evidence, Markdown fallback.
2. business-analyst draft (parallel กับ solution-architect): § หน้าที่ 2-7 (Event Storming ถ้า complex)
3. End of phase: **Light cross-read** (1 pass, ไม่ใช่ multi-round Coop):
   - Check FR ขัด solution-architect's ADR ไหม → ping resolve
4. Return compact evidence to the router; update the confirmed record only with authority.

### task notes format (Phase 1a — business-analyst section)
```
## BRD (business-analyst)
- FR: [count]; Story: [count]; AC: [count]
- Key risk: [1-2 line]
- Cross-ref ADR: FR-N → ADR-M aligned ✅
- Open Q: [list]
```

## หน้าที่

1. **Elicitation** — 5 Whys where useful; batch unresolved decisions, no question quota.
2. **BRD** — business objective (SMART), stakeholder (RACI), scope, success criteria
3. **FRD** — functional requirement testable + AC G-W-T
4. **User Stories** — INVEST (Independent/Negotiable/Valuable/Estimable/Small/Testable)
5. **Process Modeling** — BPMN, swim lane (as-is vs to-be) — Mermaid
6. **Event Storming** — DDD discovery
7. **RTM** — canonical record links (BR → FR → Design → Test → Code)

## 🧭 Does not own → who (Self-Routing)

| งาน | ใคร |
|-----|-----|
| Architecture/tech stack | → solution-architect |
| Domain rule ลึก | → Domain Expert validate |
| Implementation | → developer |
| Test strategy | → qa-engineer (business-analyst ส่ง AC) |
| UX flow/wireframe | → ux-ui-designer |

## Best Practices

- **5 Whys** — ขุดถึง root cause (อย่าหยุดที่ what)
- **MoSCoW** prioritize: Must / Should / Could / Won't
- **Story splitting**: by workflow step / data variation / business rule / happy vs edge path
  → แตกเป็น bd จริงเมื่อไหร่ ให้โหลด **`shode-house:decompose` skill** (tracer bullet · เกณฑ์เล็กพอหรือยัง · blocking edge ประกาศตอนสร้าง · create-then-wire 2 pass)
- **Ubiquitous language** glossary — term เดียวทั้ง project → `CONTEXT.md`
- **Visual > text** — Mermaid (BPMN/sequence/flowchart) ดีกว่า paragraph
- **Empathy-driven** — persona + JTBD ก่อน feature spec
- **Scope creep guard** — orphan FR (ไม่ link BR) = scope creep

## ข้อห้าม (business-analyst-specific)

- ห้าม technical jargon ใน BRD (ไป FRD)
- ห้ามตอบ "implement ยังไง" (ไม่ใช่งาน BA)
- ห้ามข้าม AC (testable เสมอ)
- ห้าม orphan requirement
- ห้ามข้าม persona/JTBD สำหรับ user-facing feature
