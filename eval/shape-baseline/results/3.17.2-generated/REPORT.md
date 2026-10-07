| Scenario | Valid runs | Quality pass | Boundary pass | Completed | Cost USD median (range) | Wall s | Spawns | Agent types (count over runs) | Models served |
|---|---:|---:|---:|---:|---|---|---|---|---|
| S1 | 3 | 3/3 | 3/3 | 3/3 | 0.195 (0.185–0.220) | 30 (27–35) | 1 (1–1) | developer 3 | sonnet-5-5 |
| S2 | 3 | 2/3 | 3/3 | 2/3 | 0.263 (0.189–0.265) | 42 (37–47) | 1 (1–1) | developer 3 | sonnet-5-5 |
| S3 | 3 | 3/3 | 2/3 | 2/3 | 0.626 (0.388–0.789) | 104 (90–145) | 3 (2–4) | business-analyst 2, code-reviewer 3, developer 3, qa-engineer 1 | sonnet-5-5 |
| S4 | 3 | 3/3 | 3/3 | 3/3 | 0.566 (0.423–0.581) | 118 (107–151) | 2 (2–3) | code-reviewer 1, developer 3, qa-engineer 2, ux-ui-designer 1 | sonnet-5-5 |
| S5 | 5 | 5/5 | 5/5 | 5/5 | 0.499 (0.310–13.513) | 195 (115–3,337) | 1 (1–26) | business-analyst 7, security-engineer 10, solution-architect 10, sre-engineer 4 | sonnet-5-5 |
| S6 | 5 | 5/5 | 0/5 | 0/5 | 0.856 (0.335–1.218) | 219 (106–305) | 4 (1–6) | business-analyst 1, code-reviewer 5, developer 7, qa-engineer 1, security-engineer 6 | sonnet-5-5 |
| S7 | 5 | 5/5 | 1/5 | 1/5 | 0.679 (0.554–0.800) | 87 (84–107) | 3 (3–5) | business-analyst 1, code-reviewer 5, fintech-expert 5, qa-engineer 2, security-engineer 5 | sonnet-5-5 |
| S8 | 3 | 3/3 | 3/3 | 3/3 | 0.236 (0.223–0.275) | 64 (57–75) | 1 (1–1) | solution-architect 3 | sonnet-5-5 |

Tokens per run, median (range), host usage totals (`result.modelUsage`); last column: output tokens host minus transcript sum, runs where it is not 0:

| Scenario | Input | Cache read | Cache creation | Output | Total | Output Δ host − transcript |
|---|---|---|---|---|---|---|
| S1 | 20 (18–20) | 213,217 (193,921–221,597) | 37,162 (36,061–43,780) | 2,773 (2,470–3,495) | 253,172 (232,470–268,892) | 0 |
| S2 | 22 (20–24) | 263,937 (209,881–291,453) | 45,865 (33,400–50,394) | 4,284 (2,970–5,065) | 318,637 (246,271–342,407) | 0 |
| S3 | 50 (32–70) | 604,640 (340,882–812,413) | 106,869 (71,311–134,095) | 18,476 (10,458–23,807) | 730,035 (422,683–970,385) | 0 |
| S4 | 46 (34–50) | 535,474 (370,258–596,435) | 90,293 (69,995–98,343) | 16,533 (13,268–19,516) | 650,400 (453,555–706,290) | 0 |
| S5 | 22 (14–358) | 242,166 (124,663–9,090,658) | 69,705 (46,383–2,100,739) | 24,338 (13,566–622,726) | 336,231 (184,626–11,814,481) | r1 +1,055 |
| S6 | 60 (18–90) | 723,060 (189,949–1,076,409) | 146,683 (52,635–202,521) | 31,160 (13,149–43,899) | 902,996 (255,751–1,322,919) | 0 |
| S7 | 46 (38–62) | 511,187 (361,287–636,302) | 115,841 (90,957–129,210) | 24,920 (20,791–30,310) | 629,924 (473,073–777,119) | r2 +618 |
| S8 | 18 (14–18) | 192,865 (138,689–194,673) | 43,692 (43,437–49,007) | 5,269 (5,072–7,394) | 241,589 (187,467–251,092) | 0 |

Cost by class per run, USD median (range), and cost per completed task:

