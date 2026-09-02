const fs = require('fs');
const path = require('path');
const { getClaudeDir } = require('./ponytail-config');

const STATE_FILE = '.ponytail-active';
const isCopilot = Boolean(process.env.COPILOT_PLUGIN_DATA);
const isCodex = !isCopilot && Boolean(process.env.PLUGIN_DATA);

let stateDir = getClaudeDir();
if (isCodex) stateDir = process.env.PLUGIN_DATA;
if (isCopilot) stateDir = process.env.COPILOT_PLUGIN_DATA;

const statePath = path.join(stateDir, STATE_FILE);

// Once-per-session delivery marker. In cloud (Cowork) sessions the synced
// plugins register their hooks several seconds AFTER SessionStart has fired
// (observed 2026-09-02), so the activate hook never runs there; the
// UserPromptSubmit tracker delivers the ruleset on the first prompt instead.
// The marker, keyed on session_id, keeps that to exactly once either way.
const MARKER_DIR = process.env.CLAUDE_PLUGIN_DATA || stateDir;

function markerPath(sessionId) {
  return path.join(MARKER_DIR,
    '.ponytail-injected-' + String(sessionId).replace(/[^A-Za-z0-9_.-]/g, '_'));
}

function hasInjected(sessionId) {
  if (!sessionId) return false;
  try { return fs.existsSync(markerPath(sessionId)); } catch (e) { return false; }
}

function markInjected(sessionId) {
  if (!sessionId) return;
  try {
    fs.mkdirSync(MARKER_DIR, { recursive: true });
    fs.writeFileSync(markerPath(sessionId), new Date().toISOString());
    const cutoff = Date.now() - 24 * 60 * 60 * 1000;
    for (const name of fs.readdirSync(MARKER_DIR)) {
      if (!name.startsWith('.ponytail-injected-')) continue;
      const f = path.join(MARKER_DIR, name);
      try { if (fs.statSync(f).mtimeMs < cutoff) fs.unlinkSync(f); } catch (e) {}
    }
  } catch (e) {
    // best effort — a missing marker only risks a repeat, never a silence
  }
}

// Read the hook payload from stdin without hanging on hosts that pipe nothing.
function readStdinJson(cb) {
  let input = '';
  let done = false;
  const finish = () => {
    if (done) return;
    done = true;
    let data = {};
    try { data = JSON.parse(input.replace(/^\uFEFF/, '')); } catch (e) {}
    cb(data || {});
  };
  try {
    process.stdin.setEncoding('utf8');
    process.stdin.on('data', chunk => { input += chunk; });
    process.stdin.on('end', finish);
    process.stdin.on('error', finish);
    setTimeout(finish, 1500).unref();
    process.stdin.resume();
  } catch (e) {
    finish();
  }
}

function setMode(mode) {
  fs.mkdirSync(path.dirname(statePath), { recursive: true });
  fs.writeFileSync(statePath, mode);
}

function clearMode() {
  try { fs.unlinkSync(statePath); } catch (e) {}
}

// Live mode written by activate/mode-tracker. Absent flag = ponytail off.
function readMode() {
  try {
    return fs.readFileSync(statePath, 'utf8').trim() || null;
  } catch (e) {
    return null;
  }
}

function writeHookOutput(event, mode, context = '') {
  if (isCopilot) {
    // Copilot reads additionalContext on SessionStart; ignores output elsewhere.
    process.stdout.write(JSON.stringify(
      event === 'SessionStart' && context ? { additionalContext: context } : {}));
    return;
  }
  if (isCodex) {
    const output = { systemMessage: `PONYTAIL:${mode.toUpperCase()}` };
    if (context) {
      output.hookSpecificOutput = {
        hookEventName: event,
        additionalContext: context,
      };
    }
    process.stdout.write(JSON.stringify(output));
    return;
  }
  // Native Claude: SessionStart accepts raw stdout, but SubagentStart needs the
  // hookSpecificOutput JSON form or the context is dropped.
  if (event === 'SubagentStart') {
    process.stdout.write(JSON.stringify(
      { hookSpecificOutput: { hookEventName: event, additionalContext: context } }));
    return;
  }
  process.stdout.write(context);
}

module.exports = {
  clearMode,
  hasInjected,
  isCodex,
  isCopilot,
  markInjected,
  readMode,
  readStdinJson,
  setMode,
  writeHookOutput,
};
