#!/usr/bin/env node
// PostToolUse(Write|Edit) → report-only register check on prose files.
// Report-only by design: an email has no git history to undo a silent rewrite from.
// Set BLOG_LINT_HOOK=off to silence.
'use strict';
const { execFileSync } = require('child_process');
const path = require('path');
const fs = require('fs');

const PROSE = /\.(md|markdown|txt)$/i;
// ponytail: path denylist, not content sniffing. Add entries when something noisy shows up.
const SKIP = /(^|\/)(node_modules|\.git|dist|build|vendor|__pycache__)(\/|$)|\.(lock|min)\./i;
const MIN_BYTES = 400;   // below this, prose_lint's metrics are noise

let input = '';
process.stdin.on('data', (c) => (input += c));
process.stdin.on('end', () => {
  if (process.env.BLOG_LINT_HOOK === 'off') return;
  let file;
  try {
    const d = JSON.parse(input.replace(/^﻿/, ''));
    file = d?.tool_input?.file_path;
  } catch { return; }

  if (!file || !PROSE.test(file) || SKIP.test(file)) return;
  let bytes;
  try { bytes = fs.statSync(file).size; } catch { return; }
  if (bytes < MIN_BYTES) return;

  const lint = path.join(__dirname, '..', 'scripts', 'prose_lint.py');
  let out;
  try {
    // Capture stdout only; a lint failure is a finding, not a hook error.
    out = execFileSync('python3', [lint, file, '--report'], {
      encoding: 'utf8', timeout: 10000, stdio: ['ignore', 'pipe', 'ignore'],
    });
  } catch (e) {
    out = e.stdout || '';           // non-zero exit still carries the STATUS line
  }

  const m = out.match(/GRADE=(\w+)\s+SCORE=(\d+)/);
  if (!m) return;
  const [, grade, score] = m;
  if (grade === 'A') return;        // clean: stay quiet

  console.error(
    `[prose] ${path.basename(file)} GRADE=${grade} SCORE=${score} — ` +
    `run /prose-lint "${file}" --fix to apply the deterministic fixes.`
  );
});
