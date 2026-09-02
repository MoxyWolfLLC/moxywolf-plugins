#!/usr/bin/env node
// gstack-execution — verification discipline, injected once per session.
//
// A SKILL.md section only reaches Claude if that skill is invoked. Every
// mistake these checks describe was made WITHOUT invoking gstack-execution,
// so documenting them there would not have prevented one of them. A hook
// fires whether or not anything thinks to read it — which is the entire
// reason this file exists rather than another paragraph in the skill.
//
// Three entry points, one delivery:
//   (no arg)   SessionStart      — the normal path. Emits the checks.
//   subagent   SubagentStart     — emits the checks to the subagent.
//   prompt     UserPromptSubmit  — the fallback. In cloud (Cowork) sessions the
//              synced plugins finish registering their hooks several seconds
//              AFTER SessionStart has already fired (observed 2026-09-02:
//              SessionStart at +0.0s, "Registered 5 hooks from 46 plugins" at
//              +7.8s), so the SessionStart hook never runs there. The first
//              user prompt does run this hook, so it delivers the checks then.
//
// "Once" is enforced with a marker file keyed on the session id, so a session
// that DID get the block at start never gets it twice, and the prompt path
// never repeats it on every turn.
//
// Output contract (matching ponytail's, which is the working reference):
//   native Claude SessionStart / UserPromptSubmit — raw stdout is the context
//   native Claude SubagentStart                   — hookSpecificOutput JSON
//   Codex                                          — systemMessage + hookSpecificOutput
//   Copilot                                        — additionalContext on SessionStart only
//
// Never blocks a session: any failure exits 0 having said nothing.

const fs = require('fs');
const os = require('os');
const path = require('path');

const MODE = process.argv[2];
const EVENT =
  MODE === 'subagent' ? 'SubagentStart' :
  MODE === 'prompt' ? 'UserPromptSubmit' :
  'SessionStart';
const isCodex = !!process.env.CODEX_HOME || process.env.CLAUDE_CODE_HOST === 'codex';
const isCopilot = process.env.CLAUDE_CODE_HOST === 'copilot';

const CHECKS = path.join(
  __dirname, '..', 'skills', 'gstack-execution', 'references', 'verification-checks.md',
);

// Marker directory: the plugin's data dir when the host provides one, else a
// per-user temp dir. Markers are tiny and keyed by session id; stale ones are
// harmless and get swept when older than a day.
const MARKER_DIR =
  process.env.CLAUDE_PLUGIN_DATA ||
  path.join(os.tmpdir(), 'gstack-execution-' + (os.userInfo().username || 'user'));

function markerPath(sessionId) {
  return path.join(MARKER_DIR, sessionId.replace(/[^A-Za-z0-9_.-]/g, '_') + '.injected');
}

function alreadyInjected(sessionId) {
  try { return fs.existsSync(markerPath(sessionId)); } catch { return false; }
}

function markInjected(sessionId) {
  try {
    fs.mkdirSync(MARKER_DIR, { recursive: true });
    fs.writeFileSync(markerPath(sessionId), new Date().toISOString());
    sweepStale();
  } catch {
    // best effort — a missing marker only risks a repeat, never a silence
  }
}

function sweepStale() {
  try {
    const cutoff = Date.now() - 24 * 60 * 60 * 1000;
    for (const name of fs.readdirSync(MARKER_DIR)) {
      const p = path.join(MARKER_DIR, name);
      try { if (fs.statSync(p).mtimeMs < cutoff) fs.unlinkSync(p); } catch {}
    }
  } catch {}
}

function readStdin(cb) {
  let input = '';
  let done = false;
  const finish = () => { if (!done) { done = true; cb(input); } };
  try {
    process.stdin.setEncoding('utf8');
    process.stdin.on('data', (chunk) => { input += chunk; });
    process.stdin.on('end', finish);
    process.stdin.on('error', finish);
    // Hosts that do not pipe a payload never close stdin; do not hang on them.
    setTimeout(finish, 1500).unref();
    process.stdin.resume();
  } catch {
    finish();
  }
}

function emit(context) {
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
}

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

if (EVENT === 'SubagentStart') {
  // Subagents are fresh contexts; always deliver, no marker.
  emit(context);
  process.exit(0);
}

readStdin((raw) => {
  let sessionId = '';
  try {
    // Strip a UTF-8 BOM some shells prepend when piping (breaks JSON.parse)
    const data = JSON.parse(raw.replace(/^\uFEFF/, ''));
    sessionId = typeof data.session_id === 'string' ? data.session_id : '';
  } catch {
    // no payload — SessionStart still emits; the prompt path stays silent
  }

  if (EVENT === 'UserPromptSubmit') {
    // Fallback only: without a session id there is no way to say "once", and
    // repeating the block on every turn is worse than relying on SessionStart.
    if (!sessionId || alreadyInjected(sessionId)) process.exit(0);
    emit(context);
    markInjected(sessionId);
    process.exit(0);
  }

  // SessionStart
  emit(context);
  if (sessionId) markInjected(sessionId);
  process.exit(0);
});
