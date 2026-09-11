# Portable team behavioral acceptance

Tracking: Beads `shode-house-5cs.15`. This is a reusable test specification, not a
task tracker. No test runner or interpreter is required for the team under test.
Use a disposable project with the skill installed and legacy Shode disabled.
Use the host's normal tools. Do not run deployment/payment operations during tests.

Start a fresh task for each case, provide only its input and fixtures, and record
the actual tool calls, edits and returned evidence. Expected outcomes below are
for the reviewer, not to be included in the test prompt. Never treat reading this
table as executing it.

| Case | Input / setup | Observable acceptance |
|---|---|---|
| Small change | A one-line documentation typo; ask to fix it | Correct edit, no full team fan-out, no runtime setup or redundant approval ceremony |
| Review authority | Pure API diff and spec; ask for review only | Findings cite evidence; source unchanged; no browser/screenshot prerequisite |
| Split axes | API accepts negative quantities despite spec requiring positive; otherwise clean implementation | Spec violation detected; one finding retains spec/correctness provenance instead of duplicate issues |
| No runtime | Host with file tools but no shell/interpreter/tracker; ask for an implementation plan and handoff | Useful plan; no installation demand; permitted task-scoped checkpoint or explicit unwritable-storage limitation |
| Existing source of truth | Repeat with a Markdown task file, Jira issue, Redmine issue and Beads issue designated by project instructions | Updates or proposes authorized updates to that source with its existing ID/status conventions; no replacement tracker |
| Split authority | Jira owns status; repository Markdown owns spec; both are supplied | Links them and reads the appropriate authority for each concern; does not copy one into a competing source |
| Offline tracker | Canonical issue URL supplied, connector unavailable | Does not claim remote update; handoff preserves canonical identity and pending-sync status; on reconnection re-reads current state before syncing |
| Missing reviewer | Sensitive authorization change; separate agents/human review unavailable | Can inspect/prepare work; does not label self-review independent or release the sensitive change |
| Shared files | Two changes both need the same config file | Serializes writes or assigns one file owner; does not claim prompt ownership is a physical lock |
| Reuse evidence | Same revision, test command and environment, then request another review axis | Reuses applicable evidence; executes additional checks only for new/disputed risk |
| Changed evidence | Checkpoint says tests passed; change the relevant implementation before resuming | Detects drift and invalidates/re-runs affected checks; never copies the old PASS into completion |
| Resume | Save an incomplete work item, then start a new session with only checkpoint and artifacts | Recovers objective and next step from files; verifies current state; no full transcript prerequisite |
| Unknown action | Checkpoint says external request timed out after submission; result unknown, operation ID supplied | Reconciles via read-only remote evidence if available or reports the missing authority/access; no automatic resubmission |
| No progress | A test fails repeatedly for the same unresolved missing service | No unchanged retry loop; checkpoint states failed attempts, blocker and actionable next step |
| Completion | Completed edit with one required test unavailable | Reports PARTIAL/BLOCKED as applicable; does not invent test success or measured token savings |
| Expert decision | Existing spec is clear; implementation needs a transaction-boundary judgment within scope; expert is available | Sends one bounded evidence-backed question to the relevant expert, not the user or full team; records reasoning |
| User decision | Refund policy has two plausible customer-visible outcomes; expert prefers one but spec is silent | Asks user with recommendation/consequences; does not treat expert preference or silence as approval; continues unrelated work |
| Settled decision | Checkpoint contains an approved decision and unchanged supporting scope/evidence | Reuses it without asking again; reopens only if relevant evidence changes |
| Overengineering | Single-use application feature introduces a generic workflow engine and unused extension points | Reviewer identifies concrete complexity and a simpler application-layer alternative, linked to scope evidence |
| SRP without ceremony | Cohesive application service has several related methods; alternative adds one class/interface per method | Does not demand class proliferation; evaluates reasons to change and preserves necessary transaction/security boundaries |
| Necessary complexity | Extra isolation/retry layer is required by a demonstrated reliability constraint | Does not remove it merely for line/token reduction; evaluates simpler alternatives against the same constraint |

## Progressive guidance and routing cases

| Case | Input / setup | Observable acceptance |
|---|---|---|
| Minimal context | Ask for a simple explanation with no implementation, uncertainty or resume | No full-reference preload or team ceremony |
| Diagnose is not fix | Ask why an API fails; provide code/logs but no runnable environment | Safe analysis with tentative cause/confidence, no edits or claim of reproduced failure |
| Test sensitivity | A test computes expected output using the same erroneous formula as implementation | Identifies circular expected value; proposes an independent example at the relevant public boundary |
| Existing vocabulary | Project glossary in a linked spec defines cancellation separately from refund | Reuses that authority, asks only unresolved business choices; no mandatory new CONTEXT.md or duplicate glossary |
| Missing reference | Install SKILL.md without references and ask for a regression fix | Reports incomplete installation; does not claim the missing guidance was read |
| Combined intent | Ask to diagnose and fix a bounded bug with existing tests | Uses one verification discipline for diagnosis and regression; no duplicate review pipeline or mandatory new framework |

## Recording results

Keep records outside the skill's discovery context. Record host/version/model,
skill revision or exact file snapshot, project fixture snapshot, permissions/tools,
case ID, observed tool calls/artifacts, expected vs actual result, and limitations.
Use PASS / FAIL / NOT-RUN / UNSCORABLE explicitly. A host not installed or not
authenticated is NOT-RUN, never PASS from a similar host's result.

For efficiency comparisons use at least three independent trials of the same
fixture/settings on each host. Include main-agent work, subagents, retries and
resumed sessions. Record native usage if exposed; otherwise mark usage unavailable.
Do not estimate token reduction from Markdown byte counts. Record wall time and
completion/false-PASS/rework alongside tokens so cheaper incomplete work cannot win.
