#!/usr/bin/env node
// ponytail — UserPromptSubmit hook to track which ponytail mode is active
// Inspects user input for /ponytail commands and writes mode to flag file

const { getDefaultMode, isDeactivationCommand } = require('./ponytail-config');
const { getPonytailInstructions } = require('./ponytail-instructions');
const {
  clearMode,
  hasInjected,
  markInjected,
  setMode,
  writeHookOutput,
} = require('./ponytail-runtime');

let input = '';
process.stdin.on('data', chunk => { input += chunk; });
process.stdin.on('end', () => {
  try {
    // Strip UTF-8 BOM some shells prepend when piping (breaks JSON.parse)
    const data = JSON.parse(input.replace(/^\uFEFF/, ''));
    const prompt = (data.prompt || '').trim().toLowerCase();
    const sessionId = typeof data.session_id === 'string' ? data.session_id : '';
    let handled = false;

    // Match /ponytail commands
    if (/^[/@$]ponytail/.test(prompt)) {
      const parts = prompt.split(/\s+/);
      const cmd = parts[0].replace(/^[@$]/, '/');
      const arg = parts[1] || '';

      let mode = null;

      if (cmd === '/ponytail-review' || cmd === '/ponytail:ponytail-review') {
        mode = 'review';
      } else if (cmd === '/ponytail' || cmd === '/ponytail:ponytail') {
        if (arg === 'lite') mode = 'lite';
        else if (arg === 'full') mode = 'full';
        else if (arg === 'ultra') mode = 'ultra';
        else if (arg === 'off') mode = 'off';
        else mode = getDefaultMode();
      }

      if (mode && mode !== 'off') {
        handled = true;
        setMode(mode);
        markInjected(sessionId);
        writeHookOutput(
          'UserPromptSubmit',
          mode,
          'PONYTAIL MODE CHANGED — level: ' + mode,
        );
      } else if (mode === 'off') {
        handled = true;
        clearMode();
        markInjected(sessionId);
        writeHookOutput('UserPromptSubmit', 'off', 'PONYTAIL MODE OFF');
      }
    }

    // Detect deactivation
    if (!handled && isDeactivationCommand(prompt)) {
      handled = true;
      clearMode();
      markInjected(sessionId);
      writeHookOutput('UserPromptSubmit', 'off', 'PONYTAIL MODE OFF');
    }

    // First-prompt fallback: in cloud (Cowork) sessions the SessionStart hook
    // never runs (plugins register after it fires), so a session can reach its
    // first prompt without the ruleset. Deliver it here, once. Without a
    // session_id there is no way to say "once", so stay silent rather than
    // repeat the block on every turn.
    if (!handled && sessionId && !hasInjected(sessionId)) {
      const mode = getDefaultMode();
      if (mode !== 'off') {
        setMode(mode);
        markInjected(sessionId);
        writeHookOutput('UserPromptSubmit', mode, getPonytailInstructions(mode));
      } else {
        markInjected(sessionId);
      }
    }
  } catch (e) {
    // Silent fail
  }
});
