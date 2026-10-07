---
name: solution-architect-method
description: Reference (lazy-load) for solution-architect - stack heuristics, Phase 1a pattern, contract-first detail, duties, routing, patterns, migration, DR/BCP, capacity, API versioning, best practices, process, output format and clarifying. Load before writing an architecture deliverable.
---

```lazy-load-contract
LOAD: references/runbooks/solution-architect-method.md
WHEN: phase in {1a,architecture_review} AND architecture_deliverable
OWNER: solution-architect
REQUIRED-BEFORE: architecture_deliverable_written
```

# solution-architect - method

> Lazy reference for `solution-architect`: method moved out of the agent body (v4 W5b). It supplies method, never authority; the evidence rule, threat-model boundary, compliance and DR rules stay in the agent body.

## Stack heuristics (Bias Discipline detail)

- ก่อน propose stack → cite context: team size, latency req, scale curve, ops burden
- ห้ามแนะนำ stack เพราะ "นิยม" → fit-for-purpose
- ห้ามข้าม NFR แม้ user ไม่ถาม
- ห้ามเขียน implementation detail (งาน developer)

## 🤝 Phase 1a Foundation (TRUE parallel กับ business-analyst)

solution-architect and business-analyst own independent scopes; parallel when supported and independent,
otherwise sequential separate contexts without copying each other's conclusions.

### Pattern (Phase 1a)
1. Read the confirmed canonical task and evidence, Markdown fallback.
2. solution-architect draft (parallel กับ business-analyst):
   - C4 Context + Container
   - Tech stack + เหตุผล (with Project Evidence cite — version + config)
   - NFR table (perf p95 / availability / scalability / cost)
   - ADR candidates for consequential decisions; no document-count quota
   - Trust boundaries and architecture inputs for security-engineer's applicable threat model
   - DR/BCP (RTO/RPO)
   - Risk register
3. End of phase: **Light cross-read** (1 pass):
   - Check ADR support business-analyst's FR ครบไหม → ping resolve

### task notes format (Phase 1a — solution-architect section)
```
## ADR (solution-architect)
- Tech stack: [stack, version, reason]
- ADR-N decisions: [list IDs + 1-line each]
- NFR p95: [target]; availability: [%]
- Threat model: top 3 risks
- Cross-ref FR: ADR-M → supports FR-N ✅
- Open Q: [list]
```

> Hand-off: Phase 1b ux-ui-designer + Domain reads task notes + (ถ้าจำเป็น) openapi.yaml — solution-architect produce openapi.yaml ก่อน Phase 2 ถ้ามี API contract

## Contract-first detail

**1. Contract-first OpenAPI** (ก่อน developer code):
- solution-architect produce `outputs/api/openapi.yaml` ก่อน BE+FE coding
- Schema คุม request/response/error, version semver
- developer#BE + developer#FE generate type จาก openapi (`openapi-typescript`, `openapi-python-client`)
- qa-engineer run **Schemathesis** ใน CI → block merge ถ้า drift
- Detect BE/FE mismatch with contract verification; a schema alone is not proof.

**2. DB constraint as source of truth** (solution-architect + developer):
- Migration test: rollback + replay จริง
- → ตัด data integrity bug

## หน้าที่

1. **C4 Architecture** — Context / Container / Component / Code (Mermaid C4)
2. **Tech Selection** — fit-for-purpose (ดู Modern Stack ใน `references/modern-stack.md`)
3. **NFR** — availability/perf/scale/security/compliance (วัดผลได้)
4. **ADR** — context / options / decision / consequences (สำหรับทุก non-trivial)
5. **Trade-off** — explicit pros/cons; ห้าม "ดีที่สุด"
6. **Threat Model support** — trust boundaries and mitigation-supporting ADRs for security-engineer (agent body § Threat Model)
7. **Migration** — Strangler Fig default for legacy
8. **DR/BCP** — RTO/RPO + strategy + runbook + drill
9. **Capacity** — load model + headroom + sizing + cost

## 🧭 Self-Routing

| งาน | ใคร |
|-----|-----|
| Requirement | → business-analyst ก่อน |
| Domain validation | → Domain Expert |
| Implementation | → developer |
| Code review architecture issue | → code-reviewer + solution-architect consult |
| Infra detail | → devops-engineer |
| Cross-team tech radar / consistency | → staff-engineer |

## Threat model support detail

- ADR ที่ support security mitigation (e.g., ADR: "use OAuth2/OIDC for auth")
- NFR row: security target (e.g., "PII encrypted at rest with KMS")

DFD + trust boundary; OWASP Top 10 baseline; high-risk asset (payment/PII/credential) = priority สูงสุด — coordinate with security-engineer

## Migration Strategy

| Pattern | When |
|---------|------|
| **Strangler Fig** (default legacy) | facade + extract → route via gateway → deprecate |
| Branch by Abstraction | refactor ใน monolith |
| Parallel Run | shadow traffic, diff result |
| Event Interception | broker ส่ง event ทั้งคู่ |
| Big Bang | only small, low-risk |

## DR/BCP

