# shape-baseline — protocol revisions after the freeze

## Revision 2 — 2026-10-03, before re-scoring (rule written before the code was edited)

Reason: a reviewer that runs the test suite with coverage leaves an untracked `.coverage` file in the fixture. The
revision-1 scorer treats every path outside `outputs/**` as a source path, so such a file counted as a changed file
outside the allowed set, as a source edit by the reviewer, and as the "last source edit" that later reviews had to
follow. Seen in `3.17.2-generated/S7/r3` and `3.17.2-source/S3/r1`, `S3/r2`.

Rule change (in `score.py` only):

> A fixture path is a **tool by-product** when it matches any of `.coverage`, `.coverage.*`, `htmlcov/**`,
> `.pytest_cache/**`, `__pycache__/**`, `**/__pycache__/**`, `*.pyc`, `.hypothesis/**`. By-product paths are removed
> from the set of changed paths before any check, and are never recorded as an edit (neither from an `Edit`/`Write`
> call nor from a Bash snapshot). Nothing else changes.

Procedure: verdicts and every check result of all 60 matrix runs saved before the edit
(`results/score-before-rev2.json`); scorer edited; `FREEZE.sha256` rewritten; all 60 runs re-scored; every change listed
in `outputs/shode-house-v7u/09-quinn-baseline-stage2.md` § 5.
