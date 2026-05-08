---
description: "[shode-house] Init wizard — interactive scaffold project ใหม่ (Aaron + Bella + tracker setup)"
allowed-tools: Read, Write, Edit, Bash, Task
argument-hint: [optional: project-name]
---

[Oliver] Init wizard เริ่มต้น scaffold project ใหม่ — option-style ทุกคำถาม (Sandcastle-inspired `sandcastle init`)

## Phase 1: Discover (Oliver clarify ก่อน scaffold)

ถาม batch 4-6 คำถาม option-style ผ่าน `AskUserQuestion`:

```
Q1: Project type?
  A) Web app (frontend + backend)
  B) API service (backend only)
  C) Mobile app (iOS/Android/cross-platform)
  D) CLI tool / library
  E) Full-stack monorepo

Q2: Primary stack?
  A) TypeScript (Next/Nest/Bun) (Recommended modern)
  B) Python (FastAPI/Django + uv)
  C) Go (Chi/Echo + sqlc)
  D) Java/Kotlin (Spring Boot)
  E) Other (specify)

Q3: Domain focus?
  A) Generic (no domain)
  B) Fintech (Felix lead)
  C) ERP/Accounting (Elena)
  D) SAP (Sam)
  E) Booking (Brooke)
  F) Insurance (Iris)
  G) Trading (Tara)
  H) E-commerce (Emma)

Q4: Tracker?
  A) beads (bd) (Recommended local)
  B) GitHub Issues
  C) Linear
  D) Jira
  E) Asana

Q5: Engagement mode default?
  A) Hybrid (Recommended) — AFK pre-deploy + Interactive deploy
  B) AFK — full auto, R0 only ask
  C) Interactive — every hand-off ask

Q6: Sandbox?
  A) Docker (default)
  B) Podman (rootless)
  C) Devcontainer (VS Code)
  D) Cloud (Codespaces/Vercel)
```

## Phase 2: Scaffold (Aaron + Bella parallel)

[Aaron] รับ stack/sandbox → setup:
- Folder structure ตาม convention
- Dockerfile + docker-compose (multi-stage, non-root, healthcheck)
- Pre-commit hooks (format/lint/type/secret)
- Makefile (`make dev/test/build/deploy/worktree`)
- CI workflow (GitHub Actions / GitLab CI)
- `.env.example` + `.gitignore`
- README + CONTRIBUTING + CLAUDE.md (AI agent onboarding)
- **🔴 v2.4 UI test toolchain** (auto ถ้า Q1=Web app/Full-stack monorepo): Playwright + @axe-core/playwright + visual baseline + `make ui-test/ui-baseline/ui-test-ui` + ui-test CI job (required check on main, blocks `pre-merge-ui` gate)

[Bella] รับ domain → seed:
- BRD template (`outputs/brd.md`) + sample FR
- Tracker init (`bd init` หรือ equivalent)
- Sample BR/FR/Story tracker entry
- Glossary template (ubiquitous language)

[Oliver] config engagement defaults:
- `.shode-house/config.yaml`:
  ```yaml
  mode: hybrid
  tracker: bd
  sandbox: docker
  domain: fintech
  stack: typescript
  ```

## Phase 3: Verify (Aaron — anti-puppet)

```bash
make dev                     # ต้อง up healthy
docker compose ps             # paste output
curl localhost:PORT/health   # paste 200
bd ready --json              # paste empty list (just init)
git log --oneline             # paste init commit

# 🔴 v2.4 — ถ้า Web app/Full-stack:
make ui-test                 # paste Playwright + axe output (sample test = 1 placeholder spec)
ls tests/e2e/                # paste folder structure
```

## Phase 4: Hand-off (Oliver)

```
[Oliver] Init เสร็จ ✅
- Project: {{PROJECT_NAME}}
- Stack: {{STACK}} | Domain: {{DOMAIN}} | Tracker: {{TRACKER}}
- Mode: {{MODE}} | Sandbox: {{SANDBOX}}

Next steps:
1. /shode-house:design-system [feature] → start first design
2. /shode-house:spec-only [feature] → spec-only mode
3. /shode-house:implement [feature] → if spec already exists
```

## ⚠️ Rules

- บังคับ option-style ทุกคำถาม (ใช้ `AskUserQuestion`)
- บังคับ verify (anti-puppet) — paste output จริง
- Save config ที่ `.shode-house/config.yaml` — agent อื่น read ได้
- ภาษาไทย + technical term อังกฤษ
