# academic-pipeline — Governance

This plugin conforms to the MoxyWolf AI Governance Manifesto; see [../../PLUGIN-CONFORMANCE-AND-MIGRATION-PLAN.md](../../PLUGIN-CONFORMANCE-AND-MIGRATION-PLAN.md) and its five tests.

**Reference implementation.** academic-pipeline is an EXEMPLAR for **Test 3 (Provenance)**: its "never invent citation data" rule — missing fields flagged `n.d.` rather than fabricated — is the model for honest scholarly output. The plugin generates articles and bibliographies locally and never publishes or sends; its critique skills read and report.

| Skill/Command | risk_tier | note |
|---|---|---|
| skill: `academic-pipeline-orchestrator` | generate | Orchestrates the pipeline; produces local artifacts |
| skill: `bibtex-abstract-generator` | generate | Generates AI abstracts for entries lacking them |
| skill: `bibtex-theme-analyzer` | generate | Maps bibliography into theme tree + title |
| skill: `academic-perspective-builder` | generate | Builds perspective (HITL inputs); local |
| skill: `academic-voice` | generate | Voice profile for academic writing |
| skill: `academia-formatting` | generate | Applies formatting requirements |
| skill: `research-analyst` | read-only | Analyzes sources + structure; reports |
| skill: `research-writer` | generate | Drafts the article; does not publish |
| skill: `bibliography-generator` | generate | Produces bibliography; never invents citation data |
| skill: `professor` | read-only | 10-phase critique; evaluates + reports, no writes |
| skill: `scholarly-content-updater` | generate | Updates draft content locally |
| `academic-pipeline` | generate | Full pipeline; .bib to critiqued article (local) |
| `academic-themes` | generate | Theme tree + suggested title (Stage 1) |
| `enrich-bibtex` | generate | AI abstracts for entries (Stage 0) |
| `academic-critique` | read-only | Professor critique (Stage 8); evaluates + reports |
