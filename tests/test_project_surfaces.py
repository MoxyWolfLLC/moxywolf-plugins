from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from tests.support import create_standard_project, run_script, standard_manifest, write_json, write_text


class ProjectSurfaceResolutionTests(unittest.TestCase):
    def resolve(self, taskade: Path, vault: Path, github: Path, project: str = "Team Plugins"):
        return run_script(
            "project_surfaces.py",
            "resolve",
            "--project",
            project,
            "--taskade-root",
            taskade,
            "--vault-root",
            vault,
            "--github-root",
            github,
        )

    def test_resolves_taskade_workspace_vault_memory_and_repository(self):
        with tempfile.TemporaryDirectory() as tmp:
            taskade, vault, github = create_standard_project(Path(tmp))
            result = self.resolve(taskade, vault, github)

            self.assertEqual(result.returncode, 0, result.stderr)
            packet = json.loads(result.stdout)
            self.assertEqual(packet["project_id"], "team-plugins")
            self.assertEqual(packet["workspace"]["plane"], "project-workspace")
            self.assertTrue(packet["workspace"]["path"].endswith("Taskade/Team Plugins"))
            self.assertTrue(packet["memory"]["path"].endswith("MoxyWolf Vault/Projects/Moxywolf Plugins"))
            self.assertEqual(packet["repositories"][0]["access"], "read-write")

    def test_resolves_project_alias(self):
        with tempfile.TemporaryDirectory() as tmp:
            taskade, vault, github = create_standard_project(Path(tmp))
            result = self.resolve(taskade, vault, github, "Moxywolf Plugins")

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(json.loads(result.stdout)["display_name"], "Team Plugins")

    def test_supports_project_without_repository(self):
        with tempfile.TemporaryDirectory() as tmp:
            manifest = standard_manifest(repositories=[])
            taskade, vault, github = create_standard_project(Path(tmp), manifest)
            result = self.resolve(taskade, vault, github)

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(json.loads(result.stdout)["repositories"], [])

    def test_preserves_multiple_repository_roles_and_access(self):
        with tempfile.TemporaryDirectory() as tmp:
            repos = [
                {"path": "GitHub/moxywolf-plugins", "access": "read-write", "role": "source"},
                {"path": "GitHub/reference-plugin", "access": "read-only", "role": "reference"},
            ]
            manifest = standard_manifest(repositories=repos)
            taskade, vault, github = create_standard_project(Path(tmp), manifest)
            write_text(github / "reference-plugin" / "README.md", "# Reference\n")
            result = self.resolve(taskade, vault, github)

            self.assertEqual(result.returncode, 0, result.stderr)
            packet = json.loads(result.stdout)
            self.assertEqual([repo["access"] for repo in packet["repositories"]], ["read-write", "read-only"])
            self.assertEqual([repo["role"] for repo in packet["repositories"]], ["source", "reference"])

    def test_preserves_declared_related_taskade_workspace_without_replacing_primary(self):
        with tempfile.TemporaryDirectory() as tmp:
            manifest = standard_manifest()
            manifest["related_workspaces"] = [
                {
                    "path": "Taskade/Workforce Automation",
                    "access": "read-write",
                    "role": "related workforce vocabulary work",
                }
            ]
            taskade, vault, github = create_standard_project(Path(tmp), manifest)
            write_text(taskade / "Workforce Automation" / "README.md", "# Workforce Automation\n")
            result = self.resolve(taskade, vault, github)

            self.assertEqual(result.returncode, 0, result.stderr)
            packet = json.loads(result.stdout)
            self.assertTrue(packet["workspace"]["path"].endswith("Taskade/Team Plugins"))
            self.assertEqual(len(packet.get("related_workspaces", [])), 1)
            self.assertTrue(packet["related_workspaces"][0]["path"].endswith("Taskade/Workforce Automation"))
            self.assertEqual(packet["related_workspaces"][0]["role"], "related workforce vocabulary work")

    def test_resolves_explicit_vault_only_exception(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            taskade, vault, github = root / "Taskade", root / "MoxyWolf Vault", root / "GitHub"
            manifest = standard_manifest(
                project_id="research-council",
                display_name="Research Council",
                aliases=[],
                workspace_type="vault-only",
                workspace_path="MoxyWolf Vault/Projects/Research Council",
                memory_path="MoxyWolf Vault/Projects/Research Council",
                moc="00-Hub/Research Council Index.md",
                repositories=[],
            )
            write_json(vault / "Projects" / "Research Council" / "00-Hub" / "project-surfaces.json", manifest)
            write_text(vault / "Projects" / "Research Council" / "00-Hub" / "Research Council Index.md", "# Research Council\n")
            result = self.resolve(taskade, vault, github, "Research Council")

            self.assertEqual(result.returncode, 0, result.stderr)
            packet = json.loads(result.stdout)
            self.assertEqual(packet["workspace"]["type"], "vault-only")
            self.assertEqual(packet["workspace"]["plane"], "project-workspace")

    def test_reports_missing_declared_repository_without_inventing_one(self):
        with tempfile.TemporaryDirectory() as tmp:
            taskade, vault, github = create_standard_project(Path(tmp))
            for child in (github / "moxywolf-plugins").iterdir():
                if child.is_file():
                    child.unlink()
                else:
                    for nested in sorted(child.rglob("*"), reverse=True):
                        if nested.is_file():
                            nested.unlink()
                        else:
                            nested.rmdir()
                    child.rmdir()
            (github / "moxywolf-plugins").rmdir()
            result = self.resolve(taskade, vault, github)

            self.assertEqual(result.returncode, 0, result.stderr)
            packet = json.loads(result.stdout)
            self.assertEqual(len(packet["repositories"]), 1)
            self.assertFalse(packet["repositories"][0]["available"])
            self.assertIn("missing", packet["warnings"][0].lower())

    def test_rejects_path_outside_approved_roots(self):
        with tempfile.TemporaryDirectory() as tmp:
            manifest = standard_manifest(workspace_path="Taskade/../Other Project")
            taskade, vault, github = create_standard_project(Path(tmp), manifest)
            result = self.resolve(taskade, vault, github)

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("approved roots", result.stderr.lower())

    def test_rejects_plane_paths_under_the_wrong_root(self):
        cases = [
            ("workspace", standard_manifest(workspace_path="MoxyWolf Vault/Projects/Moxywolf Plugins")),
            ("memory", standard_manifest(memory_path="Taskade/Team Plugins")),
            ("repository", standard_manifest(repositories=[{"path": "Taskade/Team Plugins", "access": "read-write", "role": "wrong"}])),
        ]
        for label, manifest in cases:
            with self.subTest(label=label), tempfile.TemporaryDirectory() as tmp:
                taskade, vault, github = create_standard_project(Path(tmp), manifest)
                result = self.resolve(taskade, vault, github)

                self.assertNotEqual(result.returncode, 0)
                self.assertIn("must use", result.stderr.lower())

    def test_rejects_related_workspace_outside_taskade(self):
        with tempfile.TemporaryDirectory() as tmp:
            manifest = standard_manifest()
            manifest["related_workspaces"] = [
                {"path": "MoxyWolf Vault/Projects/Moxywolf Plugins", "access": "read-only", "role": "wrong"}
            ]
            taskade, vault, github = create_standard_project(Path(tmp), manifest)
            result = self.resolve(taskade, vault, github)

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("taskade", result.stderr.lower())

    def test_rejects_moc_traversal_outside_memory_root(self):
        with tempfile.TemporaryDirectory() as tmp:
            manifest = standard_manifest(moc="../Other Project/Index.md")
            taskade, vault, github = create_standard_project(Path(tmp), manifest)
            result = self.resolve(taskade, vault, github)

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("moc", result.stderr.lower())

    def test_rejects_symlink_escape_from_declared_root(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            taskade, vault, github = create_standard_project(root)
            outside = root / "outside"
            outside.mkdir()
            link = github / "escape"
            link.symlink_to(outside, target_is_directory=True)
            manifest_path = taskade / "Team Plugins" / "00 – Project Hub" / "project-surfaces.json"
            manifest = json.loads(manifest_path.read_text())
            manifest["repositories"] = [{"path": "GitHub/escape", "access": "read-write", "role": "escape"}]
            write_json(manifest_path, manifest)
            result = self.resolve(taskade, vault, github)

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("escapes", result.stderr.lower())

    def test_rejects_duplicate_alias_across_projects(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            taskade, vault, github = create_standard_project(root)
            duplicate = standard_manifest(
                project_id="other-project",
                display_name="Other Project",
                aliases=["Moxywolf Plugins"],
                workspace_path="Taskade/Other Project",
                memory_path="MoxyWolf Vault/Projects/Other Project",
                moc="00-Hub/Other Project Index.md",
                repositories=[],
            )
            write_json(taskade / "Other Project" / "00 – Project Hub" / "project-surfaces.json", duplicate)
            write_text(vault / "Projects" / "Other Project" / "00-Hub" / "Other Project Index.md", "# Other\n")
            result = self.resolve(taskade, vault, github, "Moxywolf Plugins")

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("ambiguous", result.stderr.lower())

    def test_fails_closed_for_legacy_project_without_manifest(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            taskade, vault, github = root / "Taskade", root / "MoxyWolf Vault", root / "GitHub"
            write_text(taskade / "Legacy" / "00 – Project Hub" / "cowork-project-instructions.md", "# Legacy\n")
            result = self.resolve(taskade, vault, github, "Legacy")

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("project-surfaces.json", result.stderr)


class OutputRoutingTests(unittest.TestCase):
    def route(self, taskade: Path, vault: Path, github: Path, output_type: str, *extra: str):
        return run_script(
            "project_surfaces.py",
            "route",
            "--project",
            "Team Plugins",
            "--output-type",
            output_type,
            "--taskade-root",
            taskade,
            "--vault-root",
            vault,
            "--github-root",
            github,
            *extra,
        )

    def test_routes_working_artifact_to_taskade(self):
        with tempfile.TemporaryDirectory() as tmp:
            taskade, vault, github = create_standard_project(Path(tmp))
            result = self.route(taskade, vault, github, "working-artifact")

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(json.loads(result.stdout)["plane"], "project-workspace")

    def test_routes_code_change_only_to_declared_writable_repository(self):
        with tempfile.TemporaryDirectory() as tmp:
            taskade, vault, github = create_standard_project(Path(tmp))
            result = self.route(taskade, vault, github, "code-change", "--repository", "moxywolf-plugins")

            self.assertEqual(result.returncode, 0, result.stderr)
            packet = json.loads(result.stdout)
            self.assertEqual(packet["plane"], "code-workspace")
            self.assertEqual(packet["access"], "read-write")

    def test_routes_durable_knowledge_to_approval_not_direct_write(self):
        with tempfile.TemporaryDirectory() as tmp:
            taskade, vault, github = create_standard_project(Path(tmp))
            result = self.route(taskade, vault, github, "durable-knowledge")

            self.assertEqual(result.returncode, 0, result.stderr)
            packet = json.loads(result.stdout)
            self.assertEqual(packet["plane"], "company-memory")
            self.assertEqual(packet["action"], "propose-via-obsidian-update")
            self.assertFalse(packet["write_authorized"])


if __name__ == "__main__":
    unittest.main()
