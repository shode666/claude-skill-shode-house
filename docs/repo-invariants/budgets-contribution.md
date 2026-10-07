# Repo invariants, detail — runtime guarantees, budgets, contribution

This file states no rule. The rules are in `AGENTS.md`, which is loaded on every session; each section here adds scope detail, rationale, history or examples to the section of that file named in its heading, and is meant to be read next to it. If anything here seems to differ from that file, that file is the rule. Linked from the index table there, not imported.

## Detail for `AGENTS.md` § Lazy ≠ Negligent

**Runtime guarantee.** Examples of a guarantee that has to be enforced at runtime: a long-run fan-out cap, retry, checkpoint. The contract a generated runner follows covers journal, idempotency, replay boundary, version stamp, HITL hash and crash injection.

The other rules of that section need no further detail.

## Detail for `AGENTS.md` § Budgets

**Rule conservation.** A migration entry records the exact source, the fragment and the reason. The gate script compares against the pinned base in `.rule-baseline`. The `root_only` anchors are declared in `.enforcement-map.json`; the floor CI #21 holds is 190 (raised from 123 at the 4.0.0 switch to the measured count: router style +23, safety floor +16, the W5a and W5b bodies +12 and +16).

## Questions for `AGENTS.md` § Contribution rules

**New rule**

- What failure does it prevent?
- Who is the canonical owner? (table → `docs/enforcement-map.md`)
- Does it have to be always-on, or can it be a lazy reference?
- Which eval or gate protects it?

**New skill**

- Is it a separate capability that is really reused?
- Can an existing skill plus ≤ 1 branch/reference cover it?
- Is discovery still unambiguous?

**New model profile**

- Which eval fails?
- For which model family?
- How consistently?
- Why can the core wording not fix it?
- What is the smallest override?
