// Completion gate. SHADOW ONLY: it records what Jev would have decided next
// to what actually happened, and never changes the outcome of a task.
import { appendFileSync, existsSync, mkdirSync, readFileSync } from 'node:fs';
import { dirname } from 'node:path';
import { checksGreen, type WorkerResult } from './worker-result.js';

export type GateVerdict = 'accept' | 'reject' | 'escalate';

export interface GateInput {
  taskId: string;
  objective: string;
  acceptanceCriteria: string[];
  /** High-risk envelopes never auto-accept, whatever Jev says. */
  highRisk: boolean;
  result: WorkerResult;
}

export interface GateDecision {
  verdict: GateVerdict;
  /** Which layer decided: a deterministic rule, Jev, or the Jev-unavailable fallback. */
  decidedBy: 'rule' | 'jev' | 'fallback';
  reason: string;
  /** Probability per acceptance criterion, in envelope order. Empty when a rule decided. */
  criteria: number[];
  evidenceConcrete: number | null;
  ms: number;
}

type Question =
  | { type: 'noul'; instructions: string }
  | { type: 'choice'; instructions: string; criteria: Record<string, string> };

export type JevAnswers = Record<string, { noul?: number; choice?: string; confidence?: number }>;
export type JevAsker = (state: unknown, questions: Record<string, Question>) => Promise<JevAnswers>;

export interface GateOptions {
  /** Every criterion and the evidence check must reach this to accept. Starting point, recalibrate. */
  acceptThreshold?: number;
  ask?: JevAsker;
}

const DEFAULT_ACCEPT_THRESHOLD = 0.94;

/** Minimal state: the contract and the worker's structured claim. Never the repo, never secrets. */
export function buildGateState(input: GateInput) {
  const r = input.result;
  return {
    objective: input.objective,
    worker_report: {
      status: r.status,
      implemented: r.implemented,
      files_changed: r.filesChanged,
      validation: r.validation,
      unresolved: r.unresolved,
      risks: r.risks,
      diff: r.diffStats,
      worker_confidence: r.workerConfidence,
    },
  };
}

/** One narrow question per criterion instead of a single "is it done?". */
export function buildGateQuestions(criteria: string[]): Record<string, Question> {
  const questions: Record<string, Question> = {
    evidence_concrete: {
      type: 'noul',
      instructions:
        'Is the worker report backed by concrete evidence (changed files and passing checks) rather than bare claims?',
    },
  };
  criteria.forEach((criterion, i) => {
    questions[`criterion_${i}`] = {
      type: 'noul',
      instructions: `Does the worker report show this acceptance criterion was met? Criterion: ${criterion}`,
    };
  });
  return questions;
}

export async function evaluateCompletion(input: GateInput, opts: GateOptions = {}): Promise<GateDecision> {
  const started = Date.now();
  const done = (d: Omit<GateDecision, 'ms'>): GateDecision => ({ ...d, ms: Date.now() - started });
  const ruled = (verdict: GateVerdict, reason: string) =>
    done({ verdict, decidedBy: 'rule', reason, criteria: [], evidenceConcrete: null });

  // Deterministic rules first: anything a rule can decide must not reach Jev.
  if (!checksGreen(input.result)) return ruled('reject', 'objective checks are not green');
  if (input.result.unresolved.length > 0) return ruled('escalate', 'worker reported unresolved items');
  if (input.highRisk) return ruled('escalate', 'high-risk task: Jev is never the sole authority');
  if (input.acceptanceCriteria.length === 0) return ruled('escalate', 'no acceptance criteria to check against');

  const threshold = opts.acceptThreshold ?? DEFAULT_ACCEPT_THRESHOLD;
  const ask = opts.ask ?? askTypeSafe;
  let answers: JevAnswers;
  try {
    answers = await ask(buildGateState(input), buildGateQuestions(input.acceptanceCriteria));
  } catch (err) {
    // Fail open to the conservative route: a Jev outage wakes the strong model, it never accepts.
    return done({
      verdict: 'escalate',
      decidedBy: 'fallback',
      reason: `jev unavailable: ${(err as Error).message}`,
      criteria: [],
      evidenceConcrete: null,
    });
  }

  const criteria = input.acceptanceCriteria.map((_, i) => answers[`criterion_${i}`]?.noul ?? 0);
  const evidenceConcrete = answers['evidence_concrete']?.noul ?? 0;
  const weakest = Math.min(evidenceConcrete, ...criteria);
  return done({
    verdict: weakest >= threshold ? 'accept' : 'escalate',
    decidedBy: 'jev',
    reason: `weakest signal ${weakest.toFixed(2)} vs threshold ${threshold}`,
    criteria,
    evidenceConcrete,
  });
}

function resolveKey(): string | undefined {
  return process.env['JEV_API_KEY'] ?? process.env['TYPESAFE_API_KEY'] ?? process.env['jev_key'];
}

const askTypeSafe: JevAsker = async (state, questions) => {
  const key = resolveKey();
  if (!key) throw new Error('no Jev API key in env');
  const res = await fetch(process.env['JEV_BASE_URL'] ?? 'https://api.typesafe.ai/v1/systemone', {
    method: 'POST',
    headers: { Authorization: `Bearer ${key}`, 'Content-Type': 'application/json' },
    body: JSON.stringify({ model: process.env['JEV_MODEL'] ?? 'jev-latest', state, questions }),
    signal: AbortSignal.timeout(5000),
  });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  const data = (await res.json()) as { answers?: JevAnswers };
  if (!data.answers) throw new Error('response without answers');
  return data.answers;
};

// --- shadow ledger -------------------------------------------------------------------------

export interface ShadowEntry {
  at: string;
  taskId: string;
  gate: GateDecision;
  /** What really happened to the task, filled in by whoever decided it (Claude or the human). */
  actual: GateVerdict | null;
}

export function recordShadow(file: string, entry: ShadowEntry): void {
  mkdirSync(dirname(file), { recursive: true });
  appendFileSync(file, `${JSON.stringify(entry)}\n`);
}

export interface ShadowReport {
  total: number;
  judged: number;
  agree: number;
  /** Gate said accept, reality said otherwise. The only disagreement that would have cost something. */
  falseAccepts: number;
  /** Tasks the gate would have closed without waking the strong model. */
  wouldHaveSaved: number;
}

export function shadowReport(file: string): ShadowReport {
  const report: ShadowReport = { total: 0, judged: 0, agree: 0, falseAccepts: 0, wouldHaveSaved: 0 };
  if (!existsSync(file)) return report;
  for (const line of readFileSync(file, 'utf8').split('\n')) {
    if (!line.trim()) continue;
    const entry = JSON.parse(line) as ShadowEntry;
    report.total++;
    if (entry.actual === null) continue;
    report.judged++;
    if (entry.gate.verdict === entry.actual) report.agree++;
    if (entry.gate.verdict === 'accept') {
      if (entry.actual === 'accept') report.wouldHaveSaved++;
      else report.falseAccepts++;
    }
  }
  return report;
}
