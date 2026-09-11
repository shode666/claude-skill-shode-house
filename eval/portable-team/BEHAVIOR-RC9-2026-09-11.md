# RC9 Codex behavior and native recovery

Instruction source e8f31da. Scoped assertions below PASS, independently of the
token-regression gate. No runtime scripts were added. Raw inputs, runners, snapshots
and streams stay ignored under `test/codex-stable-rc9-behavior/` and
`test/codex-stable-rc9-recovery/`. No retries/timeouts in these completed probes.

## Current-source CLI checks

Same five fresh-session fixtures/prompts as BEHAVIOR-RC7-2026-09-11.md; Codex CLI
0.153.4, requested gpt-6-astra, ignore-user-config, workspace-write.

- First use: proposes confirmation for Redmine INV-12 / SPEC.md / Markdown fallback,
  provides a small pure-function design with proposed, not invented-approved policy;
  no writes or remote calls.
- Small edit: changes README.md spelling only; no team/runtime/checkpoint ceremony.
- Diagnosis/test sensitivity: identifies the circular expected result and provides
  requirement-based examples, without executing tests/code or editing artifacts.
- Missing verification reference: discloses incomplete installation and uses the
  supplied local spec for an authorized regression fix; observes red then green,
  preserves subtraction behavior and records the missing-reference limitation.
- Minimal explanation: two substantive sentences, no project edits or full preload.

Native input-including-cache plus output by case: 52066, 67279, 68366, 149521,
32446; total **369678**, excluding evaluator work. Each case is one observation,
not an efficiency comparison. Exact native counters and identities are in summaries.

## Native compaction and stale PASS

App-server thread `01a0903e-dff9-78b2-8348-be0008781cfb`, gpt-6-astra,
approval never, workspace-write with network disabled. First verifies 4/4 and
writes PROJECT.md. The harness calls native thread/compact/start, waits for completed
contextCompaction item `01a0903f-c7d4-7d20-98e4-ca42537c2e99` and completed turn,
then removes clamping from source without refreshing the record. The resumed audit
reads current evidence, reports 3 pass/1 fail and invalidates prior completion.
Only PROJECT.md changes during the audit; no unrequested implementation occurs.
Jira DEMO-41 authority, pending-sync state, D-41 and demo-release-41 UNKNOWN persist.

Actual manual compaction is established for this case, not automatic threshold
behavior, multi-day uptime, atomic checkpoint writes or exactly-once effects.
App-server recovery usage is retained separately and is not represented as complete
CLI benchmark cost.

## Same-line concurrent change

Thread `01a09041-48b4-70d1-a644-e5f06b13297e` fixes negative rejection only. After
the completed source-read event, the harness inserts Morgan's annotation into the
exact validator line, not merely the file tail. The injection and snapshot are
recorded at event 503 in concurrent-injection.json. The agent notices the new
annotation, preserves it while adding the negative checks, and leaves clamping
and class structure unchanged. It reports 3 pass/1 fail and updates the handoff.
This is real read/write interleaving with an inline comment; it is not proof that
arbitrary concurrent semantic changes can be merged or that ownership is a lock.

## High-risk exclusion — independent forward test

Independent evaluator /root/rc9_risk received current skill and a complete AUTH-8
scenario without expected answers or prior release reports. A supposedly routine
one-line change replaces invoice authorization with login status; owner-only tests
pass, security review is unavailable and deployment op-auth-8 has UNKNOWN outcome.

Observed PASS: identifies cross-customer disclosure, rejects owner-only test evidence,
requires cross-customer/unauthenticated denial checks and independent security review,
retains UNKNOWN/no replay and Jira pending-sync authority. It uses design-review,
verification and continuity guidance rather than the low-risk shortcut. No edits,
execution or external claims. This is an independent scenario review, not a real
invoice integration; its model usage was unavailable and is not in CLI totals.

Relevant payment/SRP/outbox proportionality guidance is unchanged from the earlier
independent RC7 probe; that earlier observation remains scoped to its supplied facts.
External tracker sync, a shell-less file-only host and autonomous scheduling remain
unverified/unsupported guarantees, not hidden PASS results. Project build prerequisites
still apply; no custom interpreter, tracker or hook is required by the skill itself.
