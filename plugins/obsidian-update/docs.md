# Noridoc: obsidian-update

Path: @/plugins/obsidian-update

### Overview

- Owns approval-gated promotion of durable project learning into MoxyWolf's company-wide Vault memory.
- Consumes both session evidence and schema-valid knowledge candidates produced by federated plugins.
- Preserves the boundary between active Taskade artifacts, Git executable truth, and authored Vault knowledge.

### How it fits into the larger codebase

- `project-init` and independent plugin preflights route durable findings into the active Taskade hub's candidate queue.
- Producing plugins attach project identity, rationale, sensitivity, proposed routing, and rooted supporting sources.
- This plugin validates and deduplicates those proposals before merging them into its normal extraction plan.
- Human confirmation remains mandatory before any candidate becomes company memory.
- Project-specific knowledge routes to the corresponding Vault project; cross-project knowledge routes to shared company-memory areas.
- Council verification and existing decision-routing rules continue to operate inside the same approval boundary.

### Core Implementation

- The candidate queue is validated against a schema bundled with this plugin so it works when installed independently.
- Malformed entries are reported and skipped rather than repaired through inference.
- Supporting sources are plane-labeled and confined to Taskade, GitHub, or the MoxyWolf Vault as appropriate.
- Proposed routes are confined beneath the Vault and reject traversal.
- Deduplication compares candidates with existing Vault notes and other unresolved queue entries.
- Only successfully approved and written candidates advance to `promoted`; deferred and rejected state remains explicit.

### Things to Know

- `knowledge-candidates.json` is operational transport in Taskade, not company memory.
- A candidate can be correct and still be rejected if it is transient, duplicated, overly sensitive, or belongs in Taskade or Git instead.
- Working deliverables and source code do not move into the Vault merely because a plugin produced them.
- Direct specialized derived-artifact writers retain their existing confirmation and governance gates.
- Schema copies in project-init and obsidian-update must remain identical.

Created and maintained by Nori.
