# Repo invariants, detail — plugin manifest, packaging, release

This file states no rule. The rules are in `AGENTS.md`, which is loaded on every session; each section here adds scope detail, rationale, history or examples to the section of that file named in its heading, and is meant to be read next to it. If anything here seems to differ from that file, that file is the rule. Linked from the index table there, not imported.

## Tooling for `AGENTS.md` § Validation

Prerequisites:

- **bash + jq + python3** for the gate — inline in `.github/workflows/ci.yml`, run locally with `make validate`. `jq`: `brew install jq` / `apt install jq`. The gate scripts use the python3 stdlib only; gate #27 also runs the A15 design-runner suite and the W9 eval suites (`eval/v4-security/tests`, `eval/shadow-floor/tests`, plus `eval/scenarios/core-4.0/check-freeze.sh`), which need **pytest** and **git >= 2.26** (locally `python3 -m pip install --require-hashes --only-binary :all: -r .github/requirements-ci.txt`; CI installs the same hash-pinned file after `actions/setup-python`), and without pytest `make validate` reports A15 and W9 as NOT CHECKED (red)
- **make** + **zip** for packaging (`make pack`)
- **git** + **gh CLI** for release/publish (or GitHub Actions)

Dev-loop: `make validate` is the same gate CI runs. The other targets are `make pack` (zip), `make stats` and `make skills`; publishing goes through `gh` or GitHub Actions.

## Detail for `AGENTS.md` § Plugin

**Who enforces what.** The Cowork validator rule groups two kinds of constraint. The description length and ASCII caps are enforced by Cowork only; the JSON schema does not enforce them, so `claude plugin validate` passes on a manifest that Cowork then rejects. The path-array rule and the unknown-field rule are schema rules, enforced by the CLI and by Cowork alike. CI #4 covers the caps on every push, on GitHub.

**Path arrays, by example.**

- ❌ `[{"name": "x", "path": "y", "role": "z"}]` — an array of objects; the schema rejects it.
- ✅ `"skills": ["./skills/workflow/", "./skills/ops/"]`

**Why nested buckets have to be declared.** With the field absent, the loader auto-discovers the default paths (`skills/`, `commands/`, `agents/`) one level deep only, so `skills/<bucket>/<name>/SKILL.md` is never found.

**Fields the manifest schema allows:** `name`, `version`, `description`, `author`, `homepage`, `repository`, `license`, `keywords`, `category`, `tags`, `commands`, `agents`, `skills`, `outputStyles`, `hooks`, `mcpServers`, `lspServers`, `settings`.

**The archive, by entry.** The recipe of `make pack` holds no path: it reads the list file and stops when an entry is missing. Today's entries and why each is there:

| Entry | Why |
|-------|-----|
| `.claude-plugin/plugin.json`, `LICENSE` | plugin format, licence text |
| `.claude-plugin/marketplace.json` | not read by a plugin host; kept because the archive shape that passed the Cowork drag-drop contained it |
| `agents`, `commands`, the five skill buckets, `output-styles` | discovery surface |
| `hooks`, the eight runner scripts under `scripts/` | runtime enforcement |
| `.enforcement-map.json` | `scripts/policy-check.sh` reads it at run time and stops without it |
| `references` | lazy-loaded knowledge and the data files the scripts read |

The generated tree under `plugins/shode-house` ships less on purpose (no hooks, no runner scripts, its own manifests); the test checks that it never copies a source file the archive leaves out.

**What the test counts as a pointer.** Markdown link targets, `@` imports, `README §`-style section pointers, and any path token whose first segment is a top-level name of this repository, in prose, backticks or a script. A name target projects also use is told apart from ours by existence: `tests/visual/x.png` is the reader's project, `tests/test-lock.sh` is ours. The exemptions (URLs, target-project homes such as `outputs/` and `.shode-house/`, placeholders, a short list of named lines) are declared with their reasons in `tests/test_pack_allowlist.py`.

**History.** The two releases that failed, the three manifest attempts of v3.1.0 and what to read first when validation fails again are in `docs/cowork-validator-history.md`.
