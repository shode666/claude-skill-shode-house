// Mock-host execution of optional template, not native-host qualification.
import { readFileSync } from 'node:fs';
import assert from 'node:assert/strict';
import test from 'node:test';

const source = readFileSync(new URL('../skills/ops/drain/workflow-template.js', import.meta.url), 'utf8');
const AsyncFunction = Object.getPrototypeOf(async function () {}).constructor;
async function run(count, capacity, result = { verdict: 'FIXED', note: 'candidate' }) {
  const items = Array.from({ length: count }, (_, i) => ({ id: `T-${i}`, type: 'developer', brief: 'bounded change' }));
  const body = source.replace('export const meta', 'const meta')
    .replace('const ITEMS = []', `const ITEMS = ${JSON.stringify(items)}`)
    .replace('const WORKER_LIMIT = 3', `const WORKER_LIMIT = ${JSON.stringify(capacity)}`);
  let dispatched = 0;
  try {
    const results = await new AsyncFunction('phase', 'log', 'parallel', 'agent', body)(
      () => {}, () => {}, tasks => Promise.all(tasks.map(task => task())),
      async () => { dispatched++; return result; });
    return { results, dispatched };
  } catch (error) { error.dispatched = dispatched; throw error; }
}

test('empty, oversized or invalid-capacity waves dispatch nobody', async () => {
  for (const [count, capacity] of [[0, 2], [3, 2], [21, 3], [1, 0], [1, 4], [1, 1.5]]) {
    await assert.rejects(run(count, capacity), error => error.dispatched === 0);
  }
});
test('ready wave returns candidates without integrating or closing', async () => {
  const { results, dispatched } = await run(2, 2);
  assert.equal(dispatched, 2);
  assert.equal(results.length, 2);
  assert.equal(results[0].verdict, 'FIXED');
});
test('null worker result remains blocked', async () => {
  const { results } = await run(1, 1, null);
  assert.deepEqual(results, [{ id: 'T-0', verdict: 'BLOCKED', note: 'agent returned null' }]);
});
