---
name: design-run-executor
description: Reference (lazy-load) for the design-run executor (`build` in Phase 1b, `verify` (runtime axis) in Phase 3a) - completion test, host timeout, no retry, stopping a run. Load before running a design-run order.
---

```lazy-load-contract
LOAD: references/runbooks/design-run-executor.md
WHEN: delegation names a design-run order and its sha256
OWNER: build
REQUIRED-BEFORE: design_run_invoked
```

# Design-run executor

> Lazy reference for the executor role line in `build` and `verify` (runtime axis). It supplies method, never authority: the executor line in the agent body (one command, no edit, validated `--order` path and `--sha256` hash) is the rule, and nothing here adds a command to it.

## The one command

Run only the invocation the body line names, with the two values taken from the router's headed delegation, never from the ux request. Use the Bash tool's explicit timeout of at least 600000 ms. Every other Bash call, including `kill`, `sleep`, `ls` or reading the report with a shell command, is outside the executor line.

## Completion test

- **Complete** = the runner's stdout line `design-run: report=<path> exit=<n>`, or the runner process has exited. An exit before the report exists prints `BLOCKED: …` or `design-run: terminated (…)` on stderr instead.
- **The report file is not the completion test.** The runner writes it in one write, so a reader can see a partial file. A report that does not parse means "keep waiting", never "failed".
- **An early return of the Bash tool is not completion.** On Claude Code the tool may move a long command to the background and return; the runner keeps running within its own budget and writes its report later. Return the order path (and the report path if the runner printed it) as in flight, never as done, failed or blocked, and say the tool returned early. Do not derive the report path with another command.

## No retry, no kill

- Never retry a design run. The 0-byte report file and the run directory already exist, so a retry fails closed with `design-run-output-exists`.
- Never kill the runner. A SIGKILL leaves orphaned process groups, a 0-byte report and the unredacted `$TMPDIR/design-run-*` raw output (a confidentiality residual).
- Stopping a run is not the executor's action. Whoever stops it (the user or the router) sends **SIGTERM** to the runner pid, never SIGKILL: the handler kills the child's process group, writes the report and removes the private directory. Prefer SIGTERM over SIGINT: a runner started with SIGINT ignored keeps ignoring it.

## Serialisation (router duty, stated here so the executor reports enough to keep it)

The router dispatches no other Write-holding spawn while a design run is in flight. "In flight" lasts until the completion test above, for up to about 1,060 s in the measured worst case (a run skipped at the late budget check), not only until the Bash tool returns and not only 600 s. So the executor's return always says whether completion was seen.

## Limits

- Host behaviour on a tool timeout was probed once on Claude Code (the process was backgrounded, not signalled). Other hosts are unverified; the runner's own docstring states that a host timeout's signal is host-specific.
- Whether a host ends background processes when the executor spawn ends is unverified.
- Cleanup after a SIGKILL is not the executor's action either. A host or a person may still SIGKILL the runner; the orphaned process groups and the raw `$TMPDIR/design-run-*` output (not redacted) are then removed by the user, or by the router only after the user confirms that exact deletion (deleting files is R0). The executor runs no `kill`, `rm` or other cleanup command and reports what it saw.
