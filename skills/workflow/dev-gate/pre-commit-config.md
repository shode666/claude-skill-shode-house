---
name: pre-commit-config
description: Reference (lazy-load) ของ `dev-gate` — .pre-commit-config.yaml ตัวอย่างเต็มสำหรับ Python และ TS/JS + setup steps
---

# Pre-commit config (reference)

> แยกจาก `SKILL.md` เป็น config ที่ copy ไปใช้ตอน setup project ครั้งเดียว ไม่ใช่สิ่งที่ต้องอ่านทุกครั้งที่เขียน code

ติดตั้ง `pre-commit` ([pre-commit.com](https://pre-commit.com)) + `.pre-commit-config.yaml`:

```yaml
# .pre-commit-config.yaml — Python project example
repos:
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.6.0
    hooks:
      - id: ruff-format         # Gate 1
      - id: ruff                # Gate 2+3+4 (--fix organize+unused+lint)
        args: [--fix, --exit-non-zero-on-fix]
  - repo: https://github.com/pre-commit/mirrors-mypy
    rev: v1.11.0
    hooks:
      - id: mypy                # Gate 5
        args: [--strict]
  - repo: https://github.com/pycqa/bandit
    rev: 1.7.9
    hooks:
      - id: bandit              # Gate 9
        args: [-c, pyproject.toml]
  - repo: https://github.com/gitleaks/gitleaks
    rev: v8.18.4
    hooks:
      - id: gitleaks            # Gate 9 secret scan
```

```yaml
# .pre-commit-config.yaml — TS/JS project example
repos:
  - repo: https://github.com/biomejs/pre-commit
    rev: v0.5.0
    hooks:
      - id: biome-check         # Gate 1+2+3+4 (format + imports + unused + lint)
        args: [--apply]
  - repo: local
    hooks:
      - id: tsc
        name: TypeScript strict
        entry: npx tsc --noEmit --strict
        language: system
        types: [ts]
      - id: ts-unused-exports
        name: Unused exports
        entry: npx ts-unused-exports tsconfig.json
        language: system
        pass_filenames: false
  - repo: https://github.com/gitleaks/gitleaks
    rev: v8.18.4
    hooks:
      - id: gitleaks
```

**Setup steps**:
```bash
pip install pre-commit              # หรือ brew install pre-commit
pre-commit install                  # ติด git hook
pre-commit run --all-files          # รัน lint ทั้ง repo ครั้งแรก
```

ทุก `git commit` จะถูก block ถ้า gate ใด fail. ห้าม `--no-verify` (bypass) ใน production code

---
