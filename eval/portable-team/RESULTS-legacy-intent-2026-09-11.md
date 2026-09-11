# Legacy intent compatibility slice — 2026-09-11

Tracking: shode-house-5cs.19 (partial; other entrypoints remain).

## Behavioral probe

Fresh-context delegated evaluator `/root/diagnose_authority` received the current
legacy diagnose skill, API fixture paths and a Thai diagnosis-only request. No prior
results or proposed fix were supplied. It read the code/spec and ran isolated Node
function checks (reported Node v24.20.0), detected the missing lower bound, and
returned cause/confidence with an explicit HTTP-integration limitation. Zero and
negative one returned 200 rather than expected 400. Valid boundaries and invalid
upper/fractional inputs behaved as specified. It reported no edits, tracker writes
or external operations. PASS for this bounded diagnosis-only fixture.

The evaluator started before the final compatibility headings/redaction heading
were restored; its result is evidence for the behavior-bearing rewrite, not an exact
final-snapshot replay. No multi-host or token benchmark was run. Model/usage were not
exposed in the returned evaluation. Full legacy review dispatch was NOT-RUN.

## Static validation

Initial `make validate` caught missing diagnose anchors and required headings after
the rewrite, plus a rule-conservation wording mismatch. Restored externally referenced
headings and retained explicit pinned scope with a full-file alternative. Gates were
not disabled or weakened. Final `make validate`: all 24 gates PASS.
`git diff --check`: PASS. Existing skill/command paths, registry and packaging
entrypoints retained; no new runtime scripts or dependencies added.

Static checks validate references and invariants, not end-to-end host capability
or isolation from all legacy global prompts. Full review/posting behavior remains
to be forward-tested; docs must not claim that this probe proves it.
