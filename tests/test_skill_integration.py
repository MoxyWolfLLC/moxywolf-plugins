from __future__ import annotations

import unittest
from pathlib import Path
import json


ROOT = Path(__file__).resolve().parents[1]


def read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


class ProjectLifecycleContractTests(unittest.TestCase):
    def test_project_init_creates_machine_readable_surface_manifest(self):
        skill = read("plugins/project-init/skills/project-init/SKILL.md")

        self.assertIn("project-surfaces.json", skill)
        self.assertIn("Taskade/<Project>/00 – Project Hub", skill)
        self.assertIn("vault-only", skill)
        self.assertIn("repositories", skill)

    def test_session_start_loads_three_planes_without_collapsing_them(self):
        skill = read("plugins/project-init/skills/session-start/SKILL.md")

        self.assertIn("project_surfaces.py", skill)
        self.assertIn("federated_context.py", skill)
        self.assertIn("Project workspace (Taskade)", skill)
        self.assertIn("Code workspace (Git)", skill)
        self.assertIn("Company memory (Vault)", skill)
        self.assertIn("authority domain", skill.lower())

    def test_session_start_requires_each_later_plugin_to_resolve_its_own_declaration(self):
        skill = read("plugins/project-init/skills/session-start/SKILL.md")

        self.assertIn("Before each later plugin action", skill)
        self.assertIn("that plugin's `vault-context.json`", skill)
        self.assertIn("rerun `federated_context.py`", skill)

    def test_session_start_uses_manifest_memory_path_instead_of_name_guessing(self):
        skill = read("plugins/project-init/skills/session-start/SKILL.md")

        self.assertIn("resolved manifest's memory path is authoritative", skill)
        self.assertNotIn("Otherwise match `MoxyWolf Vault/Projects/<name>/` by best name match", skill)

    def test_refresh_project_instructions_creates_or_validates_surface_manifest(self):
        command = read("plugins/project-init/commands/refresh-project-instructions.md")

        self.assertIn("project-surfaces.json", command)
        self.assertIn("create or validate", command.lower())
        self.assertIn("confirm", command.lower())

    def test_session_end_collects_candidates_without_writing_company_memory(self):
        skill = read("plugins/project-init/skills/session-end/SKILL.md")

        self.assertIn("Knowledge candidates", skill)
        self.assertIn("propose-via-obsidian-update", skill)
        self.assertIn("does not authorize a Vault write", skill)


class CompanyMemoryPromotionContractTests(unittest.TestCase):
    def test_obsidian_update_ingests_structured_candidates_and_still_requires_approval(self):
        skill = read("plugins/obsidian-update/skills/obsidian-update/SKILL.md")

        self.assertIn("Knowledge candidates", skill)
        self.assertIn("producing plugin", skill.lower())
        self.assertIn("supporting Taskade and Git sources", skill)
        self.assertIn("Wait for confirmation before writing", skill)

    def test_memory_system_keeps_working_artifacts_out_of_company_memory(self):
        skill = read("plugins/obsidian-update/skills/memory-system/SKILL.md")

        self.assertIn("company-wide long-term memory", skill)
        self.assertIn("Working artifacts remain in Taskade", skill)
        self.assertIn("Code remains in the declared Git repository", skill)


class GovernanceContractTests(unittest.TestCase):
    def test_project_init_governance_covers_surface_manifest_writes(self):
        governance = read("plugins/project-init/GOVERNANCE.md")

        self.assertIn("project-surfaces.json", governance)
        self.assertIn("side-effectful-gated", governance)

    def test_obsidian_update_governance_covers_candidate_promotion(self):
        governance = read("plugins/obsidian-update/GOVERNANCE.md")

        self.assertIn("knowledge candidate", governance.lower())
        self.assertIn("approval", governance.lower())


class RuntimeFederationContractTests(unittest.TestCase):
    def test_project_init_registers_an_always_on_federation_preflight(self):
        plugin = json.loads(read("plugins/project-init/.claude-plugin/plugin.json"))
        self.assertEqual(plugin["hooks"], "./hooks/hooks.json")
        hooks = json.loads(read("plugins/project-init/hooks/hooks.json"))
        self.assertIn("SessionStart", hooks["hooks"])
        preflight = read("plugins/project-init/hooks/federated-context-preflight.py")
        self.assertIn("Before every MoxyWolf plugin action", preflight)
        self.assertIn("vault-context.json", preflight)

    def test_knowledge_candidates_have_a_machine_readable_transport(self):
        schema = json.loads(read("plugins/project-init/schemas/knowledge-candidate.schema.json"))
        obsidian_schema = json.loads(read("plugins/obsidian-update/schemas/knowledge-candidate.schema.json"))
        self.assertEqual(schema, obsidian_schema)
        required = set(schema["items"]["required"])
        self.assertTrue({"producing_plugin", "claim", "rationale", "project_id", "supporting_sources", "proposed_route"} <= required)
        session_end = read("plugins/project-init/skills/session-end/SKILL.md")
        obsidian = read("plugins/obsidian-update/skills/obsidian-update/SKILL.md")
        self.assertIn("knowledge-candidates.json", session_end)
        self.assertIn("knowledge-candidate.schema.json", session_end)
        self.assertIn("knowledge-candidates.json", obsidian)
        self.assertIn("deferred", schema["items"]["properties"]["status"]["enum"])
        self.assertIn("MoxyWolf Vault", schema["items"]["properties"]["proposed_route"]["pattern"])
        source_path = schema["items"]["properties"]["supporting_sources"]["items"]["properties"]["path"]
        self.assertIn("pattern", source_path)


if __name__ == "__main__":
    unittest.main()
