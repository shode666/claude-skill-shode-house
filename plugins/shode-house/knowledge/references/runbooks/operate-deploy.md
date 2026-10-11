---
name: operate-deploy
description: Reference (lazy-load) for `operate` (deploy mode) - infra choice heuristics, deploy cadence, pre-commit, Docker verify, canary, project setup, sandbox and container method, UI test scaffold, CI/CD, orchestration, IaC, deploy strategies, observability, secrets and FinOps, worktrees. Load before setup, pipeline or deploy work.
---

```lazy-load-contract
LOAD: references/runbooks/operate-deploy.md
WHEN: task in {project_setup,container,ci_cd,deploy,iac,observability}
OWNER: operate
REQUIRED-BEFORE: infra_change_written
```

# `operate` (deploy mode) - method

**Contents**

- [Infra choice heuristics (Bias Discipline detail)](#infra-choice-heuristics-bias-discipline-detail)
- [🚀 Phase 5 cadence](#-phase-5-cadence)
- [Bug prevention method (v2.2)](#bug-prevention-method-v22)
- [ขอบเขต](#ขอบเขต)
- [🌳 Git Worktree Pattern (parallel safe)](#-git-worktree-pattern-parallel-safe)
- [🧭 Routing rows](#-routing-rows)
- [Best Practices](#best-practices)
- [Mode rules carried over from the former deploy mode](#mode-rules-carried-over-from-the-former-deploy-mode)

> Lazy reference for `operate` (deploy mode): method moved out of the agent body (v4 W5b). It supplies method, never authority; deploy gates, multi-sig, migration preconditions, hard rules and safety lines stay in the agent body.

## Infra choice heuristics (Bias Discipline detail)

- ห้าม default EKS/RDS/ALB ถ้า workload = batch / low traffic / single-region (consider Fargate, Lambda, smaller tier)
- ก่อน infra propose → cite cost, ops burden, HA need, latency tolerance

## 🚀 Phase 5 cadence

`operate` (deploy mode) deploy **per ready task** (continuous) หรือ user manual batch (optional). The ordered Phase 5 process (steps 1-6, staging deploy, multi-sig, canary ramp, tag) is in the agent body.

> **v3.0 handoff**: SLO/SLI/error budget/incident/runbook/postmortem → **`operate` (reliability mode)**. `operate` (deploy mode) = "build the road"; `operate` (reliability mode) = "keep cars running". `operate` (deploy mode) handoff observability deep config (Grafana/Prom alerts) to `operate` (reliability mode)

### Per-issue Phase 2 support (`operate` (deploy mode) also)
- Env var / Dockerfile update ถ้า `build` มีของใหม่ (parallel ใน Phase 3b)
- CI ถ้ามี new test type

## Bug prevention method (v2.2)

### 1. Pre-commit hook (block bad commit)
```yaml
# .pre-commit-config.yaml
- format (ruff/biome/gofmt)
- lint strict
- type check (mypy/tsc/golangci-lint)
- secret scan (gitleaks)
- commitlint (Conventional Commits)
```

### 2. Docker Verify Protocol (after Dockerfile/compose change)
```bash
docker compose build
docker compose up -d
docker compose ps          # ทุก service "healthy" (not just "running")
curl localhost:PORT/health # → 200
# clean reproduction when required: isolated checkout + disposable test data
# → paste output as evidence
```

### 3. Canary + Auto-Rollback (risky deploy)
- Argo Rollouts / Flagger: 1% → 10% → 50% → 100%
- Auto-rollback ถ้า error rate > baseline + 0.5% หรือ p95 > SLO
- → bug กระทบ ≤ 1% user

## ขอบเขต

### 1. Project Setup
- Folder structure ตาม convention
- Dependency: **uv** (Py), **pnpm** (JS), Go modules, Gradle Kotlin DSL
- Pre-commit (lint/format/type/secret), .editorconfig, .gitignore
- Makefile: `make dev/test/build/deploy`
- Merge/rebase conflict ใน CI/infra files → `references/runbooks/resolve-merge-conflicts.md`
- README + CONTRIBUTING + CLAUDE.md

### 2. Sandbox / Container

**Sandbox provider table** — เลือกตาม use case:

| Provider | When | Note |
|----------|------|------|
| **Docker** (default) | Local dev + prod container | rootful, แต่ ecosystem ใหญ่ |
| **Podman** | Security/rootless, daemonless | Docker-compatible API, no daemon |
| **Devcontainer** | VS Code dev env | spec-based, IDE-integrated |
| **GitHub Codespaces** | Cloud dev workspace | zero-setup, แพง per hour |
| **Vercel** | Frontend preview + serverless | edge-native, lock-in |

**Dockerfile**: multi-stage, non-root (`USER 1000`), distroless/Alpine, layer cache (manifest first), pinned base (`python:3.12.5-slim`), HEALTHCHECK + tini, Trivy scan ใน CI (build secrets rule: agent body)

**docker-compose**: service per container, named volume, healthcheck + `depends_on: condition: service_healthy`, profiles dev/test/prod, `.env` (gitignore) + `.env.example`

**Templates** (พร้อม): Python (FastAPI/Django + uv), Node (Nest/Next + pnpm), Go (scratch/distroless), Spring Boot (JRE-only), Vue/React (Caddy / SSR)

### 2.5 UI Test Scaffold (v2.4 — Web project default)

```
Example toolchain:
- @playwright/test (latest stable)
- @axe-core/playwright (a11y automation)
- visual baseline tool: Chromatic (recommended) | Percy | Loki | Lost Pixel — เลือก 1

Folder convention:
tests/
├── e2e/              # Playwright spec (.spec.ts)
├── visual/           # baseline screenshot per page
├── a11y/             # axe rules + ignore list
└── fixtures/         # test data builder + page object

Makefile:
make ui-test          # Playwright headless + axe + visual diff
make ui-test-ui       # Playwright headed mode (debug)
make ui-baseline      # update visual baseline (manual review/approve)
make ui-codegen       # Playwright codegen helper

CI workflow (`.github/workflows/ui-test.yml`) — parallel job:
- ui-test job:
  - install Playwright browsers (cached)
  - run e2e + axe + visual diff
  - block merge ถ้า fail (required check)
  - upload artifact: trace.zip + screenshot/ + axe-report.html
- comment PR with diff link + summary
```

**Reverse proxy**:
| Tool | When |
|------|------|
| **Caddy** (default) | Single-app — auto HTTPS, simple, 90% case |
| Traefik | K8s/Swarm container-native — label-driven |
| Envoy | Service mesh, ≥10 services |
| HAProxy | Pure L4/L7, extreme throughput |

### 3. CI/CD

Pipeline: `lint+typecheck → unit (`verify` (standards axis)) → build → SAST+SCA (`secure`) → integration → image build+scan → push → staging → E2E → prod (approval)`

Tools: **GitHub Actions** (default), GitLab CI, **Argo CD/Flux** (GitOps for K8s)

Promotion: `dev` (auto on push) · `staging` (auto on merge main) · `uat` and `prod` approvals in the agent body.

Best: cache deps, matrix, parallel, required checks (block PR), branch protection, semantic-release

### 4. Orchestration

**Kubernetes** (when scale demands): Deployment/Service/Ingress/HPA/PDB + Helm chart + probes (liveness/readiness/startup) + resource limit + NetworkPolicy + service mesh (Istio/Linkerd) ถ้าจำเป็น

**Lightweight**: Docker Swarm, Nomad, ECS, Cloud Run, **Fly.io**, **Railway**, VPS + compose

**Edge / Serverless** (modern): Cloudflare Workers, Vercel Edge, AWS Lambda + RDS Proxy

### 5. IaC
- **Terraform** (recommended) / Pulumi (TS-based) / CDK / Ansible
- Per-env directory + shared modules
- Remote state (S3 + DynamoDB lock / TFC)
- Drift detection scheduled

### 6. Deploy Strategies (🔴)
- **Rolling**: K8s default, gradual, slow rollback
- **Blue-Green**: parallel env, instant rollback, 2× cost
- **Canary**: 1%→10%→50%→100% metric-based (Argo Rollouts, Flagger)
- **Feature flag**: deploy ≠ release

### 7. DB Migration in Prod (Expand-Contract method)
1. Expand (add nullable, dual-write)
2. Migrate (backfill + dual-read)
3. Contract (drop old)

Online DDL: `pt-online-schema-change` (MySQL), `pg_repack` (Postgres). Large backfill: batch + throttle + monitor lag

### 8. Observability
- **Metrics**: **Prometheus** + **Grafana**, RED + USE
- **Traces**: **OpenTelemetry** → Jaeger/Tempo/Datadog APM
- **Alerts**: SLO-driven, symptom-based (RED: p95 latency, error rate, throughput), error budget → PagerDuty/Opsgenie + runbook per alert
- **Errors**: **Sentry**

### 9. Secret + FinOps
- Secret rotation: Vault/AWS SM + Lambda; cert-manager + Let's Encrypt
- FinOps: tag resources, Cost Explorer/Kubecost, rightsize, spot/reserved mix

## 🌳 Git Worktree Pattern (parallel safe)

ตอน `build` ทำ parallel หรือ experiment:
```makefile
# Optional adopted workflow
worktree:
	git worktree add ../$(PROJECT)-$(feat) -b $(feat)
	cd ../$(PROJECT)-$(feat) && make dev

worktree-clean:
	git worktree remove ../$(PROJECT)-$(feat)
	git branch -d $(feat)
```
Use case: `build`#1, `build`#2 parallel implement (แต่ละคน worktree ของตัวเอง → ไม่ชน) · hotfix while feature dev · A/B implementation comparison. `operate` (deploy mode) document ใน README "How to use worktree for parallel dev"

## 🧭 Routing rows

| งาน | ใคร |
|-----|-----|
| Setup/Docker/CI/IaC/observability | `operate` (deploy mode) |
| App-level env var | `build` ระบุ + `operate` (deploy mode) expose |
| `/health` `/ready` endpoint | `build` implement, `operate` (deploy mode) probe config |
| Test ใน CI | → `verify` (runtime axis)+`verify` (standards axis) ส่ง test, `operate` (deploy mode) wire |

## Best Practices

- **Pin versions** (ห้าม `:latest`); pin lock file
- **Multi-stage Dockerfile** (image เล็กลง 80%+) · **Distroless/Alpine** (minimal attack surface)
- **Cache CI deps** (build เร็ว 5-10x) · **Fail fast in CI** (lint+type ก่อน test)
- **Cost tag** (env/team/service)


## Mode rules carried over from the former deploy mode

### 🎯 Bias Discipline
Trigger: เสนอหรือรับ infra/vendor choice. Fit ไม่ชัด → ไม่ default ตาม vendor เดิม; เสนอทางเลือกพร้อม cite แล้ว escalate → `plan` (architecture mode) (ผ่าน the router)

### Phase 5 trigger
- Multi-sig gate ผ่าน (ดูข้างล่าง)

### Phase 5 process (co-owner `operate` (reliability mode))
1. Build + image scan (Trivy/Grype) — `operate` (deploy mode) — Gate: pre-deploy-staging
2. Deploy staging — `verify` (runtime axis) smoke E2E
3. Gate: pre-deploy-uat → deploy UAT — user/QA sign-off
4. Gate: pre-deploy-prod (🔴 multi-sig v3.0):
   - `operate` (deploy mode): build green + image scan ✓
   - **`operate` (reliability mode)**: SLO baseline + runbook + rollback drill ✓
   - **`secure`**: STRIDE pass + headers ✓ + observatory ≥ A
   - **`plan` (discover mode)** (R0 only): OKR/risk approve
5. Post-deploy: health check (`operate` (deploy mode)) + SLO observation 2hr (`operate` (reliability mode)) + rollback ready
6. Tag `bd-<id>-deploy-<timestamp>` after prod stable
> Continuous delivery respects authorized deployment/batching. P0 uses the authorized incident runbook; urgency grants no authority.
- `uat` (manual approval — QA sign-off)
- `prod` (manual approval — Lead approve + change ticket)

### 🔴 Mandatory Bug Prevention (v2.2)
Docker verify: Use disposable test resources or the project's safe workflow. Preserve existing volumes; cleanup needs exact disposable targets and authority.

### SLO Alert (config → `operate` (reliability mode))
- Error budget tracking → spent budget = stop risky deploy
> Anti-puppet (sd skill): ห้าม "deployed ✅" — paste health check response + canary metric

### Project Setup
- Reuse the confirmed tracker; no mandated Beads installation/init/migration

### Sandbox / Container (provider table: lazy reference)
| Sandbox | When | Note |
| **Local (no sandbox)** | Quick experiment | risky — ห้ามใช้ใน AFK mode |

### UI Test Scaffold
Authorized web scaffold: reuse/prepare UI checks with `verify` (runtime axis). Example (lazy reference); service/dependency/protection changes need authority.
**Approval Gate `pre-merge-ui`** (`operate` (deploy mode) wires CI):
- Required check บน main branch
- Pass: Playwright green + visual approved + axe critical=0
- Fail: PR locked until fix

### Observability (rest: lazy reference)
- **Logs**: structured JSON → **Loki**/ELK/Datadog, correlation ID, PII redaction

### 🧭 Self-Routing
| Architecture decision | → `plan` (architecture mode) ก่อน |
| Security finding (infra) | `operate` (deploy mode); app-level → `secure` (code fix → `build`) |

### ข้อห้าม
- ห้าม disable monitoring เพื่อลด noise
