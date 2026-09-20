# Repository Instructions

Repo-wide rules for every agent and tool working in this repository. Keep this file short; tool-specific detail lives in the files it points to.

## Authority

Current user instructions and repository rules take precedence over plugin, tool, and tracker defaults. Generated or tool-managed guidance (including anything Beads writes) is task-tracking help, not permission to override them.

## Task Tracking

This repository uses Beads (`bd`) for durable task tracking: `bd ready` to find work, `bd show <id>` to read it, `bd update <id> --claim` to take it, `bd close <id>` when it is done. Do not keep markdown TODO lists as the source of truth.

Run `bd prime` when detailed Beads workflow guidance is required.

Detailed Beads workflow: `.agents/skills/beads/SKILL.md`. Install, command reference, storage/sync architecture, agent context profiles, and the session completion sequence: `docs/bd-quickstart.md`.

## Safety

Do not commit, push, sync remote state (including `bd dolt push` / `bd dolt pull`), or perform destructive actions unless authorized by the current task or repository policy. Do not commit or push without clear authority; a current "do not commit" or "do not push" instruction always wins. If an authorized sync or push is blocked, stop and report the exact command and error.

## Validation

Run checks relevant to the changed behavior (`make validate`, `python3 -m pytest tests -q`, or the narrower check the change touches).

Fix failures caused by the requested change and rerun affected checks without requesting approval after every local iteration. At handoff, report changed files, the validation you ran, and its result.

## Shell

Use non-interactive shell operations in automated workflows; `cp`, `mv`, and `rm` may be aliased to `-i` and hang on a prompt.

- Files: `cp -f`, `mv -f`, `rm -f`; recursive: `cp -rf`, `rm -rf`
- `ssh` / `scp`: `-o BatchMode=yes`
- `apt-get`: `-y`; `brew`: `HOMEBREW_NO_AUTO_UPDATE=1`
- `bd`: never `bd edit` (opens an editor); use `bd update` flags
