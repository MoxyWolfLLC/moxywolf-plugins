#!/usr/bin/env node
// gstack-execution — verification discipline, injected at session start.
//
// A SKILL.md section only reaches Claude if that skill is invoked. Every
// mistake these checks describe was made WITHOUT invoking gstack-execution,
// so documenting them there would not have prevented one of them. A hook
// fires whether or not anything thinks to read it — which is the entire
// reason this file exists rather than another paragraph in the skill.
//
// Output contract (matching ponytail's, which is the working reference):
//   native Claude SessionStart  — raw stdout is the injected context
//   native Claude SubagentStart — must be the hookSpecificOutput JSON form
//   Codex                       — systemMessage + hookSpecificOutput
//   Copilot                     — additionalContext on SessionStart only
//
// Never blocks a session: any failure exits 0 having said nothing.

const fs = require('fs');
const path = require('path');

const EVENT = process.argv[2] === 'subagent' ? 'SubagentStart' : 'SessionStart';
const isCodex = !!process.env.CODEX_HOME || process.env.CLAUDE_CODE_HOST === 'codex';
const isCopilot = process.env.CLAUDE_CODE_HOST === 'copilot';

const CHECKS = path.join(
  __dirname, '..', 'skills', 'gstack-execution', 'references', 'verification-checks.md',
);

let body = '';
try {
  body = fs.readFileSync(CHECKS, 'utf8').trim();
} catch {
  process.exit(0); // canonical file missing or unreadable — stay silent
}
if (!body) process.exit(0);

const context =
  'VERIFICATION DISCIPLINE ACTIVE — gstack-execution.\n' +
  'These are checks, not values. Apply them before claiming anything works.\n\n' +
  body;

try {
  if (isCopilot) {
    process.stdout.write(JSON.stringify(
      EVENT === 'SessionStart' ? { additionalContext: context } : {}));
  } else if (isCodex) {
    process.stdout.write(JSON.stringify({
      systemMessage: 'VERIFY:ACTIVE',
      hookSpecificOutput: { hookEventName: EVENT, additionalContext: context },
    }));
  } else if (EVENT === 'SubagentStart') {
    process.stdout.write(JSON.stringify({
      hookSpecificOutput: { hookEventName: EVENT, additionalContext: context },
    }));
  } else {
    process.stdout.write(context);
  }
} catch {
  // best effort — never block a session on this
}
process.exit(0);
