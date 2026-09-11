# Codex usage evidence (maintainers only)

`scripts/usage-from-codex.py` parses captured `codex exec --json` stdout. It is
build/evaluation tooling, never part of the instruction-only release. Runtime
users need no collector, script or interpreter. The official JSONL interface is
documented in [OpenAI non-interactive mode](https://learn.chatgpt.com/docs/non-interactive-mode).

Capture stderr separately. Keep the entire raw stream, including failed trials,
under controlled local evidence storage; it may contain private source or secrets.
Do not publish raw transcripts without review/redaction. The normalized record
contains usage/provenance, not prompts or command output.

For each invocation, supply metadata JSON with nonempty `run_id`, `invocation_id`,
`plugin_version`, actual observed `model`, `scenario`, `source_revision`,
`source_sha256`, `fixture_sha256`, `host_version`, `settings` object and measured
`duration_ms`. SHA256 values identify the exact skill payload and input fixture;
revision alone is insufficient for a dirty source tree. Record sandbox and relevant
model settings; do not put credentials in metadata. Unresolved model identity is
UNSCORABLE, not a guessed default.

`coverage` is `main-only` or `whole-workflow-no-subagents`. The latter is a reviewer
attestation requiring inspected calls proving no delegation, not something the
collector establishes from token totals. Child work requires separate evidence;
never claim that this main stream automatically includes it.

```sh
python3 scripts/usage-from-codex.py trial.stdout.jsonl \
  --metadata invocation.json --out evidence/candidate/api-review
```

Use a distinct run ID for every independent trial. Resumed invocations retain the
same run ID and have distinct invocation IDs. Store one scenario/variant in one
output directory: within it, identical re-ingestion is idempotent; conflicting
identities and remapping the same thread into a new trial are rejected. This does
not detect duplicated streams placed in separate output directories, or overlapping
captures with altered bytes. Review input inventory and invocation boundaries before
comparison; use one complete stdout capture per invocation, never cumulative replay
exports. Do not count several agents as several independent trials.

Codex input includes cache reads. This adapter emits disjoint input-minus-cache,
cache-read and output buckets, and supports only the observed zero-cache-write
format. Nonzero cache writes fail closed until their semantics are verified.
Reasoning output is not added again to output. Invocation duration is measured
externally; summing concurrent durations is not workflow wall-clock latency.

Malformed, failed or incomplete streams are UNSCORABLE. Preserve those attempts
and their partial raw usage: an unscorable failed trial prevents an unconditional
comparison PASS, not permission to omit it. Usage completion is not engineering
success: every record starts with quality verdict NOT-EVALUATED. Review correctness,
scope, overengineering and required recovery evidence separately.

Legacy Claude/Cowork collectors still require migration for safe trial identities;
do not use their scenario-derived IDs or subagent-only records to claim complete
3.16 workflow savings. This Codex adapter does not close that cross-host gap.
