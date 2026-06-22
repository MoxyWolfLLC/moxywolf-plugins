# document-analysis — Governance

This plugin conforms to the MoxyWolf AI Governance Manifesto; see [../../PLUGIN-CONFORMANCE-AND-MIGRATION-PLAN.md](../../PLUGIN-CONFORMANCE-AND-MIGRATION-PLAN.md) and its five tests.

LOW-RISK. The plugin converts local files to Markdown (per-file isolation, idempotent manifest) and extracts glossary terms. All output is local files; nothing is sent, published, or written to shared/customer systems. Setup installs tooling into the sandbox only.

| Skill/Command | risk_tier | note |
|---|---|---|
| skill: `document-analysis` | generate | Local file → Markdown conversion + term extraction; per-file isolation |
| `markitdown-convert` | generate | Converts a file/folder to Markdown locally (mirrored tree, manifest) |
| `markitdown-setup` | generate | Installs MarkItDown + extras + OCR into the sandbox; verifies readiness |
| `extract-terms` | generate | Extracts glossary terms into a local /glossary-promote package |
