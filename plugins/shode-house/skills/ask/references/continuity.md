## Continue across sessions

## First project use

Inspect project instructions and existing records. If no prior Shode source-of-truth
confirmation is recorded, ask the user once to confirm where task status, specs,
decisions and evidence belong, proposing what you found. Offer Markdown as the
fallback for every concern, not a mandatory tracker product. Continue useful read-only
work while waiting; do not treat silence as confirmation or create a replacement store.

After confirmation, record the mapping, canonical IDs/locations, Markdown fallback
location and confirmed decision in an existing project guidance/record location.
If none exists, propose `docs/shode-house/project.md` with records under the same
folder. Create only what the task needs, and only when writes are authorized; never
overwrite an existing file. This record is a pointer/index, not duplicated task data.
For a read-only session, return the mapping in chat and state that it was not persisted.

Markdown fallback holds progress, specs, decisions, handoff and evidence summaries;
link binary artifacts/logs rather than copying transcripts. Markdown, Jira, Redmine,
Beads or other project-selected systems are equally valid. Reuse IDs, status meanings
and update conventions; no tracker migration or competing store for convenience.
For split authority, link each concern's owner (for example Jira status, Markdown
spec, code/tests evidence). Reconfirm only authority conflicts or material changes.

Save progress in the designated task record or linked artifact location. If the
canonical system is temporarily inaccessible, preserve its ID/URL and label a local
handoff as pending synchronization, not authoritative status; do not claim a remote
update succeeded. Re-read remote state and reconcile conflicts before an authorized
sync. When the project has no convention, use the confirmed Markdown fallback rather
than installing a tracker. For read-only work without writable storage, return a compact
handoff to the user and disclose that automatic recovery is unavailable.

At a meaningful work boundary, before handoff, or when the session is nearing its
limit, update the same task record with:

- Objective/acceptance criteria and authorized scope.
- Completed artifacts and source revision, including relevant uncommitted changes.
- Verification commands/results and the snapshot/environment they apply to.
- Next concrete action, outstanding decisions, dependencies and active owners.
- Attempts already made, unresolved failures and any user-set budget remaining.
- External actions already taken, operation IDs and uncertain outcomes, if any.

Maintain one current checkpoint, updating changed facts rather than appending a
full snapshot each session. Leave unchanged facts alone; summarize verification as
command/result and snapshot/environment, linking specs/tests instead of restating
requirements, coverage lists or review narration. Keep scope/approval boundaries, source-of-truth pointers,
current evidence, next action and unresolved risks or UNKNOWN operations directly
available. Link superseded evidence and resolved history through existing durable
records. When resolved history makes the current record expensive to reread, move
it to an authorized history artifact and keep a pointer, not an inline copy. Read
history only to resolve a discrepancy or dependency.
Before removing the only copy of history, preserve it in an authorized artifact
location and verify the link; if that is unavailable, retain it and disclose the
context cost. Do not trim unresolved decisions or uncertain effects to meet a size
target, rewrite immutable tracker history, or create an archive for every turn.

On resume, read that record and the referenced current artifacts. Confirm actual
implementation separately from approval: approval does not prove implementation,
and unchanged code does not prove that an approved change remains unimplemented.
Changed scope/content invalidates related evidence and approvals.
Do not replay external actions with uncertain outcomes: inspect the remote
state through available tools, then reconcile or ask for direction.

Retry only with new evidence or a changed hypothesis; repeated unchanged failure
requires a checkpoint and explanation, not a silent loop. Continue authorized work
while progress is possible. At an actual host/resource limit, save a resumable handoff
without claiming completion. A checkpoint supports recovery; it does not schedule
execution, keep the host alive or guarantee exactly-once side effects.
