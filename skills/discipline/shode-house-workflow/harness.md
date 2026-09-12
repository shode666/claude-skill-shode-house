# Team harness contract

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
make the workflow run. Preserve canonical IDs and store only pointers in other homes.
If the selected service is unavailable, mark local Markdown updates pending sync;
do not claim the remote issue changed. Reconcile before subsequent external writes.

Shared language: keep one `CONTEXT.md` (glossary only: term, meaning, where it lives
in the code, terms to avoid) in the record home. Bella owns it; every role reads it
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

Oliver is the main session. He dispatches core AND domain roles directly. A role
needing another expert returns the requested role, question and relevant paths to
Oliver; no nested spawning is required. Read the selected agent's full instructions
and its declared prerequisite skills (or use verified native preloading), then only
the conditional references applicable to the task. Preserving names without loading
their knowledge is not delegation. Do not load the whole team on every request.

Assign an outcome with task ID/record, phase/iteration, input artifact revisions,
scope and non-goals, write ownership, acceptance/evidence and unresolved decisions.
Use paths accessible to the receiving context; when files are not shared, pass the
necessary excerpts explicitly and disclose their provenance. A path alone to an
inaccessible file is not a valid handoff. No full-chat copying by default.

Each expert returns status (PASS/FAIL/BLOCKED/PARTIAL), artifact and revision, checks
actually performed, findings/dissent, questions and proposed next owner. Oliver
checks returned artifacts against acceptance; a worker's completion message is not
an integration verdict. Reject missing evidence, stale revisions and hidden scope
changes. Preserve domain/security review when triggered; do not trade it for tokens.

## Plan, execute, verify, triage

Keep the existing software-house ownership: Patrick product; Bella requirements and
spec verification; Sara architecture; Stan cross-team depth; Uma UI; Dave code/tests;
Chris independent code review; Quinn integration; Sentinel security; domain experts
business rules; Aaron deployment; Reggie operations. Assign only relevant roles,
not all 19 for every request. Reuse approved design; design-only is not permission
to implement. An authorized 'start' continues without another command.

Pipeline phases and their evidence remain distinct. Independent assignments may
run concurrently within actual host limits; producer/consumer dependencies must wait.
Sequential reviewers can be independent actors; one actor changing role labels cannot.
Code review checks invariants and proportional SOLID/application-layer design; Bella
checks requirement conformity. Link overlapping findings rather than duplicate work.
UI evidence is required for UI changes, not screenshots of pure backend operations.

Route a failed finding to its owner and affected phase, not a full pipeline reset.
Revalidate affected artifacts and dependencies. A retry needs new evidence or a
changed hypothesis; repeated unchanged failure becomes a recorded blocker. Do not
close PARTIAL/BLOCKED work. Deployment and other external changes need authorization
for that action, not just a green implementation check.

Iteration cap: three review→fix iterations per task. When the cap is reached, or a
finding needs a policy/scope call and no user channel exists (non-interactive run),
stop iterating: record a safety point (local commit when authorized), write the
blocker with options and a recommendation into the checkpoint, mark the task BLOCKED
or PARTIAL, and end the turn. Do not decide business policy, widen scope or add
iterations to reach green without the user.

## Expert questions versus user decisions

Read code/records first for project facts; ask the relevant expert for technical or
domain analysis. Only Oliver asks the user for unsettled business policy, preference,
scope or authority. Experts provide recommendations, not user permission. Bundle
questions with options, recommendation and the affected work; use the host's popup
when available or Markdown when not. Continue independent work while a decision is
pending. No silence-as-approval; no repeated file-plan approval within existing scope.
Amending an acceptance criterion is the requirements owner's call: route it to Bella
for a conformity re-check, or record it as a deviation with rationale and keep the
task PARTIAL until she confirms. Oliver does not silently rewrite AC to pass review.
In non-interactive runs, wait for dispatched workers in the foreground; never end the
turn with workers still running or their verdicts unintegrated.

## Long-run checkpoint and uncertain effects

Keep one current record in the selected home: task/phase/iteration, plugin/host/model
when known, source revision, active owners, artifacts and evidence revisions, remaining
criteria, approvals and their scope, blockers, and the next concrete action. Preserve
history by reference; never trim unresolved findings or uncertain operations for size.

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
