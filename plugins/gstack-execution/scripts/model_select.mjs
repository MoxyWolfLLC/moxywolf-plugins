#!/usr/bin/env node
// MR-001: Jev recommends the builder's model for an item, and routes only after its
// recommendations have been scored against outcomes.
//
//   model_select.mjs recommend <packet.json> [DESIGN.md]   write `model_selection` into the packet
//   model_select.mjs score --repo <path>                   read the ledger, print agreement
//
// Why a separate script: the recommendation needs a model and a network, and the dispatcher is
// stdlib Python that runs offline on purpose. `peer_review.py open` reads the field this writes and
// `record-release` appends the outcome beside it (MR-001.4); this script never touches the review.
//
// The model answers four typed questions. A rule table HERE maps the answers to a tier. The model
// never names a model: a router whose output is free text cannot be scored row by row.
//
// ponytail: one request per item, four booleans. A recommendation costs under a cent.
import fs from 'node:fs';
import path from 'node:path';
import { execFileSync } from 'node:child_process';
import { pathToFileURL } from 'node:url';
import { resolveCredential } from './packet_coverage.mjs';

const MODEL = process.env.GSTACK_COVERAGE_MODEL ?? 'typesafe-ai/jev';
export const TIERS = ['floor', 'standard', 'light'];   // most capable first; nothing selects below `light`
export const ROUTE_MIN_LINES = 20;
export const ROUTE_MIN_AGREEMENT = 0.90;

// MR-001.1: the questions, listed here and in the contract, asked verbatim.
export const QUESTIONS = {
  trust_boundary: {
    type: 'boolean',
    instructions: 'Does this item change code on a trust boundary: authentication, authorization, payment, credentials or secrets, the agent\'s GitHub token or app, a repository ruleset, a CI workflow, or anything that decides what an agent may do?',
    criteria: { true: 'At least one criterion, named path or introduced link changes such code.',
                false: 'Nothing in the item touches such code.' },
  },
  cross_file: {
    type: 'boolean',
    instructions: 'Does building this item need reasoning across more than one source file at once: a change in one file that only makes sense together with a change in another, a protocol between a writer and a reader, or a contract several files must agree on?',
    criteria: { true: 'The criteria require coordinated changes in two or more files, or a shape two or more files must agree on.',
                false: 'Each criterion can be met inside one file, or the item is not code.' },
  },
  docs_only: {
    type: 'boolean',
    instructions: 'Is this item documentation, configuration, a status line, or a version move only, with no change to executable code or tests?',
    criteria: { true: 'Every criterion is satisfied by editing prose, configuration or version strings.',
                false: 'At least one criterion changes executable code or a test.' },
  },
  has_tests: {
    type: 'boolean',
    instructions: 'Do the criteria name executable tests the build must add or make pass (a test file, a suite, a CI job that reports counts)?',
    criteria: { true: 'A criterion names a test file, suite or CI check by name.',
                false: 'No criterion names an executable test.' },
  },
};

// MR-001.2: deterministic, in this order. The first row whose condition holds fires.
export const RULES = [
  { rule: 'trust_boundary', tier: 'floor',    when: (a) => a.trust_boundary },
  { rule: 'cross_file',     tier: 'floor',    when: (a) => a.cross_file },
  { rule: 'docs_only',      tier: 'light',    when: (a) => a.docs_only && !a.has_tests },
  { rule: 'default',        tier: 'standard', when: () => true },
];

export function decide(answers) {
  const a = Object.fromEntries(Object.keys(QUESTIONS).map(k => [k, (answers[k]?.probability ?? 0) >= 0.5]));
  const row = RULES.find(r => r.when(a));
  return { tier: row.tier, rule: row.rule, booleans: a };
}

export const FILE_HEAD_LINES = 60;   // F1 (review 20261013-175825): the model reads the named files, not only their names

