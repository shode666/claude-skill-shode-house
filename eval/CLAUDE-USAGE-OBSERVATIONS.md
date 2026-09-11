# Claude/Cowork usage observations

Maintainer tooling only; none of these scripts ship in the 3.16 runtime payload.
Native completion boundaries, resumed slices and complete child aggregation have
not been verified on a live authenticated Claude host. Output is **UNSCORABLE**
for release benchmarking, even when ingestion exits successfully.

Pass one explicitly identified transcript, never an automatically selected latest
file. Create a metadata JSON object containing nonempty strings `run_id`,
`invocation_id`, `plugin_version`, `model`, `scenario`, `source_revision`,
`source_sha256`, `fixture_sha256`, `host_version`; a `settings` object; and
`coverage` equal to `main-only` or `subagents-only`. Hashes are lowercase SHA-256;
record actual observed provenance, not guessed defaults. Each independent trial
needs its own run ID, each invocation its own invocation ID.

```sh
python3 scripts/usage-from-transcript.py /absolute/main.jsonl --metadata /absolute/main-metadata.json --out /absolute/observations
python3 scripts/usage-from-cowork.py /absolute/child.jsonl --metadata /absolute/child-metadata.json --out /absolute/observations
```

Main and child tools require matching native session/message/agent identities and
coverage. Required counters cannot be missing, negative or coerced from strings.
Identical message snapshots deduplicate; conflicting snapshots, mixed sources,
malformed JSON and unknown usage layouts fail closed. An unsupported transcript
needs schema investigation, not silent omission or an invented zero.

Use one dedicated output directory and ingest serially (concurrent writers are
not supported). Repeating identical input and metadata is idempotent; relabeling
the same source or adding overlapping/resumed slices is rejected. Keep originals
for later reconciliation rather than deleting observations to bypass rejection.

Counters live under `observed_usage`; `duration_ms` is null, `usage_complete` false.
Caller metadata cannot inject benchmark counters. Exit 0 means an observation was
saved, **not PASS**. Exit 2 means ingestion failed. These files intentionally do
not satisfy the legacy benchmark record schema. Do not combine children with a
main total until native accounting proves whether that total already includes
them. Model prices and monetary cost are not inferred.
