# Team harness contract

**Contents**

- [Source of truth and host capabilities](#source-of-truth-and-host-capabilities)
- [Main owner and assignment](#main-owner-and-assignment)
- [Plan, execute, verify, triage](#plan-execute-verify-triage)
- [Expert questions versus user decisions](#expert-questions-versus-user-decisions)
- [Long-run checkpoint and uncertain effects](#long-run-checkpoint-and-uncertain-effects)
- [Beads example — only when the project's confirmed tracker is Beads](#beads-example--only-when-the-projects-confirmed-tracker-is-beads)
- [Context economy](#context-economy)
- [Design-run order](#design-run-order)

Load at engagement start/resume and before the first delegation. A harness is the
coordination contract below, not a mandatory shell runner. Native host tools or
the project's existing automation may implement it. A Markdown checkpoint supports
resumption; it does not enforce locks, keep a process alive or guarantee exactly-once
external actions. Do not claim deterministic enforcement unless tested on that host.

## Source of truth and host capabilities

On first project use, inspect existing guidance and ask once to confirm the homes
for task status/dependencies, requirements, decisions and evidence. Reuse a recorded
confirmation. Beads, Jira, Redmine or other systems are choices, not prerequisites;
Markdown is the fallback for every concern. Do not install or migrate a tracker to
make the workflow run. ใช้ source of truth ที่ user ระบุไว้แล้ว; ถ้ายังไม่ยืนยันถามครั้งเดียวพร้อม Markdown fallback.
ไม่มี `harness-contract` marker ไม่ใช่เหตุให้หยุดหรือบังคับ `/init`; reuse ของเดิมและเติมเฉพาะ context ที่ขาดในขอบเขตที่อนุญาต ไม่สร้าง runner/config ทับ project. Preserve canonical IDs and store only pointers in other homes.
If the selected service is unavailable, mark local Markdown updates pending sync;
do not claim the remote issue changed. Reconcile before subsequent external writes.

Shared language: keep one `CONTEXT.md` (glossary only: term, meaning, where it lives
in the code, terms to avoid) in the record home. business-analyst owns it; every role reads it
when present and uses its terms in artifacts, names and reports. Create it lazily on
the first resolved term; challenge or record a conflicting term immediately. It is
never a spec or a scratch pad.

Record available file access, delegation, user-question, test and durable-record
tools. Tool names in Claude examples are not portable APIs. Use actual host tools;
never invent a Task, AskUserQuestion, Bash or Jira tool. Without delegation, report
the team-execution limitation; do not simulate independent expert sign-off. Continue
permitted preparation, but hold work whose acceptance requires the missing reviewer.
Never generate/install a runner simply to satisfy a plugin convention.

## Main owner and assignment

The router is the main session. It dispatches core AND domain roles directly, as
`shode-house:<id>`. A role needing another expert returns the requested role,
question and relevant paths to the router; no nested spawning is required. Read the selected agent's full instructions
and its declared prerequisite skills (or use verified native preloading), then only
the conditional references applicable to the task. Preserving names without loading
their knowledge is not delegation. Do not load the whole team on every request.

Assign an outcome with task ID/record, phase/iteration, input artifact revisions,
scope and non-goals, write ownership, acceptance/evidence and unresolved decisions.
Use paths accessible to the receiving context; when files are not shared, pass the
necessary excerpts explicitly and disclose their provenance. A path alone to an
inaccessible file is not a valid handoff. No full-chat copying by default.

Each expert returns status (PASS/FAIL/BLOCKED/PARTIAL), artifact and revision, checks
actually performed, findings/dissent, questions and proposed next owner. The router
checks returned artifacts against acceptance; a worker's completion message is not
an integration verdict. Reject missing evidence, stale revisions and hidden scope
changes. Preserve domain/security review when triggered; do not trade it for tokens.

## Plan, execute, verify, triage

Keep the existing software-house ownership: product-manager product; business-analyst requirements and
spec verification; solution-architect architecture; staff-engineer cross-team depth; ux-ui-designer UI; developer code/tests;
code-reviewer independent code review; qa-engineer integration; security-engineer security; domain experts
business rules; devops-engineer deployment; sre-engineer operations. Assign only relevant roles,
not all 18 for every request. Reuse approved design; design-only is not permission
to implement. An authorized 'start' continues without another command.

Verification depth follows risk, not habit. Bounded change (XS/S per routing, existing
tests, no UI, no money/auth/PII/external integration, no schema or migration): developer
implements, code-reviewer reviews; qa-engineer joins only when the change crosses a process, network
or storage boundary; business-analyst (spec axis) is dispatched on every review round; with no spec source it returns `BLOCKED: no-spec` (never SKIP); it re-reads acceptance when acceptance changed. Standard feature:
business-analyst and solution-architect light, developer, code-reviewer and qa-engineer. Multi-phase, cross-team, deployment or
migration: full runbook through the router. Triggers (UI → ux-ui-designer, business rule →
domain expert, auth/session/PII/money/external integration/webhook/file upload/AI agent → security-engineer;
canonical list = SKILL.md § Phase 1c) add roles at any tier; nothing
removes a triggered role. Record the chosen tier and reason in the checkpoint.

Pipeline phases and their evidence remain distinct. Independent assignments may
run concurrently within actual host limits; producer/consumer dependencies must wait.
Sequential reviewers can be independent actors; one actor changing role labels cannot.
Code review checks invariants and proportional SOLID/application-layer design; business-analyst
checks requirement conformity. Link overlapping findings rather than duplicate work.
UI evidence is required for UI changes, not screenshots of pure backend operations.

A blocking finding (Critical/High) must name the recorded acceptance criterion,
invariant, security criterion or demonstrated defect in changed behavior it violates.
Severity follows impact: unchanged code newly exposed can block delivery. Unrelated
findings retain severity but need separate repair authority. Unsupported hypothetical
inputs alone do not justify blocking iterations.
Route a failed finding to its owner and affected phase, not a full pipeline reset.
Revalidate affected artifacts and dependencies. A retry needs new evidence or a
changed hypothesis; repeated unchanged failure becomes a recorded blocker. Do not
close PARTIAL/BLOCKED work. Deployment and other external changes need authorization
for that action, not just a green implementation check.

Iteration cap: three review→fix iterations per task. When the cap is reached with unresolved findings, or a
finding needs a policy/scope call and no user channel exists (non-interactive run),
stop iterating: record a safety point (local commit when authorized), write the
blocker with options and a recommendation into the checkpoint, mark the task BLOCKED
or PARTIAL, and end the turn. Do not decide business policy, widen scope or add
iterations to reach green without the user.

## Expert questions versus user decisions

Read code/records first for project facts; ask the relevant expert for technical or
domain analysis. Only the router asks the user for unsettled business policy, preference,
scope or authority. Experts provide recommendations, not user permission. Bundle
questions with options, recommendation and the affected work; use the host's popup
when available or Markdown when not. Continue independent work while a decision is
pending. No silence-as-approval; no repeated file-plan approval within existing scope.
Amending an acceptance criterion is the requirements owner's call: route it to business-analyst
for a conformity re-check, or record it as a deviation with rationale and keep the
task PARTIAL until it confirms. The router does not silently rewrite AC to pass review.
In non-interactive runs, wait for dispatched workers in the foreground; never end the
turn with workers still running or their verdicts unintegrated.

## Long-run checkpoint and uncertain effects

Keep one current record in the selected home: task/phase/iteration, plugin/host/model
when known, source revision, active owners, artifacts and evidence revisions, remaining
criteria, approvals and their scope, blockers, and the next concrete action. Preserve
history by reference; never trim unresolved findings or uncertain operations for size.
At task close append a three-line retro to the checkpoint: what took longer than
expected, which iteration should not have happened, which rule or artifact to change.
It feeds the next release; it is not a ceremony and needs no user reply.

Before an external effect, record its intent, destination, stable operation key and
parameters, authorization and pending status. Afterward record the authoritative
receipt/result. A timeout or interruption is UNKNOWN, not failure or success. Resume
by reading the current checkpoint and artifacts first. Reconcile UNKNOWN operations
through authorized read-only evidence before retrying; never use a new key to bypass
uncertainty. If lookup or idempotency is unavailable, hold the affected action and
ask for the missing authority/info, not blind permission to repeat it.

Resume invalidates approvals/evidence only where scope or content changed; it does
not replay completed external actions or rerun all historical phases. Ownership
notes are not locks. Use tested host/project isolation when concurrent writes need
it; otherwise serialize. Report the actual enforcement and recovery limits.

## Beads example — only when the project's confirmed tracker is Beads

ตัวอย่างต่อไปนี้สำหรับ project ที่เลือก **beads (bd)** เท่านั้น:
```bash
bd create "..." -p1 -t feature   # create
bd ready --json                  # next unblocked
bd update <id> --notes "..."     # Beads example: progress + link to the confirmed evidence home
bd close <id> --reason "<sha> <test>"  &&  bd show <id>   # 🔴 router only (M8 close-on-done) + paste read-back; workers return evidence
```

Run stamp (at task pick) and approval record:
```bash
bd update <id> --notes "run: plugin=v<X.Y.Z> model=<agent:model,...> started=<ISO8601> branch=<branch>"
```
```bash
bd update <id> --notes "approved: gate=<gate> by=<who> at=<ISO8601> artifact=<path> sha=<git hash-object path>"
```
postmortem/dispute ที่ไม่รู้ว่ารันด้วย prompt version ไหน = สืบไม่ได้ (มัน**เป็น**ตัวแปรที่เปลี่ยนผลลัพธ์)

## Context economy

- Search source code narrowly and read relevant context. Selected role/skill instructions must still be read completely as required; do not truncate safety rules to save tokens.
- The router reuses specialist analysis, but must check returned artifacts, conflicting findings and stale evidence against acceptance; avoiding duplicate work never means blind trust.
- Use available documentation tools and primary sources; tool names are host-specific. A search snippet or link alone is not verified evidence.
- Reuse accessible artifact paths and matching revisions; provide necessary excerpts when the receiver cannot access them.

## Design-run order

Router side of the ux design run (the always-on line is the router style's "Design run" item):
- The order is a new file the router writes itself in this step. An existing order path takes the next `<NN>`; the router never hashes or dispatches a file it did not write, so the sha256 it sends is of its own bytes.
- `change_paths` = the implementer's list of changed files that `git status` also shows. The router never adds an unlisted dirty path on its own; the runner blocks it, the router relays the BLOCKED list to the user, and a path the user confirms enters `change_paths` with the user's quote as `change_confirmation`.
- `loopback_ports` come from the tracked Playwright config (`webServer.port` or the `use.baseURL` port); none → `null`.
- Relay the runner's exit-3 `BLOCKED: <token> <detail>` line verbatim to the designer or the user; compute the report sha256 yourself before relaying the report to reviewers.
- While a design run is running (until the runner's completion line or report, up to about 1,060 s), dispatch no other writer, including a Bash-holding spawn; detection after the run is best-effort and does not replace this rule (UD U3).
