# Codex-only stable qualification (declared before RC7 trials)

The user explicitly narrowed stable support to Codex. Other hosts are experimental,
not PASS and not blockers for this support scope. Beads shode-house-5cs.21 tracks
qualification; historical failures remain immutable evidence.

RC7 removes repeated coordination/mapping prose and directs known-scope work to
affected artifacts without repeated broad inventories. It retains six instruction
files, safety/approval boundaries, progressive references and history read ordering.
Freeze exact candidate bytes and fixture hashes before starting any live batch.

## Efficiency and quality

Two distinct matched scenarios, each with three independent trials per arm:

1. Read-only inventory review: historical baseline fe639c0 versus RC7. Reuse the
   RC2 benchmark fixture/prompt unchanged. Require negative-input and clamping
   defects, proportional overengineering review, no edits or duplicate findings.
2. Two-session implementation/handoff/resume: baseline fd620f0 (RC2) versus RC7.
   First session fixes only negative-input rejection and checkpoints remaining
   clamping work. Fresh second session receives only current records/artifacts and
   completes clamping, tests and handoff. Preserve remote source authority,
   unresolved business choice and UNKNOWN external operation; no resubmission.

Baseline versions differ by scenario because the original review control predates
the ask entrypoint. Report them separately; never pool different sources/prompts.
Within each scenario, use identical non-skill inputs, Codex version, model,
settings and sandbox. Interleave B/C, C/B, B/C by trial. No selective retries or
sample extension. Record failed attempts, all turns, wall time and native usage.
The two resume sessions are one trial, not two independent samples. No delegation
in these small fixtures; whole-workflow cost includes all main sessions/retries.

Retain both existing regression metrics: total token volume (including cache) and
uncached-input plus output. Each scenario must meet median <= +3% and sample p90
<= +5% versus its control. Use the existing nearest-rank-index convention (for n=3,
p90 is max). All safety/quality assertions must pass; lower cost cannot compensate
for incomplete work or false PASS. Interrupted/unaccounted usage is UNSCORABLE.
Report latency and checkpoint growth, not monetary cost or general savings claims.

## Behavioral and recovery acceptance

Exercise CASES.md using bounded combined fixtures where their assertions coexist:
first use/design-only, minimal explanation/small edit, review boundaries and test
sensitivity, expert-versus-user decision/high-risk missing reviewer, missing
reference/no-runtime fallback, and checkpoint/source-of-truth cases. Record exact
case coverage and limitations; documentation or absence of tools is not host PASS.

Use native Codex compaction in an isolated test session and verify its completed
event before continuation. Change an artifact after old verification, retain an
UNKNOWN operation and verify the resumed agent consults current evidence rather
than repeating stale PASS. Separately inject an actual concurrent fixture edit
after the agent reads the source; require preservation/reconciliation or an explicit
blocked handoff, never blind overwrite. These are bounded probes, not guarantees
of exactly-once effects, atomic storage or enforced locks.

Static gates: portable mutation tests normal and optimized, usage collector tests,
payload link/frontmatter checks, archive integrity and exact source identity.
Only after all in-scope gates pass may the manifest be promoted from RC to stable.
Local packaging/commit is not permission to push, tag or publish.
