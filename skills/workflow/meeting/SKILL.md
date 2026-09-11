---
name: meeting
description: |
  [WHAT] Compatibility entrypoint for starting a legacy Shode team engagement; routes to the owning discipline without duplicating team policy.
  [WHEN] The user explicitly starts the legacy team workflow; not an ordinary question or a real-world meeting summary.
  [TRIGGER] /shode-house:meeting, "start legacy Shode team".
---

# shode-house — Team entrypoint (legacy name: meeting)

This is the legacy plugin entrypoint, not a meeting-minutes skill. Use the existing
request and task context; invoking it does not authorize implementation, publication
or tracker migration. Do not restart an engagement or reread already-loaded guidance.

## Choose the owning guidance

| Need | Owner to read when needed |
|---|---|
| Legacy safety, language and handoff constraints | `shode-house-discipline` (reuse agent preload) |
| Select a role/domain, resolve ownership or delegation | `shode-house-routing` |
| Start/resume a delivery phase or choose engagement mode | `shode-house-workflow` |
| Validate a project/domain claim | `shode-house-evidence` |
| Produce a deliverable or apply completion criteria | `shode-house-deliverable` |
| Legacy broadcast formatting | `shode-house-broadcast` |
| Resolve an actual phase/scope transition conflict | `shode-house-drift` |

Read only guidance needed for the next action. Team membership, RACI and conflict
resolution belong to routing; phase definitions and AFK/Interactive/Hybrid semantics
belong to workflow. Do not maintain a second copy here or preload all seven skills.

## Recite Discipline Card

Legacy main-session presentation is owned by `output-styles/oliver.md` and
`skills/discipline/shode-house-discipline/main-session.md`. Do not duplicate the
card or make delegates recite it. Host/user instructions and authorization prevail.

## Start from the requested outcome

A question needs an answer/consultation, not automatic phase fan-out. Existing-code
review uses `review-checklist`; root-cause investigation uses `diagnose`; authorized
code changes use `dev-gate`. Project-wide CI work alone uses `automate-test`.
For feature specification, the legacy command is `/design-system`; its name does
not mean every request requires UI design. Follow its intent selection first.

## Compatibility boundary

The portable `shode-house-team` distribution has its own core/reference workflow.
Do not combine its rules with this legacy pipeline or claim that legacy hooks,
named agents and approval mechanics work on every host. Installation and migration
choices are documented outside runtime guidance in the project README.
