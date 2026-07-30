// drain — Workflow-tool runner (Runner A). Parameterize ITEMS, then run.
// Runner B (Task tool, Claude Code default) = 1 Task per item in ONE message; same COMMON brief.
// Invariants enforced here: worktree isolation (5), no push (6), scope-lock + no-delete (7),
// unit-tests-only in parallel (8). Serial cherry-pick + `bd close` happen in the MAIN LOOP,
// never inside this workflow (see SKILL.md Step 4-5).

export const meta = {
  name: 'drain-ready-backlog',
  description:
    'Implement + unit-test N independent bd items, each in an isolated worktree on branch fix/<id>; return verdict+branch+sha for serial cherry-pick + bd close by the main loop',
  phases: [
    { title: 'Implement', detail: 'one isolated worktree agent per bd item (TDD, no push)' },
  ],
}

const COMMON = `You are in an ISOLATED git worktree. Implement ONLY the one item. Do NOT run bd (unavailable in a worktree - full context is in this prompt).
HARD RULES: TDD where it is code (failing unit test first -> fix -> green). Run UNIT tests only (e.g. pnpm exec vitest run <path>); NO Testcontainers/integration in parallel - name any that must run before deploy. tsc/eslint changed files. Then: git switch -c fix/<ID> ; git add <files> ; git commit. Do NOT push. Do NOT touch files outside scope. Do NOT delete files you did not create.
VERIFY BEFORE DONE: paste the real test PASS line. If FALSE POSITIVE or BLOCKED, say so with evidence - do NOT invent a fix.
Return structured: verdict, branch (fix/<ID>), commit_sha (git rev-parse HEAD), files, test_cmd, test_result, note.`

// { id, type: 'shode-house:developer' | 'shode-house:qa-engineer' | 'shode-house:code-reviewer'
//            | 'shode-house:devops-engineer' | 'shode-house:security-engineer' | 'shode-house:ux-ui-designer',
//   brief: 'finding + file:line + fix direction' }
// One entry per FILE-DISJOINT item. Items sharing files must be merged into ONE entry.
const ITEMS = []

const SCHEMA = {
  type: 'object',
  additionalProperties: false,
  properties: {
    id: { type: 'string' },
    verdict: { type: 'string', enum: ['FIXED', 'FALSE_POSITIVE', 'PARTIAL', 'BLOCKED'] },
    branch: { type: 'string' },
    commit_sha: { type: 'string' },
    files: { type: 'array', items: { type: 'string' } },
    test_cmd: { type: 'string' },
    test_result: { type: 'string' },
    note: { type: 'string' },
  },
  required: ['id', 'verdict', 'note'],
}

if (ITEMS.length === 0) throw new Error('drain: ITEMS is empty - verify the open set with `bd show` first')
if (ITEMS.length > 20) throw new Error('drain: > 20 items - split into rounds (SKILL.md Round cap)')

phase('Implement')
log(`drain: ${ITEMS.length} verified item(s), one worktree agent each`)

const results = await parallel(
  ITEMS.map((it) => () =>
    agent(`Fix bd ${it.id}. ${it.brief}\n${COMMON}\nUse ID=${it.id} (branch fix/${it.id}).`, {
      label: `fix:${it.id}`,
      phase: 'Implement',
      isolation: 'worktree',
      agentType: it.type,
      schema: SCHEMA,
    }).then((r) => r || { id: it.id, verdict: 'BLOCKED', note: 'agent returned null' })
  )
)

// Main loop takes it from here: serial cherry-pick of every FIXED sha, ONE fast-gate run,
// ONE push, then `bd close <id> --reason "<verdict> <sha> <test_result>"` + `bd show <id>`
// to confirm CLOSED. PARTIAL/BLOCKED stay OPEN with an honest note.
return results