// F1 (review 20261013-182804): a named file is read from the packet's head commit through git, never
// from the working tree, and only as a path inside the repository. `git show <head>:<rel>` refuses
// `..`, absolute paths and anything the commit does not track, and follows no symlink out of the tree.
export function readAtHead(repoPath, head, rel) {
  if (!repoPath || !head || !/^[A-Za-z0-9_.-][A-Za-z0-9_./-]*$/.test(rel) || rel.split('/').includes('..')) return { path: rel, exists: false };
  let text;
  try {
    text = execFileSync('git', ['-C', repoPath, 'show', `${head}:${rel}`], { encoding: 'utf8', stdio: ['ignore', 'pipe', 'ignore'], maxBuffer: 16 << 20 });
  } catch { return { path: rel, exists: false }; }
  const lines = text.split('\n');
  return { path: rel, exists: true, at: head, lines: lines.length, head: lines.slice(0, FILE_HEAD_LINES).join('\n') };
}

// F2 (review 20261013-182804, round 2): an item's "Links introduced" is read from that item's own
// section only, bounded by the next heading of any level, and an item the design file does not
// declare, or declares without the line, is refused: a recommendation over inputs the contract
// names but the script did not read is not a recommendation.
export function linksIntroduced(items, designText) {
  const out = [];
  for (const item of items) {
    const esc = item.replace(/[.*+?^${}()|[\]\\\/]/g, '\\$&');
    const head = designText.match(new RegExp(`^### ${esc} [^\\n]*$`, 'm'));
    if (!head) throw new Error(`the design file declares no item ${item}`);
    const body = designText.slice(head.index + head[0].length).split(/^#{2,3} /m)[0];
    const m = body.match(/^\*\*Links introduced:\*\* ([^\n]+)/m);
    if (!m) throw new Error(`item ${item} has no "Links introduced" line in its own section`);
    out.push({ item, links_introduced: m[1].trim() });
  }
  return out;
}

// What the model reads: the criteria, the files they name (their head, at the packet's head commit,
// when that commit tracks them), and the item's "Links introduced".
export function inputsFrom(packet, designText, repoPath = packet.repos?.[0]?.path, head = packet.repos?.[0]?.head) {
  const crits = (packet.acceptance_criteria ?? []).map(c => String(c).replace(/\s+/g, ' ').trim());
  // a path is the first token inside backticks when it has a slash or an extension: `scripts/x.mjs recommend <packet>` names scripts/x.mjs
  const paths = [...new Set(crits.flatMap(c => [...c.matchAll(/`([^`]+)`/g)].map(m => m[1].trim().split(/\s+/)[0])
                                              .filter(t => /^[A-Za-z0-9_.-][A-Za-z0-9_./-]*$/.test(t) && (t.includes('/') || /\.[a-z0-9]{1,5}$/.test(t)))))];
  const files = paths.map((rel) => readAtHead(repoPath, head, rel));
  const links = linksIntroduced(packet.items ?? [], designText);
  return { items: packet.items ?? [], criteria_count: crits.length, criteria: crits, paths_named: paths,
           files_read: files.filter(f => f.exists).length, files, links_introduced: links };
}

export function repoId(repoPath) {
  const url = execFileSync('git', ['-C', repoPath, 'remote', 'get-url', 'origin'], { encoding: 'utf8' }).trim();
  const m = url.match(/github\.com[:/]([^/]+)\/([^/]+?)(?:\.git)?$/);
  if (!m) throw new Error(`${repoPath}: origin is not a github.com repository`);
  return `${m[1]}-${m[2]}`;
}

export function reviewRoot(env = process.env) {
  if (!env.GSTACK_PEER_REVIEW_DIR) throw new Error('GSTACK_PEER_REVIEW_DIR is not set; the ledger lives under the review root and nowhere else');
  return env.GSTACK_PEER_REVIEW_DIR;
}

export function ledgerPath(repoPath, env = process.env) {
  return path.join(reviewRoot(env), 'model-selection', repoId(repoPath) + '.jsonl');
}

export function readLedger(file) {
  if (!fs.existsSync(file)) return [];
  return fs.readFileSync(file, 'utf8').split('\n').filter(Boolean).map(l => JSON.parse(l));
}

// MR-001.5: cleared means at most two rounds and no blocking finding. Counted, never characterised.
// Every released line is counted per tier (F4, review 20261013-182804). Only shadow lines feed the
// route gate and `agreement` (MR-001.6 asks for shadow history): a line written in route mode ran on
// the recommended tier, so its outcome says nothing about whether the recommendation was safe.
export function scoreLines(lines) {
  const per = Object.fromEntries(TIERS.map(t => [t, { items: 0, cleared: 0, not_cleared: 0, routed: 0 }]));
  let overridden = 0, routed = 0, cheapOk = 0, cheap = 0, shadow = 0;
  for (const l of lines) {
    if (l.override) { overridden += 1; continue; }
    const t = l.recommendation?.tier;
    if (!per[t]) continue;
    const ok = (l.outcome?.rounds_used ?? 99) <= 2 && (l.outcome?.blocking_findings ?? 99) === 0;
    per[t].items += 1; per[t][ok ? 'cleared' : 'not_cleared'] += 1;
    if (l.recommendation?.mode !== 'shadow') { routed += 1; per[t].routed += 1; continue; }
    shadow += 1;
    if (t !== 'floor') { cheap += 1; if (ok) cheapOk += 1; }
  }
  const scored = shadow;
  // agreement is compared unrounded (F4: 0.8996 printed as 0.9 must not pass 0.90); printed to 3 places
  return { lines: lines.length, scored, overridden, routed, per_tier: per,
           agreement: cheap ? cheapOk / cheap : 0, cheap_recommended: cheap };
}

export function routeAllowed(summary) {
  const ok = summary.scored >= ROUTE_MIN_LINES && summary.agreement >= ROUTE_MIN_AGREEMENT;
  return { ok, lines: summary.scored, agreement: Number(summary.agreement.toFixed(3)), needs_lines: ROUTE_MIN_LINES, needs_agreement: ROUTE_MIN_AGREEMENT };
}

// MR-001.4: a review that never reached record-release has no line. The score names how many such
// reviews of this repository exist under the review root, so a thin ledger is not read as a full one.
export function openReviews(repoPath, ledgerLines, env = process.env) {
  const root = reviewRoot(env);
  const seen = new Set(ledgerLines.map(l => l.review_id));
  let skipped = 0;
  let dirs = [];
  try { dirs = fs.readdirSync(root); } catch { return 0; }
  for (const d of dirs) {
    const pf = path.join(root, d, 'packet.json');
    if (!fs.existsSync(pf) || seen.has(d)) continue;
    let pk;
    try { pk = JSON.parse(fs.readFileSync(pf, 'utf8')); } catch { continue; }
    if (pk.model_selection?.status === 'checked' && (pk.repos ?? []).some(r => path.resolve(r.path) === path.resolve(repoPath))) skipped += 1;
  }
  return skipped;
}

function printScore(s, file, skipped) {
  console.log(`ledger ${file}: ${s.lines} lines, ${s.scored} scored (shadow), ${s.overridden} overridden, ${s.routed} routed, ${skipped} open or abandoned reviews skipped`);
  for (const t of TIERS) {
    const p = s.per_tier[t];
    console.log(`  ${t.padEnd(8)} ${p.items} items, ${p.cleared} cleared in at most 2 rounds with no blocking finding, ${p.not_cleared} did not, ${p.routed} of them routed`);
  }
  console.log(`agreement ${Number(s.agreement.toFixed(3))} over ${s.cheap_recommended} standard/light recommendations`);
}

async function recommend(packetPath, designPath) {
  // F2 (review 20261013-182804): without the design file the item's "Links introduced" is never read,
  // and a recommendation over fewer inputs than the contract names is not a recommendation.
  if (!designPath || !fs.existsSync(designPath)) {
    console.error('usage: model_select.mjs recommend <packet.json> <DESIGN.md | goals/<id>/PLAN.md>  (the design file is required: it carries the item\'s Links introduced)');
    process.exit(2);
  }
  const packet = JSON.parse(fs.readFileSync(packetPath, 'utf8'));
  const prior = packet.model_selection ?? {};
  const override = prior.override;
  if (override !== undefined) {
    // MR-001.7: a person's override wins, is recorded, and may not go below `light`.
    if (!override || !TIERS.includes(override.tier) || !String(override.reason ?? '').trim()) {
      console.error(`model_selection.override must be {tier: one of ${TIERS.join('|')}, reason}; got ${JSON.stringify(override)}`);
      process.exit(2);
    }
  }
  const designText = fs.readFileSync(designPath, 'utf8');
  let inputs;
  try { inputs = inputsFrom(packet, designText); } catch (e) { console.error(`model selection refused: ${e.message}`); process.exit(2); }
  const wanted = process.env.GSTACK_MODEL_ROUTING === 'route' ? 'route' : 'shadow';
  const write = (fields) => {
    packet.model_selection = { model: MODEL, checked_at: new Date().toISOString(), inputs, ...fields,
                               ...(override !== undefined ? { override } : {}),
                               declared_tier: prior.declared_tier ?? null,
                               // MR-001.6 as amended: who applied the tier. An interactive session takes it as advice;
                               // a runner that starts the builder on it writes `launched`. Nothing launches today.
                               routing: prior.routing === 'launched' ? 'launched' : 'advice' };
    fs.writeFileSync(packetPath, JSON.stringify(packet, null, 2) + '\n');
  };

  // MR-001.6: route only on a scored history. Checked before the model is asked, so a refusal costs nothing.
  let mode = wanted, route_refused = null;
  if (wanted === 'route') {
    const file = ledgerPath(packet.repos[0].path);
    const gate = routeAllowed(scoreLines(readLedger(file)));
    if (!gate.ok) {
      mode = 'shadow';
      route_refused = { reason: 'insufficient_history', ...gate, ledger: file };
      console.error(`route refused: insufficient_history (${gate.lines} scored lines, agreement ${gate.agreement}; needs ${gate.needs_lines} at ${gate.needs_agreement}). Running in shadow mode.`);
    }
  }

  let ai;
  try { ai = await import('ai'); } catch (e) {
    write({ status: 'broken', mode, why: `the selector could not load its dependency \`ai\`: ${e.code ?? ''} ${e.message}`.trim() });
    console.error("model selection broken: `ai` did not load. Run `npm ci` in plugins/gstack-execution.");
    process.exit(3);
  }
  const cred = resolveCredential();
  if (!cred.key) {
    write({ status: cred.status, mode, why: cred.why, consulted: cred.consulted });
    console.error(`model selection ${cred.status}: ${cred.why}`);
    process.exit(cred.status === 'unavailable' ? 0 : 4);
  }
  process.env.AI_GATEWAY_API_KEY = cred.key;
  const model = process.env.JEV_ENDPOINT
    ? ai.createGateway({ baseURL: process.env.JEV_ENDPOINT }).evaluationModel(MODEL)
    : MODEL;
  let r;
  try {
    r = await ai.experimental_evaluate({ model, state: inputs, questions: QUESTIONS, maxRetries: 1 });
  } catch (e) {
    write({ status: 'unusable', mode, why: `the gateway refused or failed the call: ${e.message}`, credential_source: cred.source });
    console.error(`model selection unusable: ${e.message}`);
    process.exit(4);
  }
  const d = decide(r.answers ?? {});
  const applied = override ? override.tier : d.tier;
  write({ status: 'checked', mode, answers: r.answers, booleans: d.booleans, rule: d.rule, tier: d.tier,
          applied_tier: applied, credential_source: cred.source, input_tokens: r.usage?.inputTokens ?? 0,
          ...(route_refused ? { route_refused } : {}) });
  console.log(`model selection (${mode}): tier ${d.tier} by rule ${d.rule}` +
              (override ? `; override to ${override.tier}: ${override.reason}` : '') +
              `\n  ${Object.entries(d.booleans).map(([k, v]) => `${k}=${v}`).join('  ')}`);
  process.exit(route_refused ? 5 : 0);
}

async function main() {
  const [cmd, ...rest] = process.argv.slice(2);
  if (cmd === 'recommend' && rest[0]) return recommend(rest[0], rest[1]);
  if (cmd === 'score') {
    const i = rest.indexOf('--repo');
    if (i < 0 || !rest[i + 1]) { console.error('usage: model_select.mjs score --repo <path>'); process.exit(2); }
    const file = ledgerPath(rest[i + 1]);
    const lines = readLedger(file);
    printScore(scoreLines(lines), file, openReviews(rest[i + 1], lines));
    return;
  }
  console.error('usage: model_select.mjs recommend <packet.json> [DESIGN.md] | score --repo <path>');
  process.exit(2);
}

if (process.argv[1] && import.meta.url === pathToFileURL(fs.realpathSync(process.argv[1])).href) await main();
