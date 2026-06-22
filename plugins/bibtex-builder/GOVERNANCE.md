# bibtex-builder — Governance

This plugin conforms to the MoxyWolf AI Governance Manifesto; see [../../PLUGIN-CONFORMANCE-AND-MIGRATION-PLAN.md](../../PLUGIN-CONFORMANCE-AND-MIGRATION-PLAN.md) and its five tests.

LOW-RISK. The plugin builds and enriches local `.bib` files and "never invents citation data" (Test 3). It produces local artifacts that do not auto-ship; no sends, no writes to shared/customer systems.

| Skill/Command | risk_tier | note |
|---|---|---|
| skill: `bibtex-builder` | generate | Builds/enriches local .bib files; never invents citation data |
| `bibtex-enrich` | generate | Adds abstracts to an existing BibTeX file (local) |
| `bibtex-from-urls` | generate | Builds a .bib with abstracts from one or more URLs (local) |
