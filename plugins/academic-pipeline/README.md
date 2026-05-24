# academic-pipeline

End-to-end academic content pipeline for Cowork: take a BibTeX bibliography all the way to a critiqued, publication-ready article — with the author's authentic voice and Academia.edu formatting baked in from the first draft.

## Why it exists

Most AI writing pipelines draft first, then try to bolt on a voice and a journal format afterward, then rewrite. This one is **voice-first**: it fixes the writing perspective, the author's voice, and the formatting rules *before* a single section is drafted. Stage 6 then writes in that voice and that format from the first sentence. No retrofitting, no second-pass rewrites.

## The pipeline

```
BibTeX input
    |
[0] bibtex-abstract-generator   (optional)   ->  enriched .bib
[1] bibtex-theme-analyzer                    ->  theme tree + TARGET_TITLE
[2] academic-perspective-builder   * HITL    ->  perspective.json        (3 questions)
[3] academic-voice                 * HITL    ->  voice_context.json      (8 questions)
[4] academia-formatting                      ->  formatting_requirements.json
[5] research-analyst               * HITL    ->  handoff_for_writer.json (structure approval)
[6] research-writer                          ->  draft (section by section)
[7] bibliography-generator                   ->  complete_document.md
[8] professor                                ->  critique_report.md + improvement_plan.md
```

`* HITL` marks a human checkpoint — three of them, twelve questions total, all asked inline with the AskUserQuestion tool.

## Skills

| Skill | Stage | Role |
|-------|-------|------|
| `academic-pipeline-orchestrator` | — | Sequences all stages, owns the run folder and checkpoints |
| `bibtex-abstract-generator` | 0 | Generates AI abstracts for `.bib` entries that lack them |
| `bibtex-theme-analyzer` | 1 | Maps the bibliography into a Mermaid theme tree; proposes the title |
| `academic-perspective-builder` | 2 | Captures lens, audience, and sub-themes |
| `academic-voice` | 3 | Reads the standing voice profile, captures the article's voice |
| `academia-formatting` | 4 | Academia.edu structure + MoxyWolf anti-AI writing rules |
| `research-analyst` | 5 | Analyzes sources, designs the structure, gets it approved |
| `research-writer` | 6 | Drafts the paper section by section, voice and format applied |
| `bibliography-generator` | 7 | Formats references and assembles the final document |
| `professor` | 8 | 10-phase peer-review critique with a path forward |
| `scholarly-content-updater` | — | Companion: updates any file against a reference source |

## Commands

| Command | Does |
|---------|------|
| `/academic-pipeline [.bib]` | Runs the full eight-stage pipeline |
| `/academic-themes [.bib]` | Stage 1 only — theme map + suggested title |
| `/academic-critique [paper]` | Stage 8 only — professor critique of an existing paper |
| `/enrich-bibtex [.bib]` | Stage 0 only — add AI abstracts to a bibliography |

## Run folder

Every artifact from one run lives in a single run folder. In a MoxyWolf project session that is `<active project>/11 – Project Knowledge/Papers/<target-slug>/`; otherwise the user picks, or it falls back to the Cowork outputs folder.

```
<run folder>/
├── mermaid_diagram.md          deliverable
├── complete_document.md        MAIN deliverable
├── critique_report.md          deliverable
├── improvement_plan.md         deliverable
└── pipeline/                   intermediate JSON + draft
```

## Requirements

- **Standing voice profile** — Stage 3 reads `MoxyWolf Vault/_Shared Knowledge/Brand and Voice/dorian-cougias.md`. Outside the MoxyWolf vault (or for another author), the skill asks for a profile or runs a short standing-voice mini-interview instead.
- **Web fetch** — Stage 0 uses `mcp__workspace__web_fetch` to pull source content for abstracts.
- No external database. The pipeline reads BibTeX files directly and writes Markdown/JSON to the run folder.

## Relationship to other MoxyWolf plugins

- **`research-pipeline`** — a different, complementary flow: literature *discovery* (find sources on a topic), citation verification, and Supabase-backed synthesis. `academic-pipeline` starts from a `.bib` you already have and ends at a critiqued paper. Use `research-pipeline` to build the bibliography, `academic-pipeline` to write from it.
- **`bibtex-builder`** — also enriches `.bib` files with abstracts. `academic-pipeline` bundles its own Stage 0 (`bibtex-abstract-generator`) so the pipeline is self-contained; `bibtex-builder` remains the standalone choice for bibliography work outside this pipeline.
- **`editorial-forge`** — voice and authorship for long-form book/strategy work. `academic-pipeline` is scoped to journal-style articles built from a bibliography.

## Credit

Adapted and modernized for Cowork from a set of MoxyWolf academic skills originally written for a GSD-mode runtime. The HITL machinery now uses the AskUserQuestion tool, outputs route to a single run folder, and BibTeX files are read directly.

© MoxyWolf LLC.
