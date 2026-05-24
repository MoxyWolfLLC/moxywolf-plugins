# Academic Pipeline: How-To Guide

A complete manual for using the `academic-pipeline` plugin: how to take research all the way to a critiqued, publication-ready academic article, no matter where you are starting from.

This guide is organized around the three places people actually start:

- **[Scenario A](#scenario-a-you-have-an-idea-or-a-thesis):** you have an idea or a thesis, but no sources yet.
- **[Scenario B](#scenario-b-you-have-a-bibtex-file):** you have a BibTeX file of research and want a paper out of it. *(This is the pipeline's home turf.)*
- **[Scenario C](#scenario-c-you-have-a-paper-or-papers-already-written):** you already have a written paper (or several) and want it critiqued, formatted, strengthened, or used as the seed for something new.

If you read nothing else, read [Before you begin](#before-you-begin) and the [Quick reference card](#quick-reference-card) at the end.

---

## What this plugin does

The `academic-pipeline` turns a bibliography into a finished, peer-review-ready paper through eight stages (plus an optional Stage 0):

```
BibTeX input
    |
[0] enrich-bibtex            (optional)   add missing abstracts
[1] theme analysis                        theme tree + working title
[2] perspective              * checkpoint lens, audience, sub-themes
[3] voice                    * checkpoint the author's voice for this piece
[4] formatting                            Academia.edu structure + anti-AI rules
[5] research analysis        * checkpoint source analysis + structure plan
[6] iterative writing                     section-by-section drafting
[7] bibliography                          formatted references -> complete document
[8] professor critique                    10-phase review + improvement plan
```

`* checkpoint` marks a human-in-the-loop stage. There are three of them, twelve questions total, all asked inline.

**The core idea is "voice-first."** Most AI writing drafts first and tries to bolt a voice and a journal format on afterward. This pipeline fixes the perspective (Stage 2), the voice (Stage 3), and the formatting (Stage 4) *before* a word is drafted, so Stage 6 writes in the right voice and the right format from the first sentence. No retrofitting.

---

## Before you begin

### The one hard rule

**The pipeline writes *from cited sources*.** Every claim in the finished paper traces to an entry in your bibliography. Stage 1 needs at least **three entries with usable abstracts** to map themes. This is by design. It is what keeps the output grounded and citable instead of confidently hollow.

That rule is why "starting from an idea" (Scenario A) has an extra step at the front: an idea is not yet a bibliography.

### Prerequisites

| Thing | Why | If missing |
|---|---|---|
| A BibTeX (`.bib`) file | The pipeline's input | See Scenario A for how to build one |
| Abstracts in the `.bib` | Stage 1 maps themes from abstract text | Run Stage 0 (`/enrich-bibtex`) |
| The standing voice profile | Stage 3 reads it for the author's durable voice | See [Voice profile setup](#voice-profile-setup) |
| Web fetch | Stage 0 pulls source content for abstracts | Stage 0 simply skips entries it cannot reach |

### Where the output goes

Everything from one run lands in a single **run folder**. Inside a MoxyWolf project session that is `<project>/11 – Project Knowledge/Papers/<paper-slug>/`. Outside a project, the pipeline asks you where to save. See [The run folder](#the-run-folder) for the layout.

### The four commands

| Command | Runs |
|---|---|
| `/academic-pipeline [.bib]` | The whole pipeline, Stages 1 to 8 |
| `/academic-themes [.bib]` | Stage 1 only: theme map and title |
| `/academic-critique [paper]` | Stage 8 only: the professor critique |
| `/enrich-bibtex [.bib]` | Stage 0 only: add abstracts to a `.bib` |

You can also just describe what you want in plain language. The skills trigger on intent, so "run the academic pipeline on this bibliography" works as well as the slash command.

---

## Which starting point are you?

| You have... | You want... | Go to |
|---|---|---|
| An idea, a thesis, a topic | A finished paper | [Scenario A](#scenario-a-you-have-an-idea-or-a-thesis) |
| A `.bib` file of research | A finished paper | [Scenario B](#scenario-b-you-have-a-bibtex-file) |
| One finished paper | An honest pre-submission review | [Scenario C1](#c1-critique-one-finished-paper) |
| One finished paper | It formatted for journal submission | [Scenario C2](#c2-format-a-paper-for-academiaedu) |
| A paper that needs strengthening | New material merged into it | [Scenario C3](#c3-strengthen-or-update-an-existing-paper) |
| One or more existing papers | A *new* paper that builds on them | [Scenario C4](#c4-turn-existing-papers-into-a-new-paper) |

---

## Scenario A: You have an idea or a thesis

**Example starting point:** *"I think multi-agent AI systems should borrow consensus mechanisms from distributed-systems research, and almost nobody is making that connection."*

That is a thesis. It is not yet a paper, and it is not yet something the pipeline can run, because the pipeline writes from sources and you do not have any. So Scenario A is really **one preparation step, then Scenario B**.

Here is the important reassurance: **your idea is not lost in the handoff.** It becomes the steering input for three stages:

- The Stage 1 working title: you can override the suggested title with your own.
- The Stage 2 **perspective**: your thesis *is* the writing lens and the sub-themes.
- The Stage 3 **voice**: your thesis, stated plainly, is the answer to "what does most of the field get wrong" and "what triggered this piece."

### Step 1: Turn the idea into a bibliography

You need a `.bib` file with real sources. Three ways to get one, in rough order of preference:

1. **Discover sources with the `research-pipeline` plugin.** Its `/discover-literature` command takes a topic and finds academic sources for you. It is the discovery-first sibling of this plugin. Use it to build a research library on your idea, then assemble those sources into a `.bib` file.
2. **Build a `.bib` from URLs with the `bibtex-builder` plugin.** If you already have a reading list (papers, reports, standards documents, vendor whitepapers), collect the URLs or DOIs and run `bibtex-builder`'s `/bibtex-from-urls`. It produces a properly formatted `.bib` with abstracts already included.
3. **Assemble it by hand.** Export entries from Zotero, Google Scholar, or a reference manager into a single `.bib` file.

Whichever route you take, the end state is the same: **one `.bib` file on disk, with at least three entries that have abstracts.**

> A good working bibliography for a pipeline run is usually 12 to 30 entries. Fewer than about 10 and the paper will feel thin. Many more than 30 and Stage 5 will be choosy about what it cites anyway.

### Step 2: Enrich abstracts if needed

If your `.bib` came from a reference manager, some entries may have no `abstract` field. Run:

```
/enrich-bibtex path/to/your.bib
```

This fetches each entry's `url` or `doi` and writes a faithful 2 to 4 sentence abstract. Entries that already have an abstract are left untouched. Nothing is fabricated. An unreachable source is simply left blank.

### Step 3: Run the pipeline

You are now in Scenario B. Run:

```
/academic-pipeline path/to/your.bib
```

When you reach the **perspective** and **voice** checkpoints, this is where your original idea does its work. Plan to say, in your own words:

- *Perspective:* the lens your thesis implies, often **Comparative** or **Innovation-focused** for a "nobody connects X and Y" thesis.
- *Voice, "contrarian take":* your thesis, stated bluntly. This is the single most important answer in the whole run.
- *Voice, "trigger":* what made you care. The conversation, the paper, the frustration.

### Worked example

> **Idea:** AI agents need consensus mechanisms from distributed systems.
> 1. `research-pipeline` `/discover-literature` on "multi-agent LLM consensus and distributed systems" finds 20-some sources. Assemble them into `agent-consensus.bib`.
> 2. `/enrich-bibtex agent-consensus.bib` fills in six missing abstracts.
> 3. `/academic-pipeline agent-consensus.bib`. At Stage 2 you choose a **Comparative** lens for "AI engineers building multi-agent systems." At Stage 3, your contrarian take is the thesis verbatim. Eight stages later you have a critiqued draft that argues exactly the paper you set out to write.

---

## Scenario B: You have a BibTeX file

This is the pipeline's home turf. One command runs all eight stages.

### Step 0: Check your abstracts

Open the `.bib` and confirm most entries have an `abstract` field. If many do not:

```
/enrich-bibtex path/to/research.bib
```

Skip this if abstracts are already present. Stage 1 will tell you to come back here if it finds fewer than three usable abstracts.

### Step 1: Start the run

```
/academic-pipeline path/to/research.bib
```

The orchestrator first asks **how you want the three checkpoints handled**:

- **Stage-by-stage (default).** The pipeline pauses at Stages 2, 3, and 5 and asks the questions in context. Best when you want to stay in the loop and react to what each stage surfaces.
- **Front-loaded.** It collects all twelve answers up front, then runs straight through without stopping. Best when you know exactly what you want and would rather not babysit it.

It then creates a task list so you can watch progress, and begins.

### Step 2: Walk the eight stages

| Stage | What happens | Your involvement |
|---|---|---|
| **1. Theme analysis** | Reads the `.bib`, builds a Mermaid theme tree, proposes 2 to 3 titles | Confirm or replace the working title |
| **2. Perspective** *(checkpoint)* | Captures the writing strategy | Answer 3 questions |
| **3. Voice** *(checkpoint)* | Captures the author's voice for this piece | Answer 8 questions |
| **4. Formatting** | Distills Academia.edu structure + anti-AI rules | None (automatic) |
| **5. Research analysis** *(checkpoint)* | Analyzes sources, designs the section structure | Approve / modify / reject the structure |
| **6. Writing** | Drafts the paper section by section | None (automatic) |
| **7. Bibliography** | Formats every cited source, assembles the final document | None (automatic) |
| **8. Professor critique** | Runs the 10-phase review | None (automatic) |

### The three checkpoints, in detail

**Stage 2, Perspective (3 questions).** Have answers ready for:

1. **Writing perspective / lens.** Critical, Historical, Practical, Theoretical, Integration, Innovation-focused, or Comparative. The pipeline suggests the 2 to 3 that fit your bibliography, but the choice is yours.
2. **Target audience.** Be specific: their background (academic, industry, policy, general), their expertise level, and what they need from the piece.
3. **Sub-themes.** Pick 3 to 5 branches of the theme tree to emphasize.

**Stage 3, Voice (8 questions).** This is the interview that makes the paper sound human. Worth preparing for:

1. **Trigger.** What conversation, situation, paper, or frustration set this in motion?
2. **Evidence.** One real, specific example. A case, a number, a moment.
3. **Contrarian take.** What does most of the field get wrong here?
4. **Authority.** Why should anyone listen to you on this?
5. **Specific reader.** Who exactly is this for, and what keeps that person up at night?
6. **Business connection.** How does this connect to MoxyWolf?
7. **Call to action.** What should the reader actually *do* afterward?
8. **Emotional core.** What about this genuinely angers, excites, or worries you?

Answer in your own words. The pipeline captures your actual phrasing rather than smoothing it into generic statements.

**Stage 5, Structure approval (1 decision).** The pipeline shows you the proposed section list, word targets, and which sources map to which section. You **approve**, **modify** (describe the changes, it revises and re-shows), or **reject** (it redesigns). Nothing gets drafted until you approve.

### Step 3: Collect your output

When Stage 8 finishes you have a run folder with everything in it. The headline files:

- **`complete_document.md`:** the finished, fully cited paper. This is the main deliverable.
- **`critique_report.md`:** the professor's 10-phase review, with a letter grade and predicted reviewer comments.
- **`improvement_plan.md`:** a specific, prioritized path from the current draft to publication-ready.

Read the critique. If the grade is not where you want it, see [After the critique](#after-the-critique).

### Worked example

> You have `compliance-ai.bib`, 22 entries, abstracts already present.
> 1. `/academic-pipeline compliance-ai.bib`, choose stage-by-stage.
> 2. Stage 1 suggests "Automated Compliance Validation in the Age of LLMs (2022-2025)", which you accept.
> 3. Stage 2: Innovation-focused lens, audience "compliance engineers and GRC leads", sub-themes picked from the tree.
> 4. Stage 3: eight voice answers, ten minutes of honest typing.
> 5. Stage 5: the six-section structure looks right, so you approve.
> 6. Stages 6 to 8 run unattended. You come back to a ~4,000-word cited draft graded B+ with a concrete plan to reach A.

---

## Scenario C: You have a paper (or papers) already written

When a paper already exists, you do not run the whole pipeline. You use the **back half** of it, plus the utility skills. Pick the branch that matches your goal.

### C1: Critique one finished paper

You want an honest, brutal-but-constructive pre-submission review.

```
/academic-critique path/to/paper.md
```

The input can be a Markdown draft or a `.docx`. The `professor` skill runs all ten phases in order, AI-detection first, then document integrity, citation format, reference completeness, logic and argumentation, methodological rigor, literature review, evidence and results, writing quality, and contribution assessment.

You get back:

- **`critique_report.md`:** phase-by-phase findings, an overall verdict (Accept / Minor revision / Major revision / Reject), a letter grade, and predicted reviewer scores.
- **`improvement_plan.md`:** a specific, prioritized path forward, not generic advice.

This needs nothing else from the pipeline. Use it any time a paper needs a reality check before it goes to a journal or a co-author.

### C2: Format a paper for Academia.edu

You have finished content and need it packaged to journal standard: the right sections in the right order, an abstract under 250 words, Vancouver citations, all the end-matter statements, and zero AI tells.

Use the **`academia-formatting`** skill. Describe it plainly ("format this paper for Academia.edu submission") or let it trigger on the request. It runs a document assessment (what sections exist, what is missing), a short voice interview, section-by-section formatting, an anti-AI checklist, and delivers a `.docx` built on the Academia.edu submission template that ships with the plugin.

### C3: Strengthen or update an existing paper

You have a paper that is fine as far as it goes but is missing something (a framework, a methodology section, current examples), and you have a reference source to pull from.

Use the **`scholarly-content-updater`** skill. Give it the target file and a reference source (a URL, a document, or a template). It compares the two, drafts the missing material in MoxyWolf voice, formats the new citations, and hands you ready-to-paste Markdown with exact placement instructions.

### C4: Turn existing papers into a *new* paper

You have one or more finished papers and want to write a new piece that synthesizes or builds on them. The move here is to **harvest their bibliographies** and then run the full pipeline.

1. From each existing paper, take the reference list and convert it into BibTeX. If the papers cite URLs and DOIs, `bibtex-builder`'s `/bibtex-from-urls` is the fast route. Merge everything into one `.bib`.
2. Optionally add the existing papers themselves as entries, so the new paper can cite your own prior work.
3. Run `/enrich-bibtex` to fill any gaps.
4. You are now in [Scenario B](#scenario-b-you-have-a-bibtex-file). Run `/academic-pipeline` on the merged `.bib`.

This is how you go from "three papers I wrote last year" to "one synthesis paper that ties them together."

### After the critique

Whatever route you took, when `professor` hands back an `improvement_plan.md` you have two ways to act on it:

- **Apply the fixes**, by hand or with `scholarly-content-updater` for the source-backed additions.
- **Re-run the critique.** Run `/academic-critique` on the revised draft to confirm the grade actually moved. Treat it as a loop: critique, fix, re-critique, until the grade is where you need it.

---

## The run folder

Every run writes to one folder so nothing scatters across your workspace:

```
<run folder>/
├── mermaid_diagram.md          theme tree (Stage 1)
├── complete_document.md        >>> the finished paper (Stage 7)
├── critique_report.md          the professor review (Stage 8)
├── improvement_plan.md         the path forward (Stage 8)
└── pipeline/                   intermediate artifacts
    ├── enriched.bib            (only if Stage 0 ran)
    ├── theme_analysis.json
    ├── perspective.json
    ├── voice_context.json
    ├── formatting_requirements.json
    ├── handoff_for_writer.json
    └── draft_document.md
```

The four files in the root are the deliverables. The `pipeline/` subfolder holds the working artifacts, useful if you want to re-run a single stage, audit a decision, or understand why the paper came out the way it did.

In a MoxyWolf project session the run folder is created under `<project>/11 – Project Knowledge/Papers/<paper-slug>/`, consistent with the project routing rules. Outside a project, the pipeline asks where to save.

### Rendering the final paper

`complete_document.md` is Markdown. To produce a submission-ready `.docx` or PDF, hand it to the `academia-formatting` skill together with the `docx` or `pdf` skills. That is the same path as [Scenario C2](#c2-format-a-paper-for-academiaedu).

---

## Commands and skills reference

### Commands

| Command | Stage | Use it to |
|---|---|---|
| `/academic-pipeline` | 1-8 | Run the whole pipeline from a `.bib` |
| `/academic-themes` | 1 | Just map a bibliography into a theme tree |
| `/academic-critique` | 8 | Just critique an existing paper |
| `/enrich-bibtex` | 0 | Just add abstracts to a `.bib` |

### Skills

| Skill | Stage | Role |
|---|---|---|
| `academic-pipeline-orchestrator` | n/a | Sequences all stages, owns the run folder and checkpoints |
| `bibtex-abstract-generator` | 0 | Generates abstracts for `.bib` entries that lack them |
| `bibtex-theme-analyzer` | 1 | Maps the bibliography into a theme tree, proposes the title |
| `academic-perspective-builder` | 2 | Captures lens, audience, sub-themes |
| `academic-voice` | 3 | Reads the standing voice profile, captures the article's voice |
| `academia-formatting` | 4 | Academia.edu structure and MoxyWolf anti-AI rules |
| `research-analyst` | 5 | Analyzes sources, designs and gets approval for the structure |
| `research-writer` | 6 | Drafts the paper section by section |
| `bibliography-generator` | 7 | Formats references, assembles the final document |
| `professor` | 8 | 10-phase peer-review critique with a path forward |
| `scholarly-content-updater` | n/a | Companion: updates any file against a reference source |

### Running stages standalone

You do not have to run the whole pipeline. Every stage works on its own when you already have its input:

- Already have a structure handoff? Invoke `research-writer` directly.
- Just want the theme map? `/academic-themes`.
- Just want a critique? `/academic-critique`.

The `pipeline/` artifacts are the contracts between stages. If you have the right input file, you can enter the pipeline at any point.

---

## Voice profile setup

Stage 3 (`academic-voice`) works in two layers:

- **Standing voice.** How the author writes in general. The pipeline reads this from a profile file. It does not re-interview you for it every run.
- **Article voice.** Why *this* piece exists. Captured fresh each run via the eight questions.

For MoxyWolf work, the standing voice profile lives at:

```
MoxyWolf Vault/_Shared Knowledge/Brand and Voice/dorian-cougias.md
```

It encodes the durable rules: no em dashes, contraction habits, paragraph architecture, the two-reader frame. Stage 3 records the *path* to this file so the writer reads the live version.

**Running outside the MoxyWolf vault, or for a different author?** The skill will not guess a voice. It asks where the author's voice profile lives, or, if there is none, runs a short three-question standing-voice mini-interview and stores the answers with the run. Either way the pipeline still works. It just sources the standing voice differently.

---

## Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| Stage 1 stops: "fewer than three usable abstracts" | The `.bib` has too few abstracts | Run `/enrich-bibtex` first (Stage 0) |
| Stage 0 leaves some abstracts blank | Those sources could not be fetched | Add a working `url` or `doi` to those entries, or accept the gap |
| "Standing voice profile not found" | Running outside the MoxyWolf vault | Point the skill at a profile, or let it run the mini-interview |
| The draft cites a source you did not expect | Stage 5 mapped it to a section | Modify the structure at the Stage 5 checkpoint before approving |
| Citations are in the wrong style | Default is Vancouver (Academia.edu) | Tell `research-analyst` your style at Stage 5; APA, Chicago, and MLA are supported |
| The paper has em dashes or AI-tell phrases | Should not happen; Stage 4 forbids them | Flag it; run `/academic-critique`, whose Phase 1 catches exactly this |
| Professor grade is low | Honest review of a real weakness | Work the `improvement_plan.md`, then re-run `/academic-critique` |
| You want no interruptions | Stage-by-stage is the default | Choose **front-loaded** at the start of `/academic-pipeline` |
| Artifacts scattered around | A stage ran without a run folder | Re-run via `/academic-pipeline` so the orchestrator sets the run folder |

---

## Quick reference card

```
START FROM AN IDEA          ->  build a .bib first (research-pipeline / bibtex-builder),
                                then /academic-pipeline your.bib

START FROM A .bib FILE      ->  /enrich-bibtex your.bib   (if abstracts are thin)
                                /academic-pipeline your.bib

START FROM A WRITTEN PAPER  ->  critique it     ->  /academic-critique paper.md
                                format it       ->  academia-formatting skill
                                strengthen it   ->  scholarly-content-updater skill
                                build a new one ->  harvest its refs into a .bib,
                                                    then /academic-pipeline

THREE CHECKPOINTS  ->  Stage 2 perspective (3 Q) | Stage 3 voice (8 Q) | Stage 5 structure (approve)
MAIN DELIVERABLE   ->  <run folder>/complete_document.md
THE REVIEW         ->  <run folder>/critique_report.md  +  improvement_plan.md
```

---

*Part of the `academic-pipeline` plugin. See `README.md` for installation and the plugin's place in the MoxyWolf marketplace. (c) MoxyWolf LLC.*
