---
description: Setup project ใหม่ (Aaron) — Docker-first, CI/CD, ready-to-code
allowed-tools: Task, Read, Write, Edit, Grep, Glob, Bash
argument-hint: [stack, e.g. "FastAPI + Postgres + Redis"]
---

Setup project: **$ARGUMENTS**

## Pipeline

### 0. Prerequisite (Aaron)
- `brew install beads node` + `curl -LsSf https://astral.sh/uv/install.sh | sh`
- ยืนยัน `bd`, `npx`, `uv` พร้อมใช้

### 1. Clarify (Aaron)
- Stack (Python/Node/Go/Java/Kotlin)
- Framework (FastAPI/Nest/Gin/Spring/Ktor)
- Dependencies (DB/cache/queue/storage)
- Deploy target (VPS/ECS/K8s/Cloud Run)
- CI (GitHub Actions/GitLab/CircleCI)
- Monorepo vs polyrepo

### 2. Project Structure
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

## ⚠️ Rules

1. **Docker-first** — ทุก service runnable via Docker
2. **Reproducible** — `git clone && make dev` พอ
3. **No secret in repo** → `.env` + `.env.example`
4. **Pin versions** → ไม่ใช้ `latest`
5. **Security baseline** → non-root, image scan
6. **Observability from day 1** → log/metric/trace
7. ภาษาไทย; code/config อังกฤษ
