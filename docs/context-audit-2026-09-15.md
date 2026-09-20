# Context audit: first pass after 3.16.2

Scope: canonical Markdown selected by `scripts/pack-team.py`, not generated
discovery adapters or duplicate `plugins/shode-house/knowledge` copies. CSV data,
scripts and binary assets are storage costs, not assumed prompt input. Snapshot
contains 99 Markdown files and 720,512 bytes after the initial diagnose split.
The workspace contains unrelated pending edits; this is not a clean release metric.
Task status and remaining qualification live in Beads `shode-house-dyd`.

## Observations and dispositions

| File / group | Bytes at snapshot | Assessment |
|---|---:|---|
| design-intel quick-reference | 24,526 | Conditional UI reference; size alone is not startup cost. Measure actual retrieval before splitting further. |
| dev-gate core | 23,768 | High-value next inspection: stack matrix, pre-push commands and setup examples are conditional; keep TDD, safety carve-outs and gate criteria in core. |
| routing core | 17,942 | Keep role selection and trigger ownership; investigate repeated role descriptions versus full role files. Do not remove domain triggers. |
| drain | 17,593 | Mode-specific backlog work; large but not a universal preload. Preserve isolation/approval invariants. |
| orchestrator | 16,583 | Already conditionally loaded for complex work. Assess selected-run cost rather than total size alone. |
| wayfinding | 15,621 | Already a reference; inspect whether callers load it outside discovery before adding more layers. |
| product-manager | 15,038 | Shared frontier and map-trigger text repeats; canonical references may help if ownership and load timing remain explicit. |
| smart-coop | 14,778 | Review all consumers before shortening; workflow requirements can conflict across caller and reference. |
| solution-architect | 14,162 | Frontier boilerplate overlaps with the clarification runbook; architecture knowledge is not a removal target. |

Exact paragraph comparison (minimum 240 bytes) found 443-byte loading guidance in
seven domain roles, 458-byte domain-core guidance in six, a 392-byte frontier
explanation in three locations, and a 637-byte map trigger in two. These are
duplication candidates, not proven waste: each independently loaded worker may
need its own routing reminder. Removing a reminder that prevents missed prerequisite
loading is not a performance improvement. This pass inventories all shipped Markdown
and inspects selected candidates; it is not a completed semantic review of 99 files.

## Applied lazy-load change

Diagnose Steps 2–3 (minimisation, hypotheses and instrumentation) moved verbatim to
`skills/workflow/diagnose/full-investigation.md`. The core names the responsible
worker, the Full-path condition and the read-before point. A failing fast-path fix
promotes to Full and requires the reference. Redaction, the reproducible loop,
fix/regression and cleanup remain in core. The existing loop ladder was already
lazy-loaded; no second copy was introduced.

- Core: 16,607 → 13,376 bytes, reduction 3,231 bytes (19.5%).
- New reference: 3,827 bytes.
- Full-path core plus reference: 17,203 bytes, increase 596 bytes (3.6%).
- No model-token/cost saving claimed from these byte measurements.
- Regression compares the moved body exactly against tag `v3.16.2`, and package
  tests verify source/reference inclusion. These checks do not prove model selection.

## Second pass: dev-gate

Moved the eight-language tool matrix into `tool-matrix.md`, read by Dave/Chris
when choosing missing gate tooling or configuring checks. Existing verified project
commands require no matrix reload. A regression preserves all original table rows
from v3.16.2; examples are explicitly not current CLI syntax or installation authority.
TDD, security carve-outs, gate criteria and handoff remain in core.

The same inspection corrected overengineering triggers: SRP is about reasons to
change, not the word "and"; OCP does not mandate speculative interfaces; one
implementation can justify a security/testability/isolation seam. Project tooling
is reused instead of imposing pre-commit installation or enabling every lint rule.
Removed the unsupported universal 100x cost claim.

Current core is 22,211 bytes versus 23,768 in v3.16.2 (1,557 fewer; 6.6%). The
2,282-byte reference makes a full read 24,493 bytes (725 more; 3.1%). This combined
delta includes policy corrections, not just movement. As with diagnose, lazy loading
helps only when the conditional material is not needed; no runtime token claim.

