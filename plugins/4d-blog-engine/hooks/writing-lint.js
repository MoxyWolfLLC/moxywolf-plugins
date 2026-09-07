#!/usr/bin/env node
// PostToolUse(Write|Edit) on prose files. Two jobs, both non-mutating:
//
//   1. Baseline. On the FIRST Write of a prose file, stash a copy in a shadow
//      store. That copy is the only record of what Claude actually sampled —
//      every later Edit overwrites it in place and the baseline is gone.
//      Universal by construction: papers, emails, READMEs, posts, anything.
//      No per-skill snapshot step to add, drift out of date, or forget.
//   2. Register check. Report prose_lint's grade to stderr. Never rewrites —
//      an email has no git history to undo a silent fix from.
//
// BLOG_LINT_HOOK=off  silences both.
// PROSE_BASELINE_DIR  overrides the store (default ~/.claude/prose-baselines).
'use strict';
const { execFileSync } = require('child_process');
const crypto = require('crypto');
const path = require('path');
const os = require('os');
const fs = require('fs');

const PROSE = /\.(md|markdown|txt|tex)$/i;
// ponytail: path denylist, not content sniffing. Add entries when something noisy shows up.
const SKIP = /(^|\/)(node_modules|\.git|dist|build|vendor|__pycache__|prose-baselines)(\/|$)|\.(lock|min)\./i;
const MIN_BYTES = 400;            // below this prose_lint's metrics are noise
const PRUNE_DAYS = 90;            // ponytail: unbounded store otherwise; raise if history matters

const storeDir = () =>
  process.env.PROSE_BASELINE_DIR || path.join(os.homedir(), '.claude', 'prose-baselines');

const keyFor = (file) =>
  crypto.createHash('sha256').update(path.resolve(file)).digest('hex').slice(0, 16);

function prune(dir) {
  const cutoff = Date.now() - PRUNE_DAYS * 864e5;
  let names;
  try { names = fs.readdirSync(dir); } catch { return; }
  for (const n of names) {
    const f = path.join(dir, n);
    try { if (fs.statSync(f).mtimeMs < cutoff) fs.unlinkSync(f); } catch { /* ignore */ }
  }
}

function saveBaseline(file) {
  // A sibling *.raw.md means a pipeline already keeps its own audit-trail copy
  // (4d Phase 3 does). Don't keep a second one that can disagree with it.
  const sib = file.replace(/\.(md|markdown|txt|tex)$/i, '.raw.$1');
  if (fs.existsSync(sib)) return;

  const dir = storeDir();
  const base = path.join(dir, keyFor(file));
  if (fs.existsSync(base + '.md')) return;          // first write only
  try {
    fs.mkdirSync(dir, { recursive: true });
    fs.copyFileSync(file, base + '.md');
    fs.writeFileSync(base + '.json', JSON.stringify({
      path: path.resolve(file), captured: new Date().toISOString(),
    }));
    prune(dir);
  } catch { /* a baseline we couldn't take is not worth failing a write over */ }
}

let input = '';
process.stdin.on('data', (c) => (input += c));
process.stdin.on('end', () => {
  if (process.env.BLOG_LINT_HOOK === 'off') return;
  let file, tool;
  try {
    const d = JSON.parse(input.replace(/^﻿/, ''));
    file = d?.tool_input?.file_path;
    tool = d?.tool_name;
  } catch { return; }

  if (!file || !PROSE.test(file) || SKIP.test(file)) return;
  let bytes;
  try { bytes = fs.statSync(file).size; } catch { return; }
  if (bytes < MIN_BYTES) return;

  if (tool === 'Write') saveBaseline(file);

  const lint = path.join(__dirname, '..', 'scripts', 'prose_lint.py');
  let out;
  try {
    out = execFileSync('python3', [lint, file, '--report'], {
      encoding: 'utf8', timeout: 10000, stdio: ['ignore', 'pipe', 'ignore'],
    });
  } catch (e) {
    out = e.stdout || '';         // a non-zero exit still carries the STATUS line
  }

  const m = out.match(/GRADE=(\w+)\s+SCORE=(\d+)/);
  if (!m) return;
  const [, grade, score] = m;
  if (grade === 'A') return;      // clean: stay quiet

  console.error(
    `[prose] ${path.basename(file)} GRADE=${grade} SCORE=${score} — ` +
    `/prose-lint "${file}" --fix · /prose-survival "${file}"`
  );
});
