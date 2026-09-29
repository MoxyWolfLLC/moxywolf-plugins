#!/usr/bin/env node
// XE-010: score a review packet's acceptance criteria against the criteria DESIGN.md declares,
// and write the result into the packet for peer_review.py to gate on.
//
// Why this is a separate script and not part of the dispatcher: scoring needs a model and a
// network. The dispatcher is stdlib Python and runs offline on purpose, so it reads a report it
// never produces. That also keeps the gate free and testable when this has not run.
//
// The packet must declare `items`: the DESIGN.md items this checkpoint claims. It is NOT inferred
// from the packet's prose. Inferring it from the outcome string is exactly how the first run of
// this experiment mis-mapped two reviews -- packets get reused and their prose goes stale, while
// an explicit list cannot drift silently.
//
// ponytail: one boolean question per declared criterion, batched one request per item because
// several questions can share a state. 45 criteria cost $0.0005 and 19s.
//
// XE-014: `ai` is imported dynamically, after the packet is read, so a scorer that cannot load its
// dependency writes `broken` into the packet instead of dying at a static import with nothing
// recorded. That static import was the state every run was in from 2026-09-18 to 2026-09-29.
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { pathToFileURL } from 'node:url';

const MODEL = process.env.GSTACK_COVERAGE_MODEL ?? 'typesafe-ai/jev';

function declaredCriteria(designPath) {
  const design = fs.readFileSync(designPath, 'utf8');
  const items = {};
  // Stop at the next heading of ANY level, so a criterion cannot swallow the following section.
  // `$(?![\s\S])` is end-of-INPUT. The first version wrote `\Z`, which is a Python and PCRE
  // anchor: JavaScript reads it as a literal "Z", so the final criterion of every item failed to
  // match and was dropped in silence. The scorer then reported "0 below 0.5" over input it had
  // never examined -- and the one criterion it existed to catch, XE-005 #6, was among the dropped.
  // A false pass over unexamined input, inside the check built to prevent exactly that.
  const END = '$(?![\\s\\S])';
  const itemRe = new RegExp(`^### ([A-Z]{2}-\\d+) — (.+?)$([\\s\\S]*?)(?=^#{2,3} |${END})`, 'gm');
  for (const m of design.matchAll(itemRe)) {
    const body = m[3];
    const critRe = new RegExp(`^\\d+\\.\\s+([\\s\\S]+?)(?=^\\d+\\.\\s|\\n\\n\\*\\*|\\n\\n##|${END})`, 'gm');
    const crits = [...body.matchAll(critRe)]
      .map(c => c[1].replace(/\s+/g, ' ').trim())
      .filter(Boolean);

    // EV-001 applied to this extractor: a second, independent count must agree. One regex deciding
    // alone is how the last criterion vanished without anything noticing.
    const counted = (body.match(/^\d+\.\s/gm) ?? []).length;
    if (crits.length !== counted) {
      console.error(`DESIGN.md ${m[1]}: extractor found ${crits.length} criteria but ${counted} are numbered.`);
      console.error('Refusing to score a partial item: a check over input it did not examine cannot pass.');
      process.exit(2);
    }
    if (crits.length) items[m[1]] = { title: m[2].trim(), declared: crits };
  }
  return items;
}

// XE-014 criteria 3, 4, 7 and 8. The order is DR-010's: a set variable wins, then the file
// GSTACK_AIGATEWAY_ENV names, then the vault's own path on a Mac. Every step tried is named in
// `consulted`, so a record that says "no key" also says where nobody found one.
const VAULT_TAIL = ['Shared drives', 'MoxyWolf Shared Files', 'MoxyWolf Vault', '_Shared Knowledge',
                    'Agents and Plugins', 'aigateway.env'];