Independent read-only scenario evaluation confirmed selecting the matrix for
missing-tooling design rather than an already configured project, and preserving a
single-implementation trust boundary. It found remaining type-checker, coverage and
skip/xfail wording conflicts; these were corrected. This is not live coding evidence.

## Third pass: routing

Replaced the duplicated handoff protocol with an explicit read-before pointer to
the existing broadcast skill. Role/domain routing, sole-owner and RACI tables
remain intact, with regression comparison against v3.16.2. Corrected API-only
visual evidence and parallel-only independence requirements; harness selection
still preserves triggered experts. Model overrides now respect host/user settings
instead of prescribing cross-host aliases, and adding a runtime runner requires
project opt-in. Source provenance is not authority to execute document instructions.

Core: 17,942 → 16,883 bytes (1,059 fewer; 5.9%). Broadcast already exists and is
reused when loaded; no claim of measured token savings. The explicit model-policy
migrations preserve judgment, expert ownership and verification rather than simply
exempting the removed model names from conservation checks.

Independent scenario evaluation found two remaining Beads-only directives (XL
decomposition and handoff notes); both now use the confirmed project tracker/evidence
home. Domain and security routing remained applicable in the checkout scenario;
separate sequential workers remained valid in the API-only scenario.

## Fourth pass: decomposition

Reviewed the entire decompose skill. Kept Bella/Oliver ownership, Sara interface
design, Patrick outcome ordering and Quinn test slicing. Replaced Beads command
examples with a tracker-neutral dependency example; no extra runtime is required.
Remote writes require authority, drafts remain pending sync, and AC IDs/revisions
are referenced rather than copying the full specification into every task.

Corrected four workflow hazards: slices cover relevant layers rather than inventing
UI/DB work; independently verifiable security/enabling work is valid; an empty
ready set can reflect legitimate approvals/dependencies; an interface contract
does not discharge real integration/data/security prerequisites. Independent
scenario review also exposed an unconditional drain route, now gated on eligible
ready work. No model-token saving or live delivery qualification is claimed.

## Measurement boundaries

Workflow/core and smart-coop were read in full next. Aligned AFK authority, backend
N/A gates, finding-based UI failure routing and the three-review/fix cap; a successful
third iteration may complete, unresolved findings stop. Oliver must inspect returned
artifacts instead of blindly trusting a worker to avoid duplicate analysis. Selected
instructions still require complete reading. Removed the unmeasured 40% token claim
and clarified that Oliver remains the main session for user-question relay.
Initial context gates rejected the added text; shortening historical/repeated
explanations restored passing budgets without raising their limits. Independent
scenario review identified the remaining lifecycle-table and cap-boundary conflicts;
those were corrected. These are instruction/structural checks, not live benchmarks.

Drain inspection retained the existing isolated-worker/serial-integration design,
but removed the automatic main-branch push/gate-selection snippet. Added explicit
independent review, integrated acceptance, authority, pending-sync closure and
revision-bound resume before retrying uncertain operations. Worker FIXED remains
a candidate. Ready batches now respect active-writer capacity separately from the
20-item batch limit; zero-blocker tasks and legitimately empty frontiers are valid.
Handoffs use accessible acceptance pointers or necessary excerpts, not entire chats.

Drain core grew from 17,593 to 18,614 bytes (+1,021; 5.8%) because missing safety
contracts were restored. This is not a token-saving result. The existing optional
host-specific template was aligned, not installed as a runtime. Three mock-host
tests cover capacity/empty inputs, candidate returns and null-worker blocking;
they do not prove native isolation or actual delivery performance. Full make validate
and skill frontmatter validation pass; the new Node tests were run separately.

Count discovery metadata, selected core/prerequisites, conditional references,
repeated reads and worker handoffs separately. Compare successful deliveries under
matched model/host/task conditions, including cache accounting and failure rates.
Do not optimize on total repository size, line count or a single cheapest run.
Keep all 19 role sources and all 24 skills reachable; acceptance, security controls,
authority and uncertain external effects must survive every compaction.

## Cross-layer completion pass

