---
description: Draft questions for thin personas, REST-only capabilities, and questions that need customer input. Drafts stay out of exports until a named person accepts them.
argument-hint: '[--persona <id>] [--blocked] [--rest-only]'
allowed-tools: [Bash, Read, Write]
---

# /mcp-demand-harness:demand-expand (generate)

Read `skills/mcp-demand-harness/references/expansion-rules.md` first. In short:

1. Run `bank.py report` and find the gaps: personas with few or no questions, questions blocked on `requires_input`, and REST-only routes no question touches.
2. Draft into a JSON list file, not into the bank.
   - Blocked questions become `generated` children with `evidence.parent`. Use real identifiers from the repo (sample checklists, fixtures). Say in `evidence.note` which values are synthetic.
   - Persona gaps become `hypothesis` questions, with `evidence.source` and `source_line` pointing at the persona doc.
   - Every draft has `review_status: "draft"` and `evidence.authored_by: "claude (draft)"`.
   - Never present model-written text as a customer's words.
3. Add the drafts: `python3 $S/bank.py add --bank $B --capability-map $M --file drafts.json`. The add is all or nothing. Fix whatever the validator rejects, then add again.
4. List the drafts for review, grouped by persona. Each entry shows the text, why it matters, and what it checks.
5. Only the named reviewer accepts, and only the ids they read:

   ```bash
   python3 $S/bank.py accept --bank $B --capability-map $M --approver "First Last" --ids Q-0072 Q-0075
   ```
