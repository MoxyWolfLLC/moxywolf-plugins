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
import { experimental_evaluate as evaluate } from 'ai';
import fs from 'node:fs';
import path from 'node:path';

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

  const key = process.env.AI_GATEWAY_API_KEY;
  const write = (report) => {
    packet.coverage = report;
    fs.writeFileSync(packetPath, JSON.stringify(packet, null, 2) + '\n');
  };
  if (!key) {
    // unavailable is recorded, never silently treated as covered
    write({ status: 'unavailable', why: 'AI_GATEWAY_API_KEY is not set', model: MODEL,
            checked_at: new Date().toISOString() });
    console.error('no AI_GATEWAY_API_KEY; recorded coverage as unavailable (the review may still open)');
    process.exit(0);
  }

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
    const r = await evaluate({
      model: MODEL,
      state: { packet_acceptance_criteria: packet.acceptance_criteria },
      questions,
    });
    inTok += r.usage?.inputTokens ?? 0;
    items[item].declared.forEach((c, i) => {
      scored.push({ item, criterion_no: i + 1, declared: c,
                    probability: r.answers[`c${i + 1}`]?.probability });
    });
  }

  write({ status: 'checked', model: MODEL, checked_at: new Date().toISOString(),
          input_tokens: inTok, criteria: scored });

  const low = scored.filter(c => (c.probability ?? 0) < 0.5);
  for (const c of scored) {
    console.log(`  ${c.item} #${c.criterion_no}  p=${c.probability}${(c.probability ?? 0) < 0.5 ? '  <-- not covered' : ''}`);
  }
  console.log(`\n${scored.length} declared criteria scored, ${low.length} below 0.5, ${inTok} input tokens`);
  process.exit(low.length ? 1 : 0);
}

await main();
