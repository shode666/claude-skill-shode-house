---
description: "[shode-house] Init — scaffold project ใหม่. Default: interactive wizard (Aaron + Bella + tracker). `--quick <stack>`: direct Aaron Docker-first (replaces /setup-project)"
allowed-tools: Read, Write, Edit, Bash, Task, Skill, AskUserQuestion
argument-hint: '[project-name | --quick "stack description"]'
---

# /init — Project Scaffold

**Mode detection** (Oliver):

```bash
if [ -z "$ARGUMENTS" ] || [[ "$ARGUMENTS" != --quick* ]]; then
  MODE="interactive"   # Phase 1+2+3+4 (current /init wizard)
else
  MODE="quick"         # Skip Phase 1, jump to Aaron direct (replaces /setup-project)
  STACK="${ARGUMENTS#--quick }"
fi
```

## 🛡️ Phase 0 — Brownfield guard (บังคับก่อนทุก mode; ห้ามทำลายโครงสร้างเดิม)

ตรวจว่า fresh หรือ brownfield ก่อน scaffold:

```bash
# brownfield = มี git repo / manifest / source อยู่แล้ว
{ [ -d .git ] || ls package.json pyproject.toml go.mod build.gradle* Cargo.toml pom.xml 2>/dev/null | grep -q . ; } && PROJECT="brownfield" || PROJECT="fresh"
```

- **fresh** → scaffold เต็ม (Phase 2 / Mode B ตามปกติ)
- **brownfield** → **ADOPT mode (non-destructive)** — *check-first → reuse → gap-fill*:
  1. **Check ของเดิมก่อนเสมอ** (ห้ามเดา/ห้ามทับ): `harness-contract` marker มีไหม? · มี `CLAUDE.md`/`AGENTS.md` ไหม? · มี CI / test runner / pre-commit / Makefile / tracker (bd/Jira/Linear) อยู่แล้วไหม? (Glob/Grep ของจริง)
  2. **มีอยู่แล้ว → reuse + ปรับใช้** ของเขา (ไม่สร้างซ้ำ ไม่ทับ); เติมเฉพาะ **ส่วนที่ขาด**
  3. **ขาดส่วนไหน → ask** (option-style) ก่อนเพิ่ม — ไม่ auto-add; เขียนเฉพาะไฟล์ที่ยังไม่มี
  4. ไฟล์ที่จะชน → `<file>.shode-house.new` + ถาม user ก่อน merge; ไม่ auto-replace
  5. **เขียน/append section `## Harness (shode-house)` ลง project's `CLAUDE.md`** (ถ้าไม่มี CLAUDE.md ใช้ `AGENTS.md`; ไม่ทับเนื้อเดิม) — เป็นทั้ง marker + เอกสารว่า harness ทำอะไร:
     ```md
     ## Harness (shode-house) — <date>
     <!-- harness-contract -->
     - Contract: fan-out cap=<N> · retry=backoff · checkpoint=<bd|ledger> · token budget=<...>
     - Long-run: map-reduce batch subagent + idempotent resume
     - Tracker: <bd|jira|linear (reuse ของเดิม)>
     - Runner: <generated path | ยังไม่ generate (YAGNI; gen เมื่อมี long-run need)>
     - Reused: <ของเดิมที่ปรับใช้> | Added: <ส่วนที่เติม>
     ```
  6. diff preview ทุกไฟล์ + confirm ก่อน write (anti-puppet); commit แยก `chore(shode-house): adopt harness contract`

> data-loss = carve-out "ห้ามตัด/ห้ามเสี่ยง". brownfield adopt = **check ของเดิม → reuse → เติมที่ขาด → document ใน CLAUDE.md** โดยโครงสร้าง project เดิมไม่เปลี่ยน

---

## Mode A — Interactive wizard (default; no args หรือ project-name)

### Phase 1: Discover (Oliver clarify ก่อน scaffold)

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

### Phase 2: Scaffold (Aaron + Bella parallel)

> 🔴 brownfield (Phase 0) → ADOPT mode: เขียนเฉพาะไฟล์ที่ยังไม่มี; ห้ามทับของเดิม; ชน → `*.shode-house.new` + ถาม

[Aaron] รับ stack/sandbox → setup:
- Folder structure ตาม convention
- Dockerfile + docker-compose (multi-stage, non-root, healthcheck)
- Pre-commit hooks (format/lint/type/secret)
- Makefile (`make dev/test/build/deploy/worktree`)
- CI workflow (GitHub Actions / GitLab CI)
- `.env.example` + `.gitignore`
- README + CONTRIBUTING + CLAUDE.md (AI agent onboarding)
- **🔴 UI test toolchain** (auto ถ้า Q1=Web app/Full-stack monorepo): Playwright + @axe-core/playwright + visual baseline + `make ui-test/ui-baseline/ui-test-ui` + ui-test CI job (required check on main, blocks `pre-merge-ui` gate)

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

### Phase 3: Verify (Aaron — anti-puppet)

