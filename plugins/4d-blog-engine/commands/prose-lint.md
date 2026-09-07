---
description: "Run the anti-slop linter on any file — email, README, post, paper. Report by default, --fix applies the deterministic repairs. Usage: /prose-lint <path|glob> [--fix]"
argument-hint: "<path|glob> [--fix]"
allowed-tools: ["Read", "Bash", "Glob"]
---

Run `${CLAUDE_PLUGIN_ROOT}/scripts/prose_lint.py` on the path(s) the user gave.

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/prose_lint.py" <file> --report       # default
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/prose_lint.py" <file> --fix          # apply
```

A glob expands to a loop, one invocation per file, and the run reports a per-file
grade table rather than a wall of output.

**Report is the default.** `--fix` only ever applies the two deterministic repairs
— em-dash to spaced en-dash, straight quotes to typographer's — and only outside
code fences, script blocks and inline code. Everything else the linter finds stays
advisory, because it needs a human judgement the script does not have.

**Read the writer's voice profile first** and pass any devices it declares as
signature moves:

```bash
--signature-devices contrast-framing,three-beat-reveal
```

Skipping that flag silently re-applies the raw-count rule the density allowance
exists to replace, and a piece in the writer's own voice fails structurally. This
is the same footgun documented in `feedback_slop_catalog_miscalibrated_for_dorian_longform`.

For a file with no git history behind it — an email, a pasted draft — say what
`--fix` will change before running it. There is nothing to undo from.
