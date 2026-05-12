---
description: Generate the monthly MoxyWolf board deck from data sources
argument-hint: [month-year, e.g. "February 2026"]
allowed-tools: Read, Write, Edit, Bash, WebFetch, WebSearch, Task, Glob, Grep, AskUserQuestion, TodoWrite
---

Generate the MoxyWolf monthly board deck for @$1.

Follow the board-deck-builder skill workflow. The skill is at
`skills/board-deck-builder/SKILL.md` — read it first for context, then read the
reference files it points to.

## Workflow

### Phase 1: Data Collection

Read `skills/board-deck-builder/references/data-collection.md` for source-specific
instructions.

Collect data from these sources (use browser scraping and Rube tools where possible):

1. **LivePlan** — Cash position, monthly burn, P&L, balance sheet, revenue
2. **GA4** — TOF sessions by product, channel breakdown, engagement rates
3. **Taskade** — Sprint tasks by status, story points, velocity
4. **GitHub** (via Rube) — All-branch commit velocity for **STIGViewer** (`MoxyWolfLLC/stigviewer`)
   and **SAMS** (`MoxyWolfLLC/SAMS`). Use `GITHUB_LIST_BRANCHES` to enumerate every branch
   in each repo, then `GITHUB_LIST_COMMITS` per branch with the reporting month as the date
   range. Deduplicate commits by SHA for true project-wide velocity. Both repos use feature
   branches that don't reach main until go-live.
5. **Gmail** (via Rube) — **RegGenome** activity intelligence. Search Dorian's inbox for
   emails mentioning "reggenome", "regulatory genome", or "reg genome" within the reporting
   month. Extract meeting transcripts, partnership correspondence, action items, and decisions
   to populate `reggenomeActivity` and enrich `reggenomeOKRs`.

For any data that cannot be automatically collected, ask the user to provide it.

### Phase 2: Assemble JSON

Read `skills/board-deck-builder/references/data-schema.md` for the complete schema.
Use `skills/board-deck-builder/references/example-data.json` as a structural reference.

Create the data JSON file at the workspace root named `board-deck-data-{month}-{year}.json`.

Ask the user for any fields that require manual input:
- Executive Summary (headline, learning, obstacle, priority)
- KPIs (MRR, customers, products at revenue, MoM growth)
- Risks and mitigations
- Strategic decisions

### Phase 3: Generate PPTX

```bash
npm install pptxgenjs
node skills/board-deck-builder/scripts/build-deck-template.js <data.json> <output.pptx>
```

Name the output: `MoxyWolf-Board-{Month}-{Year}.pptx`

### Phase 4: QA Verify

Read `skills/board-deck-builder/references/qa-workflow.md` and run the Quick QA:

1. Convert PPTX to images using LibreOffice + pdftoppm
2. Visually inspect all 10 slides against the checklist
3. Spot-check key numbers against the data JSON
4. Fix any issues found and regenerate

Save the final deck to the workspace folder and provide a download link.