```bash
make dev                     # ต้อง up healthy
docker compose ps             # paste output
curl localhost:PORT/health   # paste 200
bd ready --json              # paste empty list (just init)
git log --oneline             # paste init commit

# 🔴 ถ้า Web app/Full-stack:
make ui-test                 # paste Playwright + axe output (sample test = 1 placeholder spec)
ls tests/e2e/                # paste folder structure
```

### Phase 4: Hand-off (Oliver)

```
[Oliver] Init เสร็จ ✅
- Project: {{PROJECT_NAME}}
- Stack: {{STACK}} | Domain: {{DOMAIN}} | Tracker: {{TRACKER}}
- Mode: {{MODE}} | Sandbox: {{SANDBOX}}

Next steps:
1. /shode-house:design-system [feature] → start first design (or --stop --estimate for proposal)
2. /shode-house:implement [feature] → if spec already exists
```

---

## Mode B — `--quick "<stack>"` (replaces /setup-project)

ตัวอย่าง: `/init --quick "FastAPI + Postgres + Redis"`

### 0. Prerequisite (Aaron)
- `brew install beads node` + `curl -LsSf https://astral.sh/uv/install.sh | sh`
- ยืนยัน `bd`, `npx`, `uv` พร้อมใช้

### 1. Mini-clarify (Aaron — 2 คำถาม เท่านั้น)
- Deploy target (VPS / ECS / K8s / Cloud Run)
- CI (GitHub Actions / GitLab / CircleCI)

### 2. Project Structure

> 🔴 brownfield (Phase 0) → ADOPT mode: ไฟล์ที่มีอยู่ห้ามทับ; เขียนเฉพาะที่ขาด + contract marker

- Folder convention ตาม stack
- Dep file (pyproject.toml/package.json/go.mod/build.gradle.kts)
- `.gitignore` + `.editorconfig` + `.dockerignore`
- Makefile (`make dev/test/build/lint`)
- Pre-commit hooks
- **`bd init`** — beads issue tracker (commit `.beads/`)
- `README.md` quickstart + `CLAUDE.md` (agent onboarding)

### 3. Dockerize
- Dockerfile multi-stage, non-root, distroless/alpine, pinned base
- docker-compose.yml — app + DB + cache + dev tool + healthcheck
- `.env.example` + local/prod profile

### 4. CI/CD
- Lint + type-check + test + build
- SAST (Semgrep) + SCA (Trivy/Grype)
- Image scan + push registry
- Deploy staging → E2E → prod (approval)

### 5. Observability
- Structured log config
- `/health` + `/ready` + `/metrics` (Prometheus)
- OpenTelemetry skeleton
- Log aggregation ready

### 6. Reverse Proxy (ถ้าต้อง)
Default: **Caddy** (auto HTTPS, simple)
- Container stack → Traefik
- Microservices ≥ 10 → Envoy
- High-throughput L4/L7 → HAProxy

### 7. Documentation
- README (quickstart, arch, env vars)
- CONTRIBUTING (branch, commit, PR)
- docs/DEPLOY.md (runbook + rollback)

---

## ⚠️ Rules (ทุก mode)

1. **Interactive mode** — บังคับ option-style ทุกคำถาม (ใช้ `AskUserQuestion`)
2. **Quick mode** — ≤ 2 clarifying questions; ที่เหลือใช้ default
3. **Docker-first** — ทุก service runnable via Docker
4. **Reproducible** — `git clone && make dev` พอ
5. **No secret in repo** → `.env` + `.env.example`
6. **Pin versions** → ไม่ใช้ `latest`
7. **Security baseline** → non-root, image scan
8. **Observability from day 1** → log/metric/trace
9. บังคับ verify (anti-puppet) — paste output จริง
10. Save config ที่ `.shode-house/config.yaml` — agent อื่น read ได้
11. **Harness contract (บังคับ establish ทุก project)** — Aaron เขียน `harness-contract` marker + ค่า (fan-out cap, retry/backoff, checkpoint via bd/ledger, token budget) ลงไฟล์ **ของ project ที่ทำงาน**: `./.shode-house/config.yaml` + section ใน project's `CLAUDE.md` (หรือ `AGENTS.md`) — เพื่อให้ Oliver Harness Contract Check เจอครั้งหน้า. Brownfield (มี repo อยู่แล้ว): non-destructive — เขียนแค่ marker ไม่ scaffold ทับ. หลักการ: plugin ดูแลแค่ contract; long/repetitive run จริง → generate runner fit stack เข้า project repo (ผ่าน dev-gate). ไม่มี need = ไม่ generate (YAGNI) แต่ contract ต้องมีเสมอ
12. ตอบภาษาเดียวกับที่ user เขียนมาล่าสุด (`shode-house-discipline` § Response Language); code/path/command/log verbatim

## Skill composition

- After `/init` → `/design-system` (start first feature design) หรือ `/automate-test` (test pyramid setup)
- After `/init` setup project → invoke `automate-test` skill ทันทีเพื่อ wire CI gate ตั้งแต่ day 1
- v3.1 merged `/setup-project` เข้ามาเป็น `--quick` mode (alias เก่ายัง work ผ่าน v3.x)