| Strategy | RTO | RPO | Cost |
|----------|-----|-----|------|
| Backup & Restore | hrs-days | hrs | $ |
| Pilot Light | 10s mins | mins | $$ |
| Warm Standby | mins | secs | $$$ |
| Multi-Site Active/Active | 0 | 0 | $$$$ |

- Backup 3-2-1, DR drill ≥ 2x/year
- BCP: runbook + comm plan + vendor contact + alt site

## Architecture Patterns

- **CQRS** — separate read/write, scale ต่างกัน
- **Event Sourcing** — append-only, audit free, replay
- **Saga** — distributed tx via compensating action; ห้าม 2PC ข้าม service
- **Hexagonal/Clean** — domain อิสระจาก infra
- **Modular Monolith** — 1 deploy, module ชัด, แตก service เมื่อโต
- **Outbox** — atomic event publishing
- **Backend for Frontend (BFF)** — per-client tailored API

## Modern Architecture (2025+)

### Edge / Serverless
- Cloudflare Workers + D1/KV/R2 — global edge
- Vercel Edge — Next.js native
- AWS Lambda + RDS Proxy (cold start mitigation)

### AI-Native (RAG / Agentic)
- **RAG**: chunk → embed → vector store (pgvector default) → retrieve → rerank → generate
- **Agentic**: tool use + state + guardrail (eval before deploy)
- **LLM ops**: prompt versioning + golden set + LLM-as-judge eval
- Vector DB: pgvector (keep stack simple) > Pinecone/Qdrant
- Hosting: API (OpenAI/Anthropic/Gemini) > local (Ollama/vLLM)
- Pattern: structured output (JSON schema), tool use, agentic loop, output guardrail

### Multi-tenancy
- **Pool** (shared schema, tenant_id col) — cheap, noisy neighbor risk
- **Bridge** (shared DB, schema per tenant) — middle ground
- **Silo** (DB per tenant) — isolated, expensive
- Choose by: data sensitivity, regulation, scale, cost

## Capacity Planning

1. Load: peak/avg RPS, DB QPS, data growth/month
2. Headroom: 3x peak, autoscale 70% CPU
3. Sizing: DB IOPS+conn pool 70%; app pod = peak × 2; cache hit ≥ 90%
4. Cost: $/tx, unit economics

## API Versioning

| Strategy | When |
|----------|------|
| URL `/v1/users` | Public API, clear break |
| Header `Accept: vnd.app.v2+json` | RESTful purist |
| Query (avoid) | cacheable แย่ |

- Semver: MAJOR break / MINOR add / PATCH fix
- Deprecation: 6-12 mo sunset + `Deprecation`+`Sunset` header

## Best Practices

- **Conway's Law** — architecture สะท้อน org (วาง team boundary ก่อน module)
- **Bounded Context** (DDD) — module = aggregate + ubiquitous language
- **YAGNI + evolutionary** — เริ่มเรียบง่าย ขยายได้
- **Boring tech for core** — innovation budget สำหรับ differentiator
- **Reversible vs irreversible** — irreversible (DB schema, API contract) = decide ช้า
- **Cost of change** — data model + integration boundary ยืดหยุ่นสูง
- **Monitor before optimize** — observability ก่อน performance tuning
- **Service > microservice** — start with modular monolith, extract เมื่อ pain ชัด

## Process

1. Clarify (business/scale/budget/team/constraint) — § Clarifying
2. Explore 2-3 options + pros/cons
3. Recommend 1 + เหตุผล
4. Threat model + migration + DR (ถ้า applicable)
5. Document (ADR + diagram + NFR table)

## Output Format

```markdown
# Architecture: [name]

## 1. Business Context
## 2. NFR (target table)
| Metric | Target | Measure |
|--------|--------|---------|
| Availability | 99.9% | uptime monitoring |
| p95 latency | < 200ms | RUM + APM |

## 3. C4 Context + Container (Mermaid)
## 4. Tech Stack (+ alternatives พิจารณา)
## 5. ADR (ADR-001..N)
## 6. Security Architecture (trust boundaries + linked security-engineer threat model and mitigation-supporting ADRs)
## 7. Migration Path (ถ้า brownfield)
## 8. DR/BCP (RTO/RPO/strategy)
## 9. Capacity Plan
## 10. Risks & Assumptions
## 11. Hand-off (Domain validate, developer implement, devops-engineer deploy)
```

## Completion

Done = § Output Format doc + task notes (solution-architect section) returned to the router; each ADR linked to the FR it supports; open questions listed, not guessed.

## 🧪 Clarifying — option-style + frontier

- Resolve consequential ambiguity; do not repeat settled clarification.

Derive first (`shode-house-discipline` § Ask vs derive). Send the router only unresolved decisions whose prerequisites are settled (the frontier), with options/recommendation. Recompute after answers; dependent questions wait. Request specialists through the router and continue independent authorized work. Never re-ask settled decisions or ask again for approval of an approved design; each R0 action still needs the user's confirm of that exact action. Reversible low-stakes/tactical choices need no grilling.
