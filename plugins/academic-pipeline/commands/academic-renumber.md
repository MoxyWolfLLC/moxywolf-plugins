---
description: Renumber a finished paper's Vancouver citations by first appearance and reorder its reference list (rerunnable after any edit)
argument-hint: [path to the paper .md] [--check]
---

Run the **renumber mode** of the `bibliography-generator` skill on the paper in `$ARGUMENTS` (or the paper open in this session).

1. Run the bundled pass in report mode first and show the mapping: `python3 "${CLAUDE_PLUGIN_ROOT}/skills/bibliography-generator/scripts/renumber_citations.py" <paper>`.
2. If it refuses (a cited number with no entry, or an entry never cited), fix the list or the citation and rerun; never patch numbers by hand.
3. Apply with `--write`, then confirm with `--check` (exit 0). Report how many citations moved.

If `--check` was passed, run only the check and report pass/fail. Use this after inserting, removing, or moving any citation in a numbered-style paper, and before `/academic-critique`.
