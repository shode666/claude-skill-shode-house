# references/scope/ -- machine-checkable scope lock (Milestone E)

> bd: shode-roadmap/C-E1 · ROADMAP-runtime-10.md SS7 (Concurrency Safety) 7.1-7.3
> Read by `scripts/scope-check.sh` and humans only -- never preloaded into an agent
> context (no `agents/**` file and no preloaded skill points at this directory).

## Relationship to `references/scope-lock.md` (do not confuse the two)

`references/scope-lock.md` is the existing **text protocol**: an implementing agent
posts a "Scope Contract" chat message (`IN/OUT/Files/Stop/Echo`) and Oliver enforces
overlap by reading that message. It works, but it is only as strong as every agent
remembering to post it and Oliver remembering to scan for overlap -- nothing stops a
write if either step is skipped (exactly what happened in this session: three agents
were told to scope-lock by brief text alone, no script backed it up).

This directory is the **script-checkable layer underneath that same discipline**:

| | `scope-lock.md` | `references/scope/` (this dir) |
|---|---|---|
| What it is | prose protocol + template | JSON Schema + example + `scripts/scope-check.sh` |
| Enforced by | agent/Oliver reading a chat message | a script any agent, hook, or CI step can call |
| Source of truth for "Files:" | the posted Scope Contract text | a manifest translated from that same text |
| Adds | IN/OUT/Echo (human-facing scope discipline) | shared-file strategy + optimistic conflict check (7.2/7.3, not covered by scope-lock.md at all) |

They are meant to compose, not duplicate: an agent still posts the Scope Contract
(scope-lock.md, unchanged), and whoever owns the manifest for a bd (Oliver, or an
`/init`-time bootstrap step -- out of this milestone's scope) mirrors the `Files:`
field into a manifest under `.shode-house/scope/<bd-id>.json` so it becomes checkable
by script instead of by re-reading chat history.

## Files here

- `manifest.schema.json` -- JSON Schema for the manifest `scripts/scope-check.sh` reads
  (`.shode-house/scope/<bd-id with / -> -->.json` inside a project, NOT this directory).
- `example.manifest.json` -- a worked example, deliberately modeled on this very
  session's three parallel agents plus the real `ci.yml` / `eval/scenarios/golden.json`
  incident (commit `ac632a3`) via `shared_files["...ci.yml"].coupled_with`.

## Using the script

```bash
scripts/scope-check.sh <bd-id> <agent> <path>              # 7.1+7.2 ownership check
scripts/scope-check.sh <bd-id> <agent> <path> --snapshot    # 7.3 record base sha
scripts/scope-check.sh <bd-id> <agent> <path> --verify      # 7.3 optimistic conflict check
```

Exit codes: `0` ALLOW · `1` DENY · `2` NO_MANIFEST · `3` CONFLICT (`--verify` only) ·
`64` usage/dependency error. If `.shode-house/` does not exist at all, every command
exits `0` with **no stdout** (engagement guard, same convention as
`scripts/workflow-state.sh`) -- this repo/session never opted in, so the script must
never block a plain `git status`-clean checkout.

Full exit-code contract + shared-file mode semantics are documented as comments in
`scripts/scope-check.sh` itself (single source of truth for behavior; this file is the
narrative index only).
