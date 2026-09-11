## Continue across sessions

Determine the project's source of truth from its instructions and existing workflow:
Markdown files, Jira, Redmine, Beads or another system are equally valid. Reuse its
task IDs, status meanings and update conventions. Do not prefer a product, migrate
tracking, or create a second tracker merely because a tool is easier to access.
If multiple systems exist, identify authority per concern (for example Jira owns
task status, repository Markdown owns the spec, code/tests own implementation
evidence) and link them. Ask only when conflicting authority blocks the next action.

Save progress in the designated task record or linked artifact location. If the
canonical system is temporarily inaccessible, preserve its ID/URL and label a local
handoff as pending synchronization, not authoritative status; do not claim a remote
update succeeded. Re-read remote state and reconcile conflicts before an authorized
sync. When the project has no convention, agree on one lightweight store rather than
installing a tracker. For read-only work without writable storage, return a compact
handoff to the user and disclose that automatic recovery is unavailable.

At a meaningful work boundary, before handoff, or when the session is nearing its
limit, update the same task record with:

- Objective/acceptance criteria and authorized scope.
- Completed artifacts and source revision, including relevant uncommitted changes.
- Verification commands/results and the snapshot/environment they apply to.
- Next concrete action, outstanding decisions, dependencies and active owners.
- Attempts already made, unresolved failures and any user-set budget remaining.
- External actions already taken, operation IDs and uncertain outcomes, if any.

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
