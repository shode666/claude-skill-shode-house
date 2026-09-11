## Resolve uncertainty without stalling the run

Weigh evidence, impact, reversibility and decision authority before escalating:

| Uncertainty | First action | Escalate when |
|---|---|---|
| Project fact or existing convention | Inspect relevant code, tests, spec or prior decision | Sources conflict or necessary evidence is inaccessible |
| Technical/domain judgment within agreed scope | Consult the relevant expert with a bounded question and evidence paths | The choice changes user-visible behavior, accepted risk, cost or scope beyond authorization |
| User intent, business priority, acceptance tradeoff or external-action authority | Ask the user with options, recommendation and consequences | Do not substitute expert consensus for the user's decision |
| Low-impact reversible implementation detail | Follow established conventions, record a material assumption and proceed | Evidence contradicts the assumption or reversal would become costly |

Consult only the expert whose answer can change the next action; do not convene the
whole team or bounce the same unresolved question between roles. Ask for conclusion,
evidence, uncertainty and recommendation. Expert opinion cannot establish a missing
project fact or grant permission. If experts disagree, compare evidence and tradeoffs;
the delivery owner resolves choices within delegated authority, otherwise ask the user.
If no expert is available, investigate with available tools without claiming an
independent consultation; keep consequential unresolved decisions open.

Batch independent user decisions in one concise request, state what is blocked and
continue unaffected work. Never treat silence as approval. Record the decision owner,
answer/source and remaining question in the canonical task record so resume does not
repeat settled questions. Ask again only when the relevant scope or evidence changes.


## Shared project language

Reuse the project's glossary, specs and decision records wherever they live; do not
create CONTEXT.md or an ADR directory merely to enforce a filename convention.
When a term is ambiguous, test it with a concrete business scenario and compare
the stated meaning with code. Distinguish intended policy from implemented behavior.
An expert can explain domain options; only an authorized owner settles business intent.

Record resolved terms once at the designated source, link them from task records,
and reuse them in code/test names where applicable. In read-only work, report proposed
clarifications without writing documents. Do not reread the full glossary every turn:
retrieve terms relevant to the change.

Capture a separate architectural decision only when there is a meaningful tradeoff
whose rationale would otherwise be lost and reversal is costly or surprising.
Reuse an existing record when sufficient; routine reversible details do not need ADRs.
