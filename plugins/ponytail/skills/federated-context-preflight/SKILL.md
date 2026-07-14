---
name: federated-context-preflight
description: Must be used before any ponytail skill or command so independently installed plugins still obey the MoxyWolf project, repository, and company-memory contract.
---

# Federated Context Preflight

Before any other skill or command from this plugin:

1. Locate the active project's `00 – Project Hub/project-surfaces.json`. Active project work normally lives under `Taskade/<Project>/`; only an explicitly declared `vault-only` project may work from the Vault.
2. Read this plugin's `${CLAUDE_PLUGIN_ROOT}/vault-context.json`. Load only planes and memory scopes it declares. Never read a plane declared `none`; stop if a required plane is unavailable. Keep Taskade current work, Git executable truth, and Vault company memory separate.
3. Reject paths that traverse or escape their plane roots. Never read credential values. Repository declarations marked read-only remain read-only.
4. If project-init's packaged resolver is available, use it. Otherwise apply the manifest and declaration directly and fail closed rather than guessing a workspace, repository, alias, or Vault folder.
5. When this plugin produces a durable decision, rationale, finding, reusable insight, or cross-project pattern, merge a proposal into the active Taskade hub's `knowledge-candidates.json`. Include `producing_plugin`, `project_id`, `claim`, `rationale`, a confined `proposed_route` under `MoxyWolf Vault/`, `sensitivity`, `related_projects`, `supporting_sources` with plane + rooted path, and `status: proposed`. This queue is transport only; it never authorizes a Vault write. `obsidian-update` verifies, deduplicates, routes, and waits for human approval.
