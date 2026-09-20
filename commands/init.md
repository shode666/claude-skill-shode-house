---
description: "[shode-house] Init — scaffold project ใหม่. Default: interactive wizard (Aaron + Bella + tracker). `--quick <stack>`: direct Aaron Docker-first (replaces /setup-project)"
allowed-tools: Read, Write, Edit, Bash, Task, Skill, AskUserQuestion
argument-hint: '[project-name | --quick "stack description"]'
---

# /init — Project Scaffold

Apply the requested scaffold/adoption scope and actual host capabilities. Reuse
confirmed project choices and authorization; ask only for missing decisions or
new scope. The examples below do not authorize installing tools, hooks, a tracker,
or a runtime beyond that scope. Preserve existing project record homes and use
the harness checkpoint when no separate script runtime has been adopted.

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
  3. **ขาดส่วนไหน → ตรวจ scope ที่อนุญาต**: เติมส่วนที่อยู่ในคำขอได้; ถ้าเป็น scope ใหม่ให้ถามก่อน เขียนเฉพาะไฟล์ที่ยังไม่มี
  4. ไฟล์ที่จะชน → `<file>.shode-house.new` + ถาม user ก่อน merge; ไม่ auto-replace
  5. **เมื่อ scope รวมการบันทึก harness ใน project guidance** ให้ append section `## Harness (shode-house)` ลง project's `CLAUDE.md` (ถ้าไม่มีใช้ `AGENTS.md`; ไม่ทับเนื้อเดิม); มิฉะนั้นใช้ confirmed record home:
     ```md
     ## Harness (shode-house) — <date>
     <!-- harness-contract -->
     - Contract: fan-out cap=<N> · retry=backoff · checkpoint=<bd|ledger> · token budget=<...>
     - Long-run: map-reduce batch subagent + idempotent resume
     - Tracker: <bd|jira|linear (reuse ของเดิม)>
     - Runner: <generated path | ยังไม่ generate (YAGNI; gen เมื่อมี long-run need)>
     - Reused: <ของเดิมที่ปรับใช้> | Added: <ส่วนที่เติม>
     ```
  6. ตรวจ diff ทุกไฟล์; ไม่ขอ confirm ซ้ำสำหรับงานใน scope ที่อนุญาตแล้ว Commit แยก `chore(shode-house): adopt harness contract` เฉพาะเมื่อมี commit authority

> data-loss = carve-out "ห้ามตัด/ห้ามเสี่ยง". brownfield adopt = **check ของเดิม → reuse → เติมที่ขาด → document ใน CLAUDE.md** โดยโครงสร้าง project เดิมไม่เปลี่ยน

### Phase 0 — runtime ignore rule (only for an adopted script runtime)

Apply this section only when the target project explicitly uses the separate
script runtime described below. The distributed instruction-only plugin does not
ship these scripts or require this directory. Do not install a runner, change hooks,
or create runtime state to satisfy this reference. For other projects, keep the
confirmed tracker/Markdown checkpoint workflow and skip this runtime-specific step.

`.shode-house/` คือ runtime dir ที่ script ของ milestone นี้เขียน state/approval/side-effect ลงไป
(bd:shode-house-5cs.5) — ต้องมี root-anchored ignore rule ใน target project's `.gitignore` ก่อน
scaffold ต่อ ไม่งั้น approval JSON ที่ script เขียนจะโผล่เป็น untracked dirt ทุกครั้งที่ grant ใหม่
(bd:shode-house-5cs.5 iter4 root cause). Leading slash ตั้งใจ — ระบุ dir ที่ ROOT เท่านั้น ไม่ ignore
ทุก dir ชื่อนี้ทุก depth:

```bash
RUNTIME_IGNORE_RULE="/.shode-house/"

# idempotent -- รันซ้ำกี่ครั้งก็เหลือ rule ที่ effective เดียว; ไม่ทับ/reorder/reformat
# entry เดิมที่ไม่เกี่ยวข้อง; ไม่ duplicate ถ้ามี rule ที่ "เทียบเท่า" อยู่แล้วคนละ spelling
# (".shode-house/", ".shode-house", "/.shode-house" -- ต่างแค่ leading/trailing slash)
ensure_runtime_ignore_rule() {
  local gi="$1" rule="$2" core line l
  core="${rule#/}"; core="${core%/}"

  if [ ! -f "$gi" ]; then
    printf '%s\n' "$rule" > "$gi"
    return 0
  fi

  # exact spelling อยู่แล้ว -> no-op
  grep -qxF "$rule" "$gi" && return 0

  # equivalent spelling อยู่แล้ว (ต่างแค่ leading/trailing slash ของชื่อเดียวกัน) -> no-op,
  # ไม่ใช่ prefix/glob match แบบ ".shode-house/*" (นั่นคือคนละความหมาย ไม่นับเทียบเท่า)
  while IFS= read -r line || [ -n "$line" ]; do
    l="${line%/}"; l="${l#/}"
    [ "$l" = "$core" ] && return 0
  done < "$gi"

  # append ต่อท้าย ไม่แตะ entry เดิมเลย; กัน glue กับบรรทัดสุดท้ายถ้าไฟล์ไม่มี trailing newline
  if [ -s "$gi" ] && [ -n "$(tail -c1 "$gi")" ]; then
    printf '\n' >> "$gi"
  fi
  printf '%s\n' "$rule" >> "$gi"
}

ensure_runtime_ignore_rule "./.gitignore" "$RUNTIME_IGNORE_RULE"
```

- ไม่มี `.gitignore` → สร้างใหม่ด้วย rule นี้บรรทัดเดียว
- มี `.gitignore` แต่ไม่มี rule นี้ (exact หรือ equivalent spelling) → append ท้ายไฟล์ เก็บ entry เดิมไว้ครบ ไม่เรียงใหม่ ไม่ format ใหม่
- รัน `/init` ซ้ำ (fresh หรือ brownfield) → เหลือ effective rule เดียวเสมอ ไม่มี duplicate line
- เกิดก่อน Phase 2 scaffold (Aaron's `.gitignore` step ด้านล่างเติมรายการอื่นต่อจากที่นี่ ไม่ทับ)

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
- **UI test toolchain** (auto ถ้า Q1=Web app/Full-stack monorepo): Playwright + @axe-core/playwright + visual baseline + `make ui-test/ui-baseline/ui-test-ui` + ui-test CI job (required check on main, blocks `pre-merge-ui` gate)

[Bella] รับ domain → seed:
- BRD template (`outputs/brd.md`) + sample FR
- Tracker: reuse the confirmed tracker (harness contract; Markdown fallback) — no install/migrate
- Sample BR/FR/Story tracker entry
- Glossary template (ubiquitous language)

[Oliver] record confirmed engagement defaults in the selected checkpoint;
if the project explicitly adopted the script runtime, its config may be:
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
# confirmed tracker: find ready → paste list (Markdown fallback: task file)
git log --oneline             # paste init commit

# ถ้า Web app/Full-stack:
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

### 1. Mini-clarify (Aaron prepares; Oliver asks — up to 2 unresolved questions)

Aaron returns missing decisions to Oliver. Reuse confirmed answers; only Oliver
asks the user, using the host's available question channel.
- Deploy target (VPS / ECS / K8s / Cloud Run)
- CI (GitHub Actions / GitLab / CircleCI)

### 2. Project Structure

> 🔴 brownfield (Phase 0) → ADOPT mode: ไฟล์ที่มีอยู่ห้ามทับ; เขียนเฉพาะที่ขาด + contract marker

- Folder convention ตาม stack
- Dep file (pyproject.toml/package.json/go.mod/build.gradle.kts)
- `.gitignore` + `.editorconfig` + `.dockerignore`
- Makefile (`make dev/test/build/lint`)
- Pre-commit hooks
- **Tracker** — the project's confirmed tracker (harness contract); Markdown fallback under `outputs/`
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
10. Save confirmed defaults in the existing record home; `.shode-house/config.yaml` is only for an explicitly adopted script runtime.
11. **Harness contract** — establish coordination using the host tools and confirmed checkpoint described in `shode-house-workflow/harness.md`. Do not require marker/config files, hooks or a generated runner merely to satisfy the plugin. Aaron generates a project runner only for an authorized concrete runtime need; preserve brownfield structure and existing guidance.
12. ตอบภาษาเดียวกับที่ user เขียนมาล่าสุด (`shode-house-discipline` § Response Language); code/path/command/log verbatim

## Skill composition

- After `/init` → `/design-system` (start first feature design) หรือ `/automate-test` (test pyramid setup)
- After `/init` setup project → invoke `automate-test` skill ทันทีเพื่อ wire CI gate ตั้งแต่ day 1
- v3.1 merged `/setup-project` เข้ามาเป็น `--quick` mode (alias เก่ายัง work ผ่าน v3.x)