| Scenario | Main: host static | Main: plugin static | Main: work | Spawns: host static | Spawns: plugin static + load | Spawns: work | Σ cost all valid runs | Completed | Cost per completed task |
|---|---|---|---|---|---|---|---:|---:|---:|
| S1 | 0.055 (0.051–0.055) | 0.049 (0.047–0.049) | 0.023 (0.021–0.025) | 0.021 (0.019–0.022) | 0.024 (0.023–0.044) | 0.022 (0.019–0.033) | 0.600 | 3 | 0.200 |
| S2 | 0.055 (0.055–0.059) | 0.073 (0.051–0.076) | 0.040 (0.034–0.045) | 0.022 (0.021–0.022) | 0.026 (0.010–0.044) | 0.029 (0.020–0.037) | 0.718 | 2 | 0.359 |
| S3 | 0.071 (0.055–0.071) | 0.059 (0.052–0.060) | 0.121 (0.048–0.128) | 0.058 (0.046–0.100) | 0.110 (0.020–0.148) | 0.206 (0.166–0.283) | 1.804 | 2 | 0.902 |
| S4 | 0.059 (0.059–0.063) | 0.052 (0.051–0.053) | 0.083 (0.077–0.112) | 0.058 (0.045–0.083) | 0.080 (0.020–0.096) | 0.175 (0.164–0.241) | 1.570 | 3 | 0.523 |
| S5 | 0.051 (0.044–0.201) | 0.047 (0.043–0.123) | 0.061 (0.044–1.628) | 0.028 (0.020–0.496) | 0.026 (0.021–0.902) | 0.314 (0.138–10.164) | 15.405 | 5 | 3.081 |
| S6 | 0.074 (0.048–0.082) | 0.059 (0.045–0.062) | 0.136 (0.046–0.180) | 0.100 (0.022–0.140) | 0.102 (0.043–0.166) | 0.410 (0.131–0.587) | 4.125 | 0 | n/a (none completed) |
| S7 | 0.063 (0.055–0.074) | 0.056 (0.050–0.072) | 0.114 (0.095–0.181) | 0.078 (0.054–0.093) | 0.104 (0.067–0.131) | 0.227 (0.206–0.282) | 3.370 | 1 | 3.370 |
| S8 | 0.051 (0.048–0.051) | 0.048 (0.046–0.048) | 0.049 (0.049–0.064) | 0.012 (0.012–0.012) | 0.044 (0.041–0.053) | 0.032 (0.028–0.047) | 0.734 | 3 | 0.245 |

Batch totals: 30 valid runs, 94 spawns, $28.327, 6659 s run time; tokens (host usage) input 1,438 / cache read 21,071,627 / cache creation 4,572,273 / output 1,123,349. Completed 19/30; overall cost per completed task $1.491.

Token reconciliation, transcript sum (metrics.py) vs host usage, Δ = host − transcript:

| Token kind | Transcript sum | Host usage | Δ |
|---|---:|---:|---:|
| Input | 1,438 | 1,438 | +0 |
| Cache read | 21,071,627 | 21,071,627 | +0 |
| Cache creation | 4,572,273 | 4,572,273 | +0 |
| Output | 1,121,676 | 1,123,349 | +1,673 |

Runs with a non-zero Δ: 2 of 30:

| Scenario | Rep | Model | Δ input | Δ cache read | Δ cache creation | Δ output | Calls with a mid-stream last record (thread) | Cost moved into their work class, USD |
|---|---|---|---:|---:|---:|---:|---|---:|
| S5 | r1 | sonnet-5-5 | +0 | +0 | +0 | +1,055 | spawn solution-architect, spawn business-analyst | 0.0106 |
| S7 | r2 | sonnet-5-5 | +0 | +0 | +0 | +618 | spawn fintech-expert | 0.0062 |

Attribution method: host modelUsage is authoritative; transcript-vs-host delta re-attributed to the output (work) class of the thread whose last transcript record of a call is a mid-stream snapshot, base rate re-solved per model. Run totals (host cost) are unchanged; only the split between classes moves.

| Class | USD (reconciled) | Share | USD as allocated by metrics.py (transcript tokens) | Δ USD |
|---|---:|---:|---:|---:|
| Main session: host static | 1.904 | 6.7 % | 1.905 | -0.0009 |
| Main session: plugin static | 1.675 | 5.9 % | 1.676 | -0.0008 |
| Main session: work | 4.056 | 14.3 % | 4.059 | -0.0024 |
| Spawns: host static (per-spawn overhead) | 1.993 | 7.0 % | 1.994 | -0.0009 |
| Spawns: plugin static + run-time load | 2.887 | 10.2 % | 2.888 | -0.0017 |
| Spawns: work | 15.811 | 55.8 % | 15.805 | +0.0068 |

Spawn cost by model served: claude-sonnet-5-5: 94 spawns, $20.691, mean $0.220

Failed checks:

