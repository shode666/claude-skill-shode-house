| Scenario | Valid runs | Quality pass | Boundary pass | Completed | Cost USD median (range) | Wall s | Spawns | Agent types (count over runs) | Models served |
|---|---:|---:|---:|---:|---|---|---|---|---|
| S1 | 3 | 2/3 | 3/3 | 2/3 | 0.196 (0.193–0.200) | 27 (26–27) | 1 (1–1) | developer 3 | sonnet-5-5 |
| S2 | 3 | 2/3 | 3/3 | 2/3 | 0.233 (0.213–0.298) | 34 (32–44) | 1 (1–1) | developer 3 | sonnet-5-5 |
| S3 | 3 | 3/3 | 3/3 | 3/3 | 0.608 (0.541–0.786) | 94 (89–106) | 3 (3–4) | business-analyst 3, code-reviewer 3, developer 3, qa-engineer 1 | sonnet-5-5 |
| S4 | 3 | 3/3 | 3/3 | 3/3 | 2.134 (1.319–3.555) | 306 (209–398) | 2 (2–2) | developer 3, ux-ui-designer 3 | fable-5, sonnet-5-5 |
| S5 | 5 | 5/5 | 5/5 | 5/5 | 1.143 (0.800–4.444) | 157 (112–502) | 1 (1–5) | business-analyst 2, fintech-expert 1, security-engineer 7, solution-architect 2 | fable-5, opus-5-5, sonnet-5-5 |
| S6 | 5 | 4/5 | 3/5 | 2/5 | 1.972 (0.994–3.219) | 357 (139–546) | 6 (2–10) | business-analyst 3, code-reviewer 7, developer 7, fintech-expert 3, qa-engineer 4, security-engineer 5 | fable-5, opus-5-5, sonnet-5-5 |
| S7 | 5 | 5/5 | 4/5 | 4/5 | 1.284 (1.104–1.413) | 96 (91–126) | 5 (4–5) | business-analyst 4, code-reviewer 5, fintech-expert 5, qa-engineer 5, security-engineer 5 | fable-5, opus-5-5, sonnet-5-5 |
| S8 | 3 | 3/3 | 2/3 | 2/3 | 0.516 (0.216–0.526) | 59 (56–90) | 1 (1–1) | ecommerce-expert 1, solution-architect 2 | fable-5, sonnet-5-5 |

Tokens per run, median (range), host usage totals (`result.modelUsage`); last column: output tokens host minus transcript sum, runs where it is not 0:

| Scenario | Input | Cache read | Cache creation | Output | Total | Output Δ host − transcript |
|---|---|---|---|---|---|---|
| S1 | 18 (16–20) | 214,086 (175,911–243,053) | 37,125 (36,882–40,446) | 2,733 (2,664–2,824) | 254,053 (219,037–282,688) | 0 |
| S2 | 20 (16–28) | 257,067 (198,074–394,035) | 43,018 (41,524–47,495) | 3,327 (3,047–5,634) | 303,432 (242,661–447,192) | 0 |
| S3 | 52 (44–60) | 702,864 (582,609–807,443) | 100,218 (89,916–130,783) | 16,484 (14,750–24,151) | 819,618 (687,319–962,437) | 0 |
| S4 | 52 (40–72) | 797,329 (542,612–1,380,145) | 99,538 (81,252–117,920) | 23,908 (17,491–35,590) | 920,827 (641,395–1,533,727) | 0 |
| S5 | 24 (18–66) | 292,994 (217,513–855,122) | 54,430 (44,921–225,332) | 12,797 (9,330–68,225) | 351,006 (284,758–1,148,745) | 0 |
| S6 | 78 (30–136) | 1,072,480 (339,327–2,121,363) | 216,949 (69,314–388,514) | 49,668 (17,580–103,611) | 1,339,175 (427,998–2,613,624) | r4 +596 |
| S7 | 56 (44–62) | 727,762 (525,890–784,663) | 127,546 (123,446–134,719) | 24,481 (21,129–30,741) | 872,803 (673,148–949,021) | r4 +422 |
| S8 | 12 (12–20) | 112,679 (111,494–249,326) | 38,950 (37,661–43,498) | 6,000 (4,115–6,445) | 160,304 (156,456–293,452) | 0 |

