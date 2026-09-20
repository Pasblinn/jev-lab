import assert from 'node:assert/strict';
import { mkdtempSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { describe, it } from 'node:test';
import {
  evaluateCompletion,
  recordShadow,
  shadowReport,
  type GateInput,
  type JevAnswers,
  type JevAsker,
} from './completion-gate.js';
import type { WorkerResult } from './worker-result.js';

const green: WorkerResult = {
  taskId: 'T-1',
  status: 'SUCCESS',
  implemented: ['LRU eviction now releases the entry buffer', 'added regression test for the leak'],
  filesChanged: ['src/cache/lru.ts', 'tests/cache/lru-leak.test.ts'],
  validation: { tests: 'PASS', typecheck: 'PASS', lint: 'PASS', build: 'PASS' },
  decisions: [],
  risks: [],
  unresolved: [],
  diffStats: { added: 41, removed: 6 },
  workerConfidence: 'high',
};

const input = (over: Partial<GateInput> = {}): GateInput => ({
  taskId: 'T-1',
  objective: 'Fix the memory leak in the LRU cache',
  acceptanceCriteria: ['Evicted entries release their buffer', 'A regression test covers the leak'],
  highRisk: false,
  result: green,
  ...over,
});

const answering =
  (answers: JevAnswers): JevAsker =>
  async () =>
    answers;
const neverAsked: JevAsker = async () => {
  throw new assert.AssertionError({ message: 'Jev must not be asked when a rule decides' });
};

describe('completion gate — deterministic rules beat Jev', () => {
  it('rejects red checks without asking Jev', async () => {
    const result = { ...green, validation: { ...green.validation, tests: 'FAIL' as const } };
    const d = await evaluateCompletion(input({ result }), { ask: neverAsked });
    assert.equal(d.verdict, 'reject');
    assert.equal(d.decidedBy, 'rule');
  });

  it('escalates unresolved items, high risk and missing criteria without asking Jev', async () => {
    for (const over of [
      { result: { ...green, unresolved: ['race on concurrent eviction'] } },
      { highRisk: true },
      { acceptanceCriteria: [] },
    ]) {
      const d = await evaluateCompletion(input(over), { ask: neverAsked });
      assert.equal(d.verdict, 'escalate');
      assert.equal(d.decidedBy, 'rule');
    }
  });
});

describe('completion gate — Jev layer', () => {
  it('accepts only when every criterion and the evidence clear the threshold', async () => {
    const d = await evaluateCompletion(input(), {
      ask: answering({ evidence_concrete: { noul: 0.97 }, criterion_0: { noul: 0.99 }, criterion_1: { noul: 0.95 } }),
    });
    assert.equal(d.verdict, 'accept');
    assert.deepEqual(d.criteria, [0.99, 0.95]);
  });

  it('one weak criterion is enough to escalate', async () => {
    const d = await evaluateCompletion(input(), {
      ask: answering({ evidence_concrete: { noul: 0.99 }, criterion_0: { noul: 0.99 }, criterion_1: { noul: 0.6 } }),
    });
    assert.equal(d.verdict, 'escalate');
    assert.equal(d.decidedBy, 'jev');
  });

  it('a missing answer counts as zero, never as a pass', async () => {
    const d = await evaluateCompletion(input(), {
      ask: answering({ evidence_concrete: { noul: 0.99 }, criterion_0: { noul: 0.99 } }),
    });
    assert.equal(d.verdict, 'escalate');
  });

  it('Jev outage escalates, it never accepts', async () => {
    const d = await evaluateCompletion(input(), {
      ask: async () => {
        throw new Error('HTTP 503');
      },
    });
    assert.equal(d.verdict, 'escalate');
    assert.equal(d.decidedBy, 'fallback');
  });
});

describe('completion gate — shadow ledger', () => {
  it('counts agreement, savings and false accepts, ignoring unjudged entries', async () => {
    const file = join(mkdtempSync(join(tmpdir(), 'gate-')), 'shadow.jsonl');
    const gate = (verdict: 'accept' | 'escalate') => ({
      verdict,
      decidedBy: 'jev' as const,
      reason: '',
      criteria: [],
      evidenceConcrete: null,
      ms: 1,
    });
    const at = '2026-09-20T00:00:00Z';
    recordShadow(file, { at, taskId: 'a', gate: gate('accept'), actual: 'accept' });
    recordShadow(file, { at, taskId: 'b', gate: gate('accept'), actual: 'reject' });
    recordShadow(file, { at, taskId: 'c', gate: gate('escalate'), actual: 'accept' });
    recordShadow(file, { at, taskId: 'd', gate: gate('accept'), actual: null });
    assert.deepEqual(shadowReport(file), { total: 4, judged: 3, agree: 1, falseAccepts: 1, wouldHaveSaved: 1 });
  });
});

// Opt-in: hits the real API. JEV_LIVE=1 JEV_API_KEY=... node --test dist/completion-gate.test.js
describe('completion gate — live Jev', { skip: process.env['JEV_LIVE'] !== '1' }, () => {
  const cases: { name: string; over: Partial<GateInput>; expect: 'accept' | 'escalate' }[] = [
    { name: 'solid report', over: {}, expect: 'accept' },
    {
      name: 'claims with no test evidence',
      over: {
        result: {
          ...green,
          implemented: ['fixed the leak'],
          filesChanged: ['src/cache/lru.ts'],
          diffStats: { added: 2, removed: 1 },
        },
      },
      expect: 'escalate',
    },
    {
      name: 'did a different task',
      over: {
        result: {
          ...green,
          implemented: ['renamed variables in the logger', 'updated README badges'],
          filesChanged: ['src/log/logger.ts', 'README.md'],
        },
      },
      expect: 'escalate',
    },
  ];
  for (const c of cases) {
    it(c.name, async () => {
      const d = await evaluateCompletion(input(c.over));
      console.log(
        `    [live] ${c.name}: ${d.verdict} (${d.decidedBy}) evidence=${d.evidenceConcrete} criteria=${JSON.stringify(d.criteria)} ${d.ms}ms`,
      );
      assert.equal(d.decidedBy, 'jev');
      assert.equal(d.verdict, c.expect);
    });
  }
});
