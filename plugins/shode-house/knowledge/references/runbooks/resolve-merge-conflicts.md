---
name: resolve-merge-conflicts
description: Reference (lazy-load) ของ Dave/Aaron — วิธีแก้ git merge/rebase conflict ทีละ hunk ตาม intent ของแต่ละฝั่ง โหลดเฉพาะตอนมี conflict ค้างอยู่
---

```lazy-load-contract
LOAD: references/runbooks/resolve-merge-conflicts.md
WHEN: git merge/rebase/cherry-pick in progress with unresolved conflicts
OWNER: developer
REQUIRED-BEFORE: git_continue_or_commit
```

# Resolving merge / rebase conflicts

Adapted from mattpocock/skills `resolving-merge-conflicts`; ownership stays with Dave
(code) and Aaron (CI/infra files). Never `--abort` to make a conflict disappear.

1. **See the state** — `git status`, which operation is in progress, every conflicted file.
2. **Find the primary source of each side** — commit messages, the task/PR/issue each change
   came from, the design record. Understand *why* each side changed the hunk, not just *what*.
3. **Resolve hunk by hunk** — keep both intents when they compose; when they cannot, keep
   the one matching the merge's stated goal and record the trade-off in the task record.
   Do not invent new behaviour inside a conflict resolution.
4. **Run the project's checks** — typecheck/lint, then tests, then format. Fix what the
   merge broke; anything you cannot fix becomes a finding for the task owner, not a skip.
5. **Finish the operation** — stage, commit (or `rebase --continue` until done). Paste the
   final `git status` and test result as evidence. Generated trees (e.g. `plugins/shode-house`)
   are regenerated from source after the merge, never hand-merged.