export function keyFromEnvFile(text) {
  // Split, never read line by line: aigateway.env has no trailing newline, and a POSIX
  // `while read` loop reads zero lines from it (criterion 8).
  for (const raw of text.split(/\r?\n/)) {
    const m = raw.trim().match(/^(?:export\s+)?AI_GATEWAY_API_KEY\s*=\s*(.*)$/);
    if (m) return m[1].trim().replace(/^(['"])(.*)\1$/, '$2') || null;
  }
  return null;
}

function vaultCandidates() {
  const cloud = path.join(os.homedir(), 'Library', 'CloudStorage');
  let dirs = [];
  try { dirs = fs.readdirSync(cloud).filter(d => d.startsWith('GoogleDrive-')).sort(); } catch { /* no such dir */ }
  return dirs.length ? dirs.map(d => path.join(cloud, d, ...VAULT_TAIL))
                     : [path.join(cloud, 'GoogleDrive-*', ...VAULT_TAIL)];
}

export function resolveCredential(env = process.env) {
  const consulted = ['env AI_GATEWAY_API_KEY'];
  if (env.AI_GATEWAY_API_KEY) return { key: env.AI_GATEWAY_API_KEY, source: 'env AI_GATEWAY_API_KEY', consulted };

  const fromFile = (file, source) => {
    consulted.push(file);
    let text;
    try { text = fs.readFileSync(file, 'utf8'); } catch (e) {
      return { status: 'unusable', why: `${source} names ${file}, which could not be read (${e.code})`, consulted };
    }
    const key = keyFromEnvFile(text);
    return key ? { key, source: file, consulted }
               : { status: 'unusable', why: `${file} sets no AI_GATEWAY_API_KEY`, consulted };
  };

  if (env.GSTACK_AIGATEWAY_ENV) {
    consulted.push('env GSTACK_AIGATEWAY_ENV');
    return fromFile(env.GSTACK_AIGATEWAY_ENV, 'GSTACK_AIGATEWAY_ENV');
  }
  consulted.push('env GSTACK_AIGATEWAY_ENV');
  for (const file of vaultCandidates()) {
    if (fs.existsSync(file)) return fromFile(file, 'the vault path');
    consulted.push(file);
  }
  return { status: 'unavailable', why: 'no AI_GATEWAY_API_KEY on any path', consulted };
}

async function main() {
  const [packetPath, designPath] = process.argv.slice(2);
  if (!packetPath || !designPath) {
    console.error('usage: packet_coverage.mjs <packet.json> <DESIGN.md>');
    process.exit(2);
  }
  const packet = JSON.parse(fs.readFileSync(packetPath, 'utf8'));
  const claimed = packet.items;
  if (!Array.isArray(claimed) || !claimed.length) {
    console.error('packet has no `items` array naming the DESIGN.md items it claims.');
    console.error('Add one. It is not inferred from prose: reused packets carry stale outcomes.');
    process.exit(2);
  }

  const write = (report) => {
    packet.coverage = { model: MODEL, checked_at: new Date().toISOString(), ...report };
    fs.writeFileSync(packetPath, JSON.stringify(packet, null, 2) + '\n');
  };

  let ai;
  try {
    ai = await import('ai');
  } catch (e) {
    write({ status: 'broken', why: `the scorer could not load its dependency \`ai\`: ${e.code ?? ''} ${e.message}`.trim(),
            consulted: [`import 'ai', resolved upward from ${path.dirname(new URL(import.meta.url).pathname)}`] });
    console.error("coverage broken: `ai` did not load. Run `npm ci` in plugins/gstack-execution.");
    process.exit(3);
  }

  const cred = resolveCredential();
  if (!cred.key) {
    write({ status: cred.status, why: cred.why, consulted: cred.consulted });
    console.error(`coverage ${cred.status}: ${cred.why}\n  consulted: ${cred.consulted.join(' | ')}`);
    // unavailable exits 0: `release` is what refuses it (XE-014 criterion 5), not the scorer
    process.exit(cred.status === 'unavailable' ? 0 : 4);
  }
  // The AI SDK reads the variable itself; the key is never passed as an argument.
  process.env.AI_GATEWAY_API_KEY = cred.key;
  // JEV_ENDPOINT points the gateway at another base URL: a stub in CI (criterion 11).
  const model = process.env.JEV_ENDPOINT
    ? ai.createGateway({ baseURL: process.env.JEV_ENDPOINT }).evaluationModel(MODEL)
    : MODEL;

  const items = declaredCriteria(designPath);
  const missing = claimed.filter(i => !items[i]);
  if (missing.length) {
    console.error(`DESIGN.md declares no criteria for: ${missing.join(', ')}`);
    process.exit(2);
  }

  const scored = [];
  let inTok = 0;
  for (const item of claimed) {
    const questions = {};
    items[item].declared.forEach((c, i) => {
      questions[`c${i + 1}`] = {
        type: 'boolean',
        instructions: `Does at least one of the packet acceptance criteria actually test this declared requirement? Judge substance, not wording. DECLARED REQUIREMENT: ${c}`,
        criteria: {
          true: 'Some packet criterion tests substantially what this declared requirement states, so a review against this packet would examine it.',
          false: 'No packet criterion tests it. A review against this packet could return a clean pass while this declared requirement remains unbuilt.',
        },
      };
    });
    let r;
    try {
      r = await ai.experimental_evaluate({
        model,
        state: { packet_acceptance_criteria: packet.acceptance_criteria },
        questions,
        maxRetries: 1,
      });
    } catch (e) {
      // ponytail: every failed call reads as unusable (bad key, gateway down, bad endpoint alike).
      // Split them when a reader needs to tell a revoked key from an outage.
      write({ status: 'unusable', why: `the gateway refused or failed the call: ${e.message}`,
              credential_source: cred.source, consulted: cred.consulted });
      console.error(`coverage unusable: ${e.message}`);
      process.exit(4);
    }
    inTok += r.usage?.inputTokens ?? 0;
    items[item].declared.forEach((c, i) => {
      scored.push({ item, criterion_no: i + 1, declared: c,
                    probability: r.answers[`c${i + 1}`]?.probability });
    });
  }

  write({ status: 'checked', credential_source: cred.source, input_tokens: inTok, criteria: scored });

  const low = scored.filter(c => (c.probability ?? 0) < 0.5);
  for (const c of scored) {
    console.log(`  ${c.item} #${c.criterion_no}  p=${c.probability}${(c.probability ?? 0) < 0.5 ? '  <-- not covered' : ''}`);
  }
  console.log(`\n${scored.length} declared criteria scored, ${low.length} below 0.5, ${inTok} input tokens`);
  process.exit(low.length ? 1 : 0);
}

// Run only as a script, so tests can import the resolver without scoring anything.
if (process.argv[1] && import.meta.url === pathToFileURL(fs.realpathSync(process.argv[1])).href) await main();
