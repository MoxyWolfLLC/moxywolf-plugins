# Noridoc: project-init

Path: @/plugins/project-init

### Overview

- Owns the MoxyWolf project lifecycle and the federated contract connecting active Taskade work, declared Git repositories, and company memory in the Vault.
- Provides deterministic project resolution, provenance-aware context selection, output routing, and the durable-knowledge proposal transport.
- Injects the common contract at session start while preserving support for explicitly designated Vault-only projects.

### How it fits into the larger codebase

- Every marketplace plugin declares its required planes, memory scopes, and output classes in a plugin-local context declaration.
- Project hubs declare the concrete operational surfaces, aliases, repository roles, and memory map in a machine-readable manifest.
- Session start resolves these two declarations together before a plugin consumes project or company context.
- Session end serializes durable findings as candidates in the Taskade project hub rather than writing company memory directly.
- `obsidian-update` consumes the candidate transport and remains the approval-gated path into the Vault.
- Independently installed plugins carry a small compatible preflight skill; the hook here provides the normal marketplace-wide session envelope.

### Core Implementation

- Project resolution accepts exact project IDs, display names, and aliases, then returns separate workspace, repository, related-workspace, and company-memory surfaces.
- Field-specific root enforcement confines Taskade workspaces, GitHub repositories, Vault memory, MOCs, and symlinks to their declared authority planes.
- Context resolution enforces required, optional, and unused planes plus an allowlist of memory scopes.
- Repository roots represent executable authority; repository Markdown is not mislabeled as live code.
- Markdown discovery ignores dependency/build directories and is bounded, while recent decisions retain the newest bounded set.
- Knowledge candidates use a schema-defined Taskade queue with rooted supporting sources, sensitivity, proposed route, and lifecycle status.

### Things to Know

- The Vault is company-wide long-term memory, never the default active project workspace.
- A plane declared `none` must not be collected, and a missing required plane stops the operation.
- Working artifacts remain in Taskade; code changes remain in explicitly writable repositories.
- Candidate records are proposals only and never authorize a Vault write.
- Credential values are never loaded into context; known credential locations may be reported only as excluded.
- Generated graphs require an explicit scope and remain derived context rather than authored canon.

Created and maintained by Nori.