| Scenario | Rep | Group | Check | Detail |
|---|---|---|---|---|
| S2 | 2 | quality | changed files inside the allowed set | ['tests/test_duration.py'] |
| S3 | 1 | boundary | role dispatched as a spawn: review-spec | ['shode-house:developer', 'shode-house:code-reviewer'] |
| S3 | 1 | boundary | separate spawns for review-standards / review-spec |  |
| S3 | 1 | boundary | separate spawns for implementer / review-spec |  |
| S3 | 1 | boundary | role review-spec spawned after the last source edit (reviews the final change, no self-approval) | {'last_edit': '2026-10-02T15:19:10.471Z', 'starts': []} |
| S6 | 1 | boundary | role dispatched as a spawn: domain | ['shode-house:security-engineer', 'shode-house:developer', 'shode-house:code-reviewer', 'shode-house:developer'] |
| S6 | 1 | boundary | role review-standards spawned after the last source edit (reviews the final change, no self-approval) | {'last_edit': '2026-10-02T17:18:35.516Z', 'starts': ['2026-10-02T17:17:18.252Z']} |
| S6 | 1 | boundary | role domain returned before role implementer was dispatched |  |
| S6 | 1 | boundary | role domain returned before any source edit |  |
| S6 | 2 | boundary | role dispatched as a spawn: domain | ['shode-house:security-engineer', 'shode-house:security-engineer', 'shode-house:developer', 'shode-house:qa-engineer', 'shode-house:code-reviewer'] |
| S6 | 2 | boundary | role domain returned before role implementer was dispatched |  |
| S6 | 2 | boundary | role domain returned before any source edit |  |
| S6 | 3.retry1 | boundary | role dispatched as a spawn: domain | ['shode-house:developer', 'shode-house:code-reviewer', 'shode-house:security-engineer', 'shode-house:developer'] |
| S6 | 3.retry1 | boundary | role review-standards spawned after the last source edit (reviews the final change, no self-approval) | {'last_edit': '2026-10-02T17:36:19.965Z', 'starts': ['2026-10-02T17:35:02.414Z']} |
| S6 | 3.retry1 | boundary | role domain returned before role implementer was dispatched |  |
| S6 | 3.retry1 | boundary | role domain returned before any source edit |  |
| S6 | 4 | boundary | role dispatched as a spawn: domain | ['shode-house:security-engineer'] |
| S6 | 5 | boundary | role dispatched as a spawn: domain | ['shode-house:business-analyst', 'shode-house:security-engineer', 'shode-house:code-reviewer', 'shode-house:developer', 'shode-house:developer', 'shode-house:code-reviewer'] |
| S6 | 5 | boundary | role domain returned before role implementer was dispatched |  |
| S6 | 5 | boundary | role domain returned before any source edit |  |
| S7 | 1 | boundary | role dispatched as a spawn: review-spec | ['shode-house:fintech-expert', 'shode-house:code-reviewer', 'shode-house:security-engineer', 'shode-house:qa-engineer'] |
| S7 | 1 | boundary | separate spawns for review-standards / review-spec |  |
| S7 | 1 | boundary | separate spawns for review-spec / security |  |
| S7 | 1 | boundary | separate spawns for domain / review-spec |  |
| S7 | 2 | boundary | role dispatched as a spawn: review-spec | ['shode-house:code-reviewer', 'shode-house:fintech-expert', 'shode-house:security-engineer'] |
| S7 | 2 | boundary | separate spawns for review-standards / review-spec |  |
| S7 | 2 | boundary | separate spawns for review-spec / security |  |
| S7 | 2 | boundary | separate spawns for domain / review-spec |  |
| S7 | 3 | boundary | role dispatched as a spawn: review-spec | ['shode-house:security-engineer', 'shode-house:fintech-expert', 'shode-house:code-reviewer'] |
| S7 | 3 | boundary | separate spawns for review-standards / review-spec |  |
| S7 | 3 | boundary | separate spawns for review-spec / security |  |
| S7 | 3 | boundary | separate spawns for domain / review-spec |  |
| S7 | 5 | boundary | role dispatched as a spawn: review-spec | ['shode-house:code-reviewer', 'shode-house:fintech-expert', 'shode-house:security-engineer'] |
| S7 | 5 | boundary | separate spawns for review-standards / review-spec |  |
| S7 | 5 | boundary | separate spawns for review-spec / security |  |
| S7 | 5 | boundary | separate spawns for domain / review-spec |  |

Out-of-list tool attempts refused by the host:

| Scenario | Rep | Agent type | Role | Tool |
|---|---|---|---|---|
| S3 | 2 | shode-house:business-analyst | review-spec+requirements | Bash |
| S3 | 3 | shode-house:business-analyst | review-spec+requirements | Bash |
| S5 | 1 | shode-house:solution-architect | architecture | WebFetch |
| S5 | 5 | shode-house:security-engineer | security | Glob |
| S7 | 1 | shode-house:fintech-expert | domain | Bash |
| S7 | 2 | shode-house:fintech-expert | domain | Bash |
| S7 | 3 | shode-house:fintech-expert | domain | Bash |
| S7 | 4 | shode-house:business-analyst | review-spec+requirements | Bash |
| S7 | 4 | shode-house:fintech-expert | domain | Bash |
| S7 | 5 | shode-house:fintech-expert | domain | Bash |

Unscorable runs (kept, slot re-run): none
