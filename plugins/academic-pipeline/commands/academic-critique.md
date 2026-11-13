---
description: Run the 10-phase professor critique on an academic paper (Stage 8 only)
argument-hint: [path to the paper — .md or .docx]
---

Run **Stage 8** of the academic pipeline standalone, using the **`professor`** skill.

1. Identify the paper to critique — the path in `$ARGUMENTS`, an uploaded file, or pasted text. It can be a `.md` draft or a `.docx`.
2. Before the review, run the prose lint on the paper (a `.md` draft; for a `.docx`, convert to Markdown first): `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/prose_lint.py <paper.md> --report --longform --signature-devices <devices from the author's voice profile> --out prose_lint.md`. It writes `prose_lint.md` on every grade and exits 1 on a D or F: then stop, say the grade and point at the findings, and don't critique until the draft is revised. On exit 0, give `prose_lint.md` to the professor with the paper.
3. Run the full 10-phase review **in order**, AI-detection first: AI detection → document integrity → citation format → reference completeness → logic & argumentation → methodological rigor → literature review → evidence & results → writing quality → contribution assessment.
4. Produce `critique_report.md` (phase-by-phase findings, verdict, letter grade, reviewer predictions) and `improvement_plan.md` (a specific, prioritized path forward).

Save both files next to the source paper, or to the run folder if this paper came from a pipeline run. Surface the headline verdict and grade in chat.

Use this any time a paper needs a brutally honest, constructive pre-submission review — it does not require the rest of the pipeline to have run.
