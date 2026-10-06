#!/usr/bin/env python3
"""GO-010: goal mode's local checks for a repository with no onboarding."""
import os
import subprocess
import tempfile
import unittest
from pathlib import Path

import goal_local as gl

BRIEF = "# g\n\n## Allowed paths\n- src/*.ts\n"


def repo(t):
    r = Path(t) / "r"
    r.mkdir()
    for c in (["init", "-q", "-b", "main"], ["config", "user.email", "t@t"], ["config", "user.name", "t"],
              ["config", "maintenance.auto", "false"], ["config", "gc.auto", "0"]):
        subprocess.run(["git", *c], cwd=r, check=True, capture_output=True)
    return r


def commit(r, files, msg="c"):
    for f, body in files.items():
        Path(r, f).parent.mkdir(parents=True, exist_ok=True)
        Path(r, f).write_text(body)
    subprocess.run(["git", "add", "-A"], cwd=r, check=True, capture_output=True)
    subprocess.run(["git", "commit", "-qm", msg], cwd=r, check=True, capture_output=True)
    return subprocess.run(["git", "rev-parse", "HEAD"], cwd=r, capture_output=True, text=True).stdout.strip()


class Local(unittest.TestCase):
    def test_envelope_without_codeowners_guards_the_gate_and_allowed_paths(self):
        with tempfile.TemporaryDirectory() as t:
            r = repo(t)
            commit(r, {"README.md": "x\n"})
            subprocess.run(["git", "switch", "-qc", "goal/g"], cwd=r, check=True)
            head = commit(r, {"src/a.ts": "1\n", ".github/workflows/x.yml": "y\n", "docs/n.md": "z\n"})
            errors, n = gl.envelope(r, "g", head, "main", BRIEF)
            self.assertEqual(n, 1)
            self.assertEqual(sorted(e.split(" ", 2)[2] for e in errors),
                             [".github/workflows/x.yml, a gate path", "docs/n.md, outside Allowed paths"])

    def test_envelope_passes_inside_allowed_paths(self):
        with tempfile.TemporaryDirectory() as t:
            r = repo(t)
            commit(r, {"README.md": "x\n"})
            subprocess.run(["git", "switch", "-qc", "goal/g"], cwd=r, check=True)
            head = commit(r, {"src/a.ts": "1\n"})
            self.assertEqual(gl.envelope(r, "g", head, "main", BRIEF), ([], 1))

    def test_manifests_are_the_install_files_only_and_refuse_a_symlink(self):
        with tempfile.TemporaryDirectory() as t:
            r = repo(t)
            commit(r, {"package.json": "{}", "apps/a/package.json": "{}", "pnpm-lock.yaml": "x", "pnpm-workspace.yaml": "x",
                       ".npmrc": "x", "src/a.ts": "1", "apps/a/index.ts": "1"})
            self.assertEqual(sorted(gl.manifests(r)), [".npmrc", "apps/a/package.json", "package.json",
                                                        "pnpm-lock.yaml", "pnpm-workspace.yaml"])
            os.symlink("/etc/passwd", Path(r, "packages/b/package.json").parent.mkdir(parents=True) or Path(r, "packages/b/package.json"))
            commit(r, {}, "link")
            with self.assertRaises(SystemExit):
                gl.manifests(r)

    def test_workspace_links_point_at_the_sandbox_copy(self):
        with tempfile.TemporaryDirectory() as t:
            r = repo(t)
            commit(r, {"package.json": "{}", "pnpm-lock.yaml": "x", "packages/u/package.json": "{}"})

            def fake(cmd, **kw):              # stands in for the networked pnpm container
                deps = Path(cmd[cmd.index("-v") + 1].split(":")[0])
                (deps / "node_modules" / "@r").mkdir(parents=True)
                os.symlink("../../packages/u", deps / "node_modules" / "@r" / "u")
                os.symlink("left-pad-real", deps / "node_modules" / "left-pad")
                (deps / "node_modules" / "left-pad-real").mkdir()
                return subprocess.CompletedProcess(cmd, 0, "", "")
            deps = gl.pnpm_deps(r, run=fake)
            self.assertEqual(os.readlink(deps / "node_modules" / "@r" / "u"), "/tmp/candidate/packages/u")
            self.assertEqual(os.readlink(deps / "node_modules" / "left-pad"), "left-pad-real")


if __name__ == "__main__":
    unittest.main()
