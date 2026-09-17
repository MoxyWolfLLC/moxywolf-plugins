from __future__ import annotations

import json
import os
import re
import tempfile
import unittest
from pathlib import Path

from tests.support import create_standard_project, run_script, write_json


class FederatedContextTests(unittest.TestCase):
    def resolve(self, root: Path, intent: str, declaration: dict | None = None):
        taskade, vault, github = create_standard_project(root)
        plugin_root = root / "plugin"
        write_json(
            plugin_root / "vault-context.json",
            declaration or {
                "schema_version": 1,
                "planes": {
                    "project_workspace": "required",
                    "company_memory": "required",
                    "repositories": "optional",
                },
                "memory_scopes": ["project-moc", "recent-decisions", "shared-operating-norms", "derived-graphs"],
                "outputs": ["working-artifact", "knowledge-candidate"],
            },
        )
        return run_script(
            "federated_context.py",
            "resolve",
            "--plugin-root",
            plugin_root,
            "--project",
            "Team Plugins",
            "--intent",
            intent,
            "--taskade-root",
            taskade,
            "--vault-root",
            vault,
            "--github-root",
            github,
        )

    def test_current_work_prioritizes_project_workspace(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = self.resolve(Path(tmp), "current-work")

            self.assertEqual(result.returncode, 0, result.stderr)
            packet = json.loads(result.stdout)
            self.assertEqual(packet["sources"][0]["plane"], "project-workspace")
            self.assertEqual(packet["authority_domain"], "current-project-work")

    def test_code_behavior_prioritizes_live_repository(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = self.resolve(Path(tmp), "code-behavior")

            self.assertEqual(result.returncode, 0, result.stderr)
            packet = json.loads(result.stdout)
            self.assertEqual(packet["sources"][0]["plane"], "code-workspace")
            self.assertEqual(packet["sources"][0]["kind"], "repository-root")
            self.assertTrue(packet["sources"][0]["path"].endswith("GitHub/moxywolf-plugins"))
            self.assertEqual(packet["authority_domain"], "executable-technical-truth")

    def test_none_plane_is_not_collected(self):
        with tempfile.TemporaryDirectory() as tmp:
            declaration = {
                "schema_version": 1,
                "planes": {
                    "project_workspace": "required",
                    "company_memory": "none",
                    "repositories": "none",
                },
                "memory_scopes": [],
                "outputs": ["working-artifact"],
            }
            result = self.resolve(Path(tmp), "current-work", declaration)

            self.assertEqual(result.returncode, 0, result.stderr)
            packet = json.loads(result.stdout)
            self.assertEqual({source["plane"] for source in packet["sources"]}, {"project-workspace"})

    def test_discovery_is_bounded_and_ignores_dependency_directories(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for index in range(240):
                target = root / "Taskade" / "Team Plugins" / "notes" / f"note-{index:03}.md"
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text("# note\n", encoding="utf-8")
            ignored = root / "Taskade" / "Team Plugins" / "node_modules" / "ignored.md"
            ignored.parent.mkdir(parents=True, exist_ok=True)
            ignored.write_text("# ignored\n", encoding="utf-8")
            result = self.resolve(root, "current-work")

            self.assertEqual(result.returncode, 0, result.stderr)
            packet = json.loads(result.stdout)
            project_sources = [source for source in packet["sources"] if source["plane"] == "project-workspace"]
            self.assertLessEqual(len(project_sources), 200)
            self.assertFalse(any("node_modules" in source["path"] for source in project_sources))
            self.assertTrue(any("source limit" in warning.lower() for warning in packet["warnings"]))

    def test_derived_graphs_require_an_explicit_memory_scope(self):
        with tempfile.TemporaryDirectory() as tmp:
            declaration = {
                "schema_version": 1,
                "planes": {"project_workspace": "optional", "company_memory": "required", "repositories": "none"},
                "memory_scopes": ["project-moc"],
                "outputs": ["knowledge-candidate"],
            }
            result = self.resolve(Path(tmp), "company-knowledge", declaration)

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertFalse(any(source["authority"] == "derived" for source in json.loads(result.stdout)["sources"]))

    def test_decision_discovery_filters_before_applying_the_source_limit(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            memory = root / "MoxyWolf Vault" / "Projects" / "Moxywolf Plugins"
            for index in range(240):
                target = memory / f"000-note-{index:03}.md"
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text("# note\n", encoding="utf-8")
            result = self.resolve(root, "historical-rationale")

            self.assertEqual(result.returncode, 0, result.stderr)
            paths = [source["path"] for source in json.loads(result.stdout)["sources"]]
            self.assertTrue(any(path.endswith("DR-014-context-contract.md") for path in paths))

    def test_recent_decision_limit_keeps_newest_records_not_first_traversed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            memory = root / "MoxyWolf Vault" / "Projects" / "Moxywolf Plugins" / "decisions"
            for index in range(205):
                target = memory / f"DR-{index:03}.md"
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text("# decision\n", encoding="utf-8")
                os.utime(target, (index + 1, index + 1))
            result = self.resolve(root, "historical-rationale")

            self.assertEqual(result.returncode, 0, result.stderr)
            paths = [source["path"] for source in json.loads(result.stdout)["sources"]]
            self.assertTrue(any(path.endswith("DR-204.md") for path in paths))
            self.assertFalse(any(path.endswith("DR-000.md") for path in paths))

    def test_historical_rationale_prioritizes_vault_decisions(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = self.resolve(Path(tmp), "historical-rationale")

            self.assertEqual(result.returncode, 0, result.stderr)
            packet = json.loads(result.stdout)
            self.assertEqual(packet["sources"][0]["plane"], "company-memory")
            self.assertIn("DR-014", packet["sources"][0]["path"])
            self.assertEqual(packet["authority_domain"], "institutional-rationale")

    def test_company_knowledge_includes_project_and_shared_memory(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = self.resolve(Path(tmp), "company-knowledge")

            self.assertEqual(result.returncode, 0, result.stderr)
            packet = json.loads(result.stdout)
            paths = [source["path"] for source in packet["sources"]]
            self.assertTrue(any("Moxywolf Plugins Index.md" in path for path in paths))
            self.assertTrue(any("norm-provenance.md" in path for path in paths))

    def test_excludes_credentials_and_downgrades_generated_graphs(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = self.resolve(Path(tmp), "company-knowledge")

            self.assertEqual(result.returncode, 0, result.stderr)
            packet = json.loads(result.stdout)
            source_paths = [source["path"] for source in packet["sources"]]
            self.assertFalse(any(path.endswith(".env") for path in source_paths))
            exclusions = {item["path"]: item["reason"] for item in packet["excluded"]}
            self.assertTrue(any(path.endswith("openrouter.env") for path in exclusions))
            graph = next(source for source in packet["sources"] if source["path"].endswith("graph.md"))
            self.assertEqual(graph["authority"], "derived")

    def test_reports_missing_required_plane(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            taskade, vault, github = create_standard_project(root)
            plugin_root = root / "plugin"
            write_json(
                plugin_root / "vault-context.json",
                {
                    "schema_version": 1,
                    "planes": {
                        "project_workspace": "required",
                        "company_memory": "required",
                        "repositories": "required",
                    },
                    "memory_scopes": [],
                    "outputs": [],
                },
            )
            for path in sorted((github / "moxywolf-plugins").rglob("*"), reverse=True):
                if path.is_file():
                    path.unlink()
                else:
                    path.rmdir()
            (github / "moxywolf-plugins").rmdir()
            result = run_script(
                "federated_context.py",
                "resolve",
                "--plugin-root",
                plugin_root,
                "--project",
                "Team Plugins",
                "--intent",
                "code-behavior",
                "--taskade-root",
                taskade,
                "--vault-root",
                vault,
                "--github-root",
                github,
            )

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("required", result.stderr.lower())


class MarketplaceContractTests(unittest.TestCase):
    def test_marketplace_and_package_versions_match(self):
        root = Path(__file__).resolve().parents[1]
        marketplace = json.loads((root / ".claude-plugin" / "marketplace.json").read_text())
        for plugin in marketplace["plugins"]:
            manifest = json.loads((root / plugin["source"] / ".claude-plugin" / "plugin.json").read_text())
            with self.subTest(plugin=plugin["name"]):
                self.assertEqual(plugin["version"], manifest["version"])

    def test_every_marketplace_plugin_has_valid_context_declaration(self):
        result = run_script("validate_federated_contract.py")

        self.assertEqual(result.returncode, 0, result.stderr)
        report = json.loads(result.stdout)
        self.assertEqual(report["missing"], [])
        self.assertEqual(report["invalid"], [])
        self.assertGreater(report["validated_plugins"], 20)

    def test_every_independent_plugin_bundles_federation_preflight(self):
        marketplace = json.loads((Path(__file__).resolve().parents[1] / ".claude-plugin" / "marketplace.json").read_text())
        for plugin in marketplace["plugins"]:
            if plugin["name"] == "project-init":
                continue
            with self.subTest(plugin=plugin["name"]):
                source = Path(__file__).resolve().parents[1] / plugin["source"]
                preflight = source / "skills" / "federated-context-preflight" / "SKILL.md"
                self.assertTrue(preflight.exists(), preflight)
                content = preflight.read_text(encoding="utf-8")
                self.assertIn("Before any other skill or command from this plugin", content)
                self.assertIn("knowledge-candidates.json", content)


class CandidateSchemaSecurityTests(unittest.TestCase):
    def test_rooted_candidate_patterns_reject_immediate_and_nested_traversal(self):
        root = Path(__file__).resolve().parents[1]
        for relative in (
            "plugins/project-init/schemas/knowledge-candidate.schema.json",
            "plugins/obsidian-update/schemas/knowledge-candidate.schema.json",
        ):
            schema = json.loads((root / relative).read_text())
            route_pattern = schema["items"]["properties"]["proposed_route"]["pattern"]
            source_pattern = schema["items"]["properties"]["supporting_sources"]["items"]["properties"]["path"]["pattern"]
            self.assertIsNone(re.fullmatch(route_pattern, "MoxyWolf Vault/../outside"))
            self.assertIsNone(re.fullmatch(route_pattern, "MoxyWolf Vault/Projects/X/../outside"))
            for path in ("Taskade/../outside", "GitHub/../outside", "MoxyWolf Vault/../outside"):
                self.assertIsNone(re.fullmatch(source_pattern, path), path)
            self.assertIsNotNone(re.fullmatch(route_pattern, "MoxyWolf Vault/Projects/SAMS/11-Knowledge/note.md"))


if __name__ == "__main__":
    unittest.main()
