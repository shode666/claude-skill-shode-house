// Optional host-specific example, not a required plugin runtime. Verify host API
// and isolation before adoption. Outputs are candidates, never acceptance/closure.
// Native delegation is an alternative. Prompts describe constraints; they do not
// prove isolation, review, safety or tool enforcement. Qualify those on the host.

export const meta = {
  name: 'drain-ready-backlog',
  description:
    'Implement one capacity-limited ready wave; return candidate evidence for independent review and authorized serial integration',
  phases: [
    { title: 'Implement', detail: 'one isolated worktree agent per bd item (TDD, no push)' },
  ],
}

const COMMON = `Use the verified isolated workspace and assigned branch. Implement ONLY the item. Oliver owns tracker writes. Load role/prerequisites and accessible acceptance evidence; ask for missing inputs.
HARD RULES: TDD for code. Run targeted project checks; shared integration/E2E resources must be serialized. Outstanding required checks block acceptance. Commit only when authorized; otherwise return a patch path and content revision in note. Do NOT push or change files outside scope. Do NOT delete files you did not create.
VERIFY BEFORE DONE: paste the real test PASS line. If FALSE POSITIVE or BLOCKED, say so with evidence - do NOT invent a fix.
Return structured: verdict, branch, commit_sha only if created, files, test_cmd, test_result, note (patch/revision, outstanding checks and questions). FIXED means candidate only; independent review and integrated checks are still required.`

// { id, type: 'shode-house:developer' | 'shode-house:qa-engineer' | 'shode-house:code-reviewer'
//            | 'shode-house:devops-engineer' | 'shode-house:security-engineer' | 'shode-house:ux-ui-designer',
//   brief: 'finding + file:line + fix direction' }
// One entry per FILE-DISJOINT item. Items sharing files must be merged into ONE entry.
const ITEMS = []
const WORKER_LIMIT = 3 // Set to the verified available host/resource capacity, at most 3.

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

if (ITEMS.length === 0) throw new Error('drain: no verified ready items - checkpoint instead of dispatch')
if (ITEMS.length > 20) throw new Error('drain: > 20 items - split into rounds (SKILL.md Round cap)')

phase('Implement')
log(`drain: ${ITEMS.length} verified item(s), one worktree agent each`)

// Caller supplies at most one verified ready wave; do not dispatch all 20 at once.
if (!Number.isInteger(WORKER_LIMIT) || WORKER_LIMIT < 1 || WORKER_LIMIT > 3)
  throw new Error('drain: verify available writer capacity between 1 and 3')
if (ITEMS.length > WORKER_LIMIT) throw new Error('drain: queue remaining items; wave exceeds verified writer capacity')
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

// Main loop validates artifacts, independent reviews and integrated required checks.
// Integrate only with authority; stop on the first failure. Push/closure require
// separate authority and receipt/read-back; UNKNOWN results must be reconciled.
// PARTIAL/BLOCKED stay open; unavailable tracker updates remain pending sync.
return results
