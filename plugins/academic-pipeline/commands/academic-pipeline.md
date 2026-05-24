---
description: Run the full academic content pipeline — BibTeX file to a critiqued, publication-ready article
argument-hint: [path to .bib file]
---

Run the complete academic content pipeline using the **`academic-pipeline-orchestrator`** skill.

Before starting:

1. Identify the BibTeX input. Use the path in `$ARGUMENTS` if given; otherwise ask the user for the `.bib` file (a path, an uploaded file, or pasted text).
2. Establish the run folder per the orchestrator's *Establish the run folder* step — in a MoxyWolf project session this is `<active project>/11 – Project Knowledge/Papers/<target-slug>/`.
3. Ask the user once whether they want **stage-by-stage** checkpoints (default) or a **front-loaded** run where all twelve HITL answers are collected up front.
4. Create a task list with one task per stage so progress is visible.

Then run all eight stages in order (plus optional Stage 0 if the `.bib` is missing abstracts): theme analysis → perspective → voice → formatting → research analysis → iterative writing → bibliography → professor critique.

The three human checkpoints (Stage 2 perspective, Stage 3 voice, Stage 5 structure approval) use the AskUserQuestion tool inline — never a blocking handoff file.

On completion, present `complete_document.md` as the main deliverable with a `computer://` link, surface the professor's verdict and grade, and offer to render the document as a formatted `.docx`/PDF.
