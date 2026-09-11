# RC2 forced-stop recovery — 2026-09-11

**PASS for one forced termination after a completed code edit.** Not partial-write,
compaction or comprehensive crash recovery acceptance. Beads: `shode-house-5cs.11.5`.
No candidate instruction changes.

## Method

Source checkout: `0f1c08707bc494a58374af10cb869507f6326fdd` (RC2).
An isolated workspace copied the six ask files, immutable inventory tests/spec,
and the real phase-1 code/checkpoint from the preceding durable-resume test.
That checkpoint authorized completing clamping and simplifying strategy indirection;
only inventory.js and PROJECT.md were writable by task scope.

Two fresh Codex CLI processes, no shared chat, no retries. The first was started
in its own process group. The maintainer harness observed its first completed
inventory.js file-change event, sent SIGKILL only to that newly created group,
and waited for the process to exit (-9). The second process started only after
the interrupted state was inspected. No evaluator edits intervened: phase-1
output hashes exactly match phase-2 input hashes.

Invocation for both: `codex exec --ignore-user-config --skip-git-repo-check
--sandbox workspace-write --json <prompt>`. Actual rollout context confirms
gpt-6-astra, effort null, approval never, workspace-write, network access false.
The harness is ignored maintainer infrastructure, not a shipped runtime requirement.

Prompts:

1. `Use ask. Resume DEMO-18 from PROJECT.md and current files. Complete its remaining authorized work and verification.`
2. `Use ask. The previous process was interrupted. Recover DEMO-18 from PROJECT.md and current files, then finish remaining authorized work and verification. Prior chat is unavailable.`

## Evidence and result

- First process reproduced the checkpoint's 3-pass/1-fail state, then implemented
  clamping. SIGKILL occurred after that completed edit, before any post-edit test
  result or checkpoint update. PROJECT.md remained byte-identical and still said
  clamping was pending. Only inventory.js changed.
- The recovery process explicitly recognized that clamping was already implemented
  despite the stale checkpoint. It compared code/test/spec hashes and ran current
  tests: 4/4 passed before further edits. It did not redo or revert clamping.
- It performed only the remaining simplification, preserved validation/export,
  obtained 4/4 again and recorded reconciliation plus completion evidence in the
  same PROJECT.md, marking old pending-work statements superseded.
- Only inventory.js and PROJECT.md changed during recovery. All tests, spec and
  six skill files retained their hashes. Inspected event traces show local reads,
  tests and permitted file edits, with no network, delegation, installs or Git
  mutations. A Git diagnostic returned 128 because the fixture has no repository.
- Evaluator independently reran `node --test inventory.test.js` after recovery:
  **4 passed, 0 failed**, exit 0, Node v24.20.0.

Interrupted code SHA-256: `b3c6b19f1afdfe56a5eb7e19857bca87fd4c3f97d63abbd45e69e48aa753970e`.
Final code SHA-256: `25532535aa2206021a9bc4f7ca5ca308281c6f1ed5b8c3d5de97a316f6486c2f`.

## Usage and limitations

Interrupted process: 31.452 s; no turn.completed usage event. Its token total is
**unavailable, not zero**. Recovery process: 66.060 s, 21,960 uncached input,
97,024 cached input, 1,496 output; total volume 120,480. Combined process wall time
97.512 s excludes evaluator work and the inspection gap. Whole-workflow token
usage is incomplete/UNSCORABLE; do not use this run to claim savings or gate PASS.

This proves recovery from an actual killed local process with a completed source
edit and stale persisted record, at one selected boundary on one host. It does
not exercise a torn write, loss of the checkpoint itself, host/OS failure, model
compaction, concurrent writers, external exactly-once effects or autonomous
checkpoint timing. The evaluator's separate ps diagnostic was sandbox-denied;
termination evidence is the harness's wait result (-9), not a process-table audit.
Full long-run and four-host gates remain open.

Ignored local evidence: `test/interrupt-rc2-2026-09-11/` contains runner, prompts,
input/output hash maps, before/after code and checkpoints, raw events and summaries.

| Phase | Thread ID | Event-stream SHA-256 |
| --- | --- | --- |
| Interrupted | `01a08fb5-3916-7722-8c02-da66eaf29294` | `c2da009c8c3ac9b8500c43a093842258b730470e3634d30934f3f97b79cecfa5` |
| Recovery | `01a08fb6-0a8c-7a23-9b53-8dadf4eb356e` | `2a52b5dcc63cdd6b93455d9c85dc7d166b8d6eade78b1b4fc3876257cd961803` |
