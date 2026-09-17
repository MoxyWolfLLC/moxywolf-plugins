#!/usr/bin/env python3
"""Inject the common MoxyWolf plugin context and knowledge-transport contract."""

print(
    """MOXYWOLF FEDERATED CONTEXT CONTRACT
Before every MoxyWolf plugin action, resolve the current project's project-surfaces.json, read that producing plugin's vault-context.json, and run the packaged project-init federated_context.py resolver with the action's intent. Do this even when /session-start was not invoked. Never collect a plane declared as none. Keep Taskade current work, declared Git executable truth, and Vault company memory visibly separate.

If the plugin produces durable knowledge, append a candidate conforming to project-init/schemas/knowledge-candidate.schema.json to the active project's 00 – Project Hub/knowledge-candidates.json. This Taskade file is machine-readable transport, not company memory and not authorization to write the Vault. obsidian-update verifies, deduplicates, routes, and approval-gates every candidate."""
)