Full reads covered all 19 role files, 26 skill/core support files and 34 command,
output-style and general reference files. A further support-reference review checks
the conditional workflow/review material; coverage is semantic instruction review,
not certification of every historical SDK or regulatory example.

Corrected specialist user-question relay, delegated product/SRE authority, optional
browser/design tooling, deployment/commit authorization, shared review-loop limits,
incident preparation versus closure, evidence status, and tracker-neutral handoffs.
Map mode no longer abandons research workers or imposes one ticket per session;
approved downstream work can continue after decisions settle. Role knowledge and
all 19 roles/24 skills remain present. Compaction shortens repeated policy text,
not specialist ownership or critical safeguards; original budget files are unchanged.

Technical spot checks also corrected reversed SRE burn-rate arithmetic, FIFO cost
direction, IFRS17/TFRS17 effective dates, React/DOMPurify Trusted Types guidance,
axe WCAG22 coverage and misleading CSP nonce/Lighthouse timing examples. ASVS
chapter examples now identify their version and do not imply complete certification.
Primary sources are attached to the affected instructions. Domain claims still
require current applicable primary evidence before use.

The static diagnose-full scenario now includes the extracted full-investigation
reference. A regression test prevents the extraction from hiding full-path cost.

## Live policy pilot — limited evidence

Two fresh ephemeral Codex sessions evaluated the same standalone decompose scenario,
once against v3.16.2 and once against the candidate. No coding, plugin installation,
real worker delegation, external writes or delivery acceptance occurred. The prompt
described a backend refund repair, Jira write unavailability, vendor approval and
an independently testable security prerequisite.

Both respected no-UI scope, blocked dispatch and the vendor dependency, and neither
claimed remote updates. Only the candidate accepted the security prerequisite.
Its answer exposed residual wording conflicts; those were subsequently fixed, so
this pilot is evidence for its recorded snapshot, not final-checkout qualification.

| Variant | Input | Cached input | Output |
|---|---:|---:|---:|
| Baseline | 40,381 | 31,104 | 318 |
| Candidate | 40,261 | 31,104 | 252 |

One pair, ambient host configuration and cache effects do not establish token/time
savings. Precise elapsed time was not retained. Selected raw result/usage events
are in `docs/evidence/policy-pilot-2026-09-15-{baseline,candidate}.json`.
Snapshot SHA256: baseline `a00a299725556ee3a705dde2ec811ed0aceb0bcd8b58377f8ebed8973fb4fbbd`;
candidate `9c5e5461549ba9045be038f5b2c7f1c05b8f98bff67cd2be6577b46c3bef599e`.

Repeated matched delivery benchmarks and native Claude/Cursor/Antigravity trials
remain unqualified. Codex CLI readiness and a policy answer do not prove native
team delivery. Claude CLI and Antigravity.app were found; PATH absence alone is
not an installation finding. See the current protocol in `eval/RUNBOOK.md` rather
than executing its explicitly historical checkout/install examples.

## Final local verification

- Canonical instruction inventory: 100 Markdown files, 733,084 bytes (19 roles,
  24 skill cores, 23 skill support references, 34 command/output/general references).
- `make validate`: all gates pass; budget files unchanged.
- Full Python suite: 210 passed, no skips. Hypothesis was installed only in the
  temporary test virtualenv. Fixed an old absolute-path skip in the usage comparator
  test so it checks this repository rather than silently skipping on other machines.
- Optional drain mock-host suite: three tests pass, now included in CI.
- Unified candidate archive: 197 entries, integrity and exact source-payload match;
  SHA256 `33a6b6291bf6d308d9630d8703d8167e9ae80cb00720854c3fe91eea6c0cdc56`.
  The legacy root-layout archive checker is not applicable to this knowledge-root
  layout; exact unified-payload comparison and candidate tests are the checks used.
- Static contexts: consult 39,668 B; full fan-out 487,493 B; map 96,810 B;
  diagnose-full 87,030 B including its extracted investigation reference.
- No commit, push, installation, version change or release performed. The candidate
  archive is temporary test output, not a replacement published 3.16.2 artifact.

Instruction audit is closed in `shode-house-dyd.2`; bounded policy pilot in `.4`.
Repeated delivery and native-host qualification remain `.5`; the epic is not closed.
