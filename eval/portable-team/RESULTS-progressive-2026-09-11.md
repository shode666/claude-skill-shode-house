# Progressive guidance evaluation — 2026-09-11

Scope: first portable core/reference revision, not a four-host benchmark.
Tracking: shode-house-5cs.18; remaining host trials: shode-house-5cs.15.

## Snapshot

SHA-256, files relative to `.agents/skills/shode-house-team/`:

| File | Hash |
|---|---|
| SKILL.md | 10070d64791481ab0dcf2ce3e414cace65099e0b072bea494eb448a5ad3bf7b0 |
| references/continuity.md | c10226eeb05589b1209c02d96ca7ce47d2228b33e3853bd43c47bfa2f4a05804 |
| references/decisions.md | 896378824f9897e05ec8f3388b5d11d4e460dae5d594fc488d839eeca47c6fb3 |
| references/design-review.md | e256ba7b01133e1be2016a126be5bb05832b756154d71bc0a5d0d8361bf936f3 |
| references/verification.md | 6618ba3e4a27c31f39ab92ebfa548797ba8d31307ec25fdfe5040340375b1f44 |

API fixture hashes: change.js
`e1d8cf7604d37665835c2dba33d697bb2ccfcef159a06889888b2b8ed11b8da5`;
spec.md `82a28353cd02bafbab58536ddbd68e87bd88e41c67813ac149e97f5d8b12ad0e`.

## Independent bounded review

PASS for this fixture. Codex desktop delegated agent `/root/forward_check`, fresh
context (no conversation fork), received only skill path, fixture paths and the
request to review without edits. Model/version and usage were not exposed in its
returned evidence; this is not a controlled model comparison or fresh-host install.

The evaluator reported reading core + verification + design-review only. It exercised
the exported function with Node without changing files. Negative one and zero
returned 200 rather than required 400; 1, 100, 101, 1.5, string 1 and null matched
the spec. It returned one contract finding plus a nonblocking maintainability
suggestion about the registry/strategy/engine. It explicitly limited verification
to the function, not a real HTTP integration. No external or tracker calls reported.

This supports Review authority, Split axes and Overengineering behavior for one
shared fixture, not three independent trials. New routing/vocabulary/diagnosis and
resume cases remain NOT-RUN on this revision. No token or elapsed-time saving claimed.

## Static checks and context size

- `make validate`: all 24 legacy gates PASS; these do not prove portable behavior.
- Separate Node checks: all four linked references exist; all five files have clean
  whitespace; current two-scalar frontmatter/name/description/placeholders PASS.
- `git diff --check`: PASS.
- Bundled skill-creator `quick_validate.py`: BLOCKED by missing PyYAML in both system
  and bundled Python. No dependency installed. Narrow Node checks are not a full
  YAML-validator substitute.
- Core: 10,049 -> 4,361 bytes (56.6% smaller). All five files total 15,491 bytes.
  Review path core + verification + design = 10,004 bytes, almost unchanged from
  the former core but with additional engineering guidance. Loading every reference
  is larger than before; progressive disclosure is essential, not guaranteed savings.
