# Architecture

3 มุมมองของ shode-house: **topology** (ใครคุยกับใคร) · **lifecycle** (งาน 1 bd เดินยังไง) · **enforcement** (กฎถูกบังคับยังไง ไม่ใช่แค่เขียนไว้)

source of truth ของแต่ละรูปอยู่ในไฟล์จริง — diagram นี้เป็นภาพสรุป ถ้าขัดกัน ไฟล์ชนะ:
`agents/orchestrator.md` · `skills/discipline/shode-house-routing/SKILL.md` · `skills/discipline/shode-house-workflow/SKILL.md` · `.enforcement-map.json` · `.github/workflows/ci.yml`

---

## 1. Agent topology — 19 agents / 7 teams

```mermaid
flowchart TB
    U([user]) --> O

    subgraph LEAD["🧭 Lead"]
        O["Oliver<br/>Engagement Lead<br/><i>main session</i>"]
        ST["Stan<br/>Staff Engineer"]
    end

    subgraph DISC["🔍 Discover — Phase 0"]
        PA["Patrick<br/>PM"]
    end

    subgraph DESIGN["📐 Design — 1a / 1b / 3a"]
        BE["Bella<br/>BA"]
        SA["Sara<br/>SA"]
        UM["Uma<br/>UX/UI · Design Authority"]
    end

    subgraph DOM["🎓 Domain — 0 / 1b / 3b"]
        FE["Felix<br/>Fintech"]
        EL["Elena<br/>ERP"]
        SM["Sam<br/>SAP"]
        TA["Tara<br/>Trading"]
        IR["Iris<br/>Insurance"]
        BR["Brooke<br/>Booking"]
        EM["Emma<br/>E-commerce"]
    end

    subgraph DEV["🛠 Dev — Phase 2"]
        DA["Dave #N<br/>Polyglot Dev"]
    end

    subgraph VER["✅ Verify — 3b"]
        CH["Chris<br/>Code Review"]
        QU["Quinn<br/>QA"]
        SE["Sentinel<br/>Security"]
    end

    subgraph OPS["🚀 Ops — 5 / 6"]
        AA["Aaron<br/>DevOps"]
        RE["Reggie<br/>SRE"]
    end

    O -. consult .-> ST
    O --> PA
    O --> BE & SA
    O --> UM
    O --> DA
    O --> CH & QU & SE
    O --> AA --> RE

    SA -. "business rule<br/>money / regulation" .-> DOM
    DA -. "business rule" .-> DOM
    CH & QU -. "domain axis" .-> DOM
    UM -. "design authority" .-> SA & DA & BE

    classDef lead fill:#1f2937,color:#fff,stroke:#111
    class O,ST lead
```

กติกา: **ทุก edge ผ่าน Oliver** — agent ไม่รับงานจาก user ตรง (M7) · **single-owner** ต่อ capability, เส้นประ = consult ได้แต่ห้ามผลิต deliverable แทนเจ้าของ · **งานที่แตะ business rule** บังคับผ่าน Domain expert ห้าม Sara/Dave เดา

---

## 2. Workflow lifecycle — PEV loop ต่อ 1 bd

```mermaid
stateDiagram-v2
    direction TB

    [*] --> PICK : bd claim

    state "PLAN" as PLAN {
        P0 : 0 Discovery — Patrick + Domain (conditional)
        P1a : 1a Foundation — Bella ∥ Sara
        P1b : 1b Pre-Design — Uma + Domain (conditional)
        P1c : 1c Threat Model — Sentinel (conditional)
        P0 --> P1a
        P1a --> P1b : pre-spec-expand
        P1a --> P1c
    }

    state "EXECUTE" as EXEC {
        P2 : 2 Implement — Dave (parallel by scope contract)
    }

    state "VERIFY (adversarial, verdict default = FAIL)" as VERIFY {
        P3a : 3a UI Check — Uma
        P3b : 3b Review — Chris ∥ Quinn (+ Sentinel / Domain on trigger)
        P3a --> P3b : pre-code-review
    }

    state "TRIAGE" as TRIAGE {
        P4 : 4 Oliver — iter ≤ 3
    }

    PICK --> PLAN
    PLAN --> EXEC : pre-implement / pre-implement-ui<br/>evidence = artifact paths
    EXEC --> VERIFY : pre-ui-check
    VERIFY --> TRIAGE
    TRIAGE --> EXEC : FAIL code/perf/security → iter+1
    TRIAGE --> PLAN : FAIL spec/AC → 1a · UI/design → 1b
    TRIAGE --> BLOCKED : iter > 3 → escalate user
    TRIAGE --> DONE : pre-loop-exit<br/>bd close --reason + bd show = CLOSED
    DONE --> DEPLOY : pre-deploy-staging / uat / prod (multi-sig R0)
    DEPLOY --> OPERATE : Aaron → Reggie (SLO, incident)
    OPERATE --> [*]
    BLOCKED --> [*]
```