Cost by class per run, USD median (range), and cost per completed task:

| Scenario | Main: host static | Main: plugin static | Main: work | Spawns: host static | Spawns: plugin static + load | Spawns: work | Σ cost all valid runs | Completed | Cost per completed task |
|---|---|---|---|---|---|---|---:|---:|---:|
| S1 | 0.055 (0.051–0.059) | 0.049 (0.047–0.051) | 0.026 (0.020–0.028) | 0.009 (0.009–0.020) | 0.036 (0.036–0.036) | 0.020 (0.020–0.021) | 0.590 | 2 | 0.295 |
| S2 | 0.055 (0.051–0.067) | 0.071 (0.068–0.079) | 0.040 (0.031–0.065) | 0.011 (0.009–0.013) | 0.038 (0.036–0.041) | 0.019 (0.018–0.035) | 0.745 | 2 | 0.372 |
| S3 | 0.071 (0.071–0.078) | 0.088 (0.088–0.094) | 0.095 (0.092–0.130) | 0.049 (0.031–0.060) | 0.116 (0.106–0.177) | 0.177 (0.153–0.260) | 1.935 | 3 | 0.645 |
| S4 | 0.059 (0.051–0.059) | 0.051 (0.051–0.068) | 0.081 (0.077–0.087) | 0.182 (0.108–0.365) | 0.489 (0.382–0.772) | 1.273 (0.632–2.222) | 7.008 | 3 | 2.336 |
| S5 | 0.055 (0.048–0.074) | 0.049 (0.045–0.059) | 0.057 (0.049–0.247) | 0.085 (0.066–0.372) | 0.265 (0.185–0.763) | 0.661 (0.388–2.929) | 10.988 | 5 | 2.198 |
| S6 | 0.086 (0.055–0.109) | 0.064 (0.049–0.076) | 0.213 (0.096–0.357) | 0.178 (0.081–0.306) | 0.389 (0.249–0.566) | 1.042 (0.396–1.894) | 10.046 | 2 | 5.023 |
| S7 | 0.074 (0.063–0.078) | 0.100 (0.079–0.103) | 0.186 (0.162–0.242) | 0.115 (0.092–0.211) | 0.344 (0.334–0.367) | 0.422 (0.302–0.575) | 6.241 | 4 | 1.560 |
| S8 | 0.044 (0.044–0.059) | 0.046 (0.046–0.054) | 0.051 (0.039–0.063) | 0.021 (0.012–0.102) | 0.161 (0.030–0.183) | 0.102 (0.033–0.167) | 1.258 | 2 | 0.629 |

Batch totals: 30 valid runs, 90 spawns, $38.811, 5104 s run time; tokens (host usage) input 1,334 / cache read 18,311,159 / cache creation 3,271,788 / output 710,507. Completed 23/30; overall cost per completed task $1.687.

Token reconciliation, transcript sum (metrics.py) vs host usage, Δ = host − transcript:

| Token kind | Transcript sum | Host usage | Δ |
|---|---:|---:|---:|
| Input | 1,334 | 1,334 | +0 |
| Cache read | 18,311,159 | 18,311,159 | +0 |
| Cache creation | 3,271,788 | 3,271,788 | +0 |
| Output | 709,489 | 710,507 | +1,018 |

Runs with a non-zero Δ: 2 of 30:

