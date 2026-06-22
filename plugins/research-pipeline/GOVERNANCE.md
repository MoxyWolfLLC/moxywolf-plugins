# research-pipeline — Governance

This plugin conforms to the MoxyWolf AI Governance Manifesto; see [../../PLUGIN-CONFORMANCE-AND-MIGRATION-PLAN.md](../../PLUGIN-CONFORMANCE-AND-MIGRATION-PLAN.md) and its five tests.

**Reference implementation.** research-pipeline is the EXEMPLAR for **Test 3 (Provenance)**: its `citation-verifier` is the canonical 4-layer provenance standard (CrossRef / DataCite / arXiv / Semantic Scholar, then semantic + LLM relevance scoring) that catches hallucinated or broken references before they reach published content. Other content-producing plugins are expected to route claim-bearing output through this verifier. The plugin is mostly generate/read-only; its only side effect is writing citations/libraries to Supabase, which is gated.

| Skill/Command | risk_tier | note |
|---|---|---|
| skill: `research-pipeline` | side-effectful-gated | Orchestrator; manages the Supabase schema (writes libraries/citations behind confirm) |
| skill: `literature-discovery` | generate | Searches sources, builds bibliography locally; Supabase insert is the gated step |
| skill: `import-bibtex` | side-effectful-gated | Parses + enriches, then inserts structured citations into Supabase |
| skill: `citation-verifier` | read-only | Validates references against external APIs; reports, does not ship |
| skill: `research-synthesizer` | generate | Builds thematic maps + perspectives; local artifacts |
| skill: `content-writer` | generate | Produces draft articles; does not publish |
| `discover-literature` | generate | Source discovery; bibliography produced locally |
| `import-bibtex` | side-effectful-gated | Imports .bib into the pipeline; Supabase write |
| `research-status` | read-only | Reports current library state |
| `synthesize-research` | generate | Thematic maps + writing perspectives |
| `verify-citations` | read-only | Runs 4-layer verification; reports |
| `write-article` | generate | Drafts research-backed article; does not auto-ship |

Note: Supabase writes (library/citation inserts in `import-bibtex` and the orchestrator) are the plugin's only real side effect and are treated as **side-effectful-gated** — they persist to a shared store, so they sit behind a confirm checkpoint (Tests 1, 5).