invariant ของ transition: **ข้าม gate ไม่ได้** · ทุก gate ต้องมี evidence path ใน bd notes · approval ผูก artifact SHA — artifact เปลี่ยนหลัง approve = approval โมฆะ · "done" พูดได้คนเดียวคือ Oliver หลัง Chris+Quinn(+Uma/Sentinel) ครบ (Anti-Puppet) · **M4** user comment บน claim = FAIL by default · **M5** spec change = bd revision ห้าม Dave fix ตรง

---

## 3. Policy / enforcement architecture — กฎถูกบังคับยังไง

```mermaid
flowchart LR
    subgraph SRC["source of truth — 1 ที่ต่อกฎ"]
        direction TB
        D["skills/discipline/*<br/>preload → ถึงทุก agent ที่ต้องรู้"]
        A["agents/*.md<br/>identity · ownership · decision boundary"]
        R["references/* · runbooks<br/>lazy → โหลดเมื่อ trigger"]
        C["commands/* · output-styles/oliver.md<br/>main-session only"]
    end

    MAP[".enforcement-map.json — 22 rules<br/>rule → owner → trigger → source_of_truth<br/>→ verification → anchor"]

    subgraph CI["CI — 24 gates (make validate = ci.yml)"]
        direction TB
        G21["#21 anchor ของทุกกฎยังอยู่ใน source จริง<br/>#23 lazy-load: owner เอื้อมถึง reference"]
        G16["#16 #20 #22 budgets — preload · agent+preload · dispatch graph<br/>ratchet: ลงได้ ขึ้นไม่ได้"]
        G18["#18 tool reachability · #19 review dispatch graph<br/>#6 model single-source · #11 #12 cross-ref / path"]
        G24["#24 section refs + rule conservation<br/>กฎหายเงียบ ๆ = แดง"]
    end

    subgraph RT["runtime proof"]
        direction TB
        M1["M1 Ingress Guard — ทุก message"]
        FX["fixture eval — eval/scenarios → results/‹version›/"]
        AB["A/B: ctx0 ต่อ agent + behavioral invariants"]
        FX --> AB
    end

    MT["mutation test ทุก gate ใหม่<br/>ทำ invariant พังโดยตั้งใจ → ต้องแดง<br/>(manual, บันทึกใน CHANGELOG)"]

    SRC ==> MAP
    MAP ==> G21
    SRC ==> G16 & G18 & G24
    MAP -- "verification = fixture" --> FX
    D -- "preload" --> M1
    CI -.-> MT
```

หลักการ: **กฎที่ไม่มี owner / ไม่มี verification = ไม่มีกฎ** · **byte ที่ลด ≠ usage ที่ลด** — static budget เป็น ratchet แต่ตัวตัดสินคือ A/B runtime (`eval/`) · verification ใน map เป็นชื่อกลไกที่ตรวจได้จริง เช่น `ci:<n>` (static gate) · `fixture` (behavioral eval) · `mutation` · `close-gate` (bd close) · `output-style-test` — ดู `docs/enforcement-map.md`

---

## ที่ยังไม่มีใน architecture นี้ (roadmap)

- **E2E eval** ผ่าน command จริง (`/implement`, `/review`) — ตอนนี้ fixture วัดที่ระดับ agent เดี่ยว → Phase B
- **behavioral scorer** แบบ machine-verifiable + regression gate ใน CI → Phase B
- **routing เป็น declarative registry** (ตอนนี้อยู่ใน Markdown ของ Oliver/routing skill) → Phase C
- **workflow state machine ที่ runtime บังคับ** (ตอนนี้ state อยู่ใน bd + SESSION-STATE.md, invariant บังคับด้วย prompt) → Phase C
- **durable runtime engine** (ตอนนี้เป็น contract ใน `references/patterns/durable-agent-runtime.md` ที่ Aaron generate ตาม) → Phase D