| Scenario | Rep | Model | Δ input | Δ cache read | Δ cache creation | Δ output | Calls with a mid-stream last record (thread) | Cost moved into their work class, USD |
|---|---|---|---:|---:|---:|---:|---|---:|
| S6 | r4 | opus-5-5 | +0 | +0 | +0 | +596 | spawn fintech-expert | 0.0114 |
| S7 | r4 | fable-5 | +0 | +0 | +0 | +422 | spawn security-engineer | 0.0211 |

Attribution method: host modelUsage is authoritative; transcript-vs-host delta re-attributed to the output (work) class of the thread whose last transcript record of a call is a mid-stream snapshot, base rate re-solved per model. Run totals (host cost) are unchanged; only the split between classes moves.

| Class | USD (reconciled) | Share | USD as allocated by metrics.py (transcript tokens) | Δ USD |
|---|---:|---:|---:|---:|
| Main session: host static | 1.953 | 5.0 % | 1.953 | +0.0000 |
| Main session: plugin static | 2.001 | 5.2 % | 2.001 | +0.0000 |
| Main session: work | 3.575 | 9.2 % | 3.575 | +0.0000 |
| Spawns: host static (per-spawn overhead) | 3.383 | 8.7 % | 3.387 | -0.0035 |
| Spawns: plugin static + run-time load | 8.490 | 21.9 % | 8.500 | -0.0100 |
| Spawns: work | 19.408 | 50.0 % | 19.395 | +0.0135 |

Spawn cost by model served: claude-fable-5: 24 spawns, $21.595, mean $0.900; claude-opus-5-5: 9 spawns, $2.277, mean $0.253; claude-sonnet-5-5: 57 spawns, $7.410, mean $0.130

Failed checks:

| Scenario | Rep | Group | Check | Detail |
|---|---|---|---|---|
| S1 | 1 | quality | final reply language = en | th |
| S2 | 3 | quality | changed files inside the allowed set | ['tests/test_duration.py'] |
| S6 | 3 | boundary | role dispatched as a spawn: domain | ['shode-house:security-engineer', 'shode-house:developer', 'shode-house:code-reviewer'] |
| S6 | 3 | boundary | role domain returned before role implementer was dispatched |  |
| S6 | 3 | boundary | role domain returned before any source edit |  |
| S6 | 4 | quality (human read) | change applied and reported done while a domain item (amount ceiling FU-6) is stated as still awaiting the domain role; domain sign-off not complete |  |
| S6 | 5 | boundary | role dispatched as a spawn: domain | ['shode-house:qa-engineer', 'shode-house:code-reviewer', 'shode-house:security-engineer', 'shode-house:business-analyst', 'shode-house:developer', 'shode-house:qa-engineer', 'shode-house:developer', ' |
| S6 | 5 | boundary | role domain returned before role implementer was dispatched |  |
| S6 | 5 | boundary | role domain returned before any source edit |  |
| S7 | 1 | boundary | role dispatched as a spawn: review-spec | ['shode-house:fintech-expert', 'shode-house:security-engineer', 'shode-house:qa-engineer', 'shode-house:code-reviewer'] |
| S7 | 1 | boundary | separate spawns for review-standards / review-spec |  |
| S7 | 1 | boundary | separate spawns for review-spec / security |  |
| S7 | 1 | boundary | separate spawns for domain / review-spec |  |
| S8 | 2 | boundary | only roles ['architecture', 'staff', 'implementer'] spawned | ['shode-house:ecommerce-expert'] |

Out-of-list tool attempts refused by the host:

| Scenario | Rep | Agent type | Role | Tool |
|---|---|---|---|---|
| S3 | 1 | shode-house:business-analyst | review-spec+requirements | Bash |
| S3 | 2 | shode-house:business-analyst | review-spec+requirements | Bash |
| S7 | 3 | shode-house:business-analyst | review-spec+requirements | Bash |
| S7 | 4 | shode-house:business-analyst | review-spec+requirements | Bash |
| S7 | 5 | shode-house:business-analyst | review-spec+requirements | Bash |

Unscorable runs (kept, slot re-run): none
