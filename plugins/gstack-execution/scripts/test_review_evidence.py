#!/usr/bin/env python3
"""XE-018 acceptance: the surface carries the files a change names, and CI runs the dispatcher
read itself, bound to the head they ran at.

SAMS PL-001 is the case: ci.yml calls scripts/local-supabase.ts, a test imports ./client, and a
criterion names apps/web. None of them reached the reviewer, and neither did the green CI run.
"""
import json, os, shutil, subprocess, sys, tempfile, unittest
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import peer_review as pr


class SurfaceEvidenceTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="xe018-"))
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        self.repo = self.tmp / "app"; self.repo.mkdir()
        self.sh("init", "-q"); self.sh("config", "user.email", "t@t"); self.sh("config", "user.name", "t")
        self.sh("remote", "add", "origin", "https://github.com/acme/app.git")
        self.write("scripts/local-supabase.ts", "export const up = 1;\n")
        self.write("db/client.ts", "export const db = {};\n")
        self.write("apps/web/package.json", "{}\n")
        self.write("apps/web/page.ts", "export {};\n")
        self.write("unrelated/thing.ts", "export {};\n")
        self.write("ci.yml", "steps: []\n")
        self.write("db/listing.test.ts", "// empty\n")
        self.sh("add", "."); self.sh("commit", "-qm", "base")
        self.base = self.sh("rev-parse", "HEAD")
        self.write("ci.yml", "steps:\n  - run: pnpm exec tsx scripts/local-supabase.ts migrate\n")
        self.write("db/listing.test.ts", 'import { db } from "./client";\n')
        self.sh("commit", "-qam", "head")
        self.head = self.sh("rev-parse", "HEAD")
        self.repos = [{"path": str(self.repo), "base": self.base, "head": self.head}]
        self.criteria = ["`cd apps/web && pnpm tsc --noEmit` passes.", "`scripts/local-supabase.ts migrate` works."]

    def sh(self, *a):
        return subprocess.run(["git", "-C", str(self.repo), *a], check=True, capture_output=True, text=True).stdout.strip()

    def write(self, rel, text):
        f = self.repo / rel; f.parent.mkdir(parents=True, exist_ok=True); f.write_text(text)

    def surface(self, **kw):
        out = self.tmp / f"out-{len(list(self.tmp.iterdir()))}"; out.mkdir()
        return pr.build_surface(self.repos, out, **kw)

    def test_named_imported_and_criterion_files_are_carried(self):
        surf, stats = self.surface(criteria=self.criteria)
        deps = surf / "dependencies" / "0-app"
        self.assertTrue((deps / "scripts/local-supabase.ts").exists(), "named by path in ci.yml")
        self.assertTrue((deps / "db/client.ts").exists(), "imported as ./client")
        self.assertTrue((deps / "apps/web/package.json").exists(), "manifest of a directory a criterion names")
        self.assertFalse((deps / "unrelated/thing.ts").exists())
        self.assertFalse((deps / "ci.yml").exists(), "a changed file is not also a dependency")
        self.assertEqual(stats["dependencies"], 3)
        text = (surf / "SURFACE.md").read_text()
        self.assertIn("imported by db/listing.test.ts", text)
        self.assertIn("named in an acceptance criterion", text)

    def test_cap_reports_what_it_withheld(self):
        surf, stats = self.surface(criteria=self.criteria, cap=1)
        self.assertEqual(stats["dependencies"], 1)
        self.assertEqual(stats["dependencies_withheld"], 2)
        self.assertIn("dependencies withheld by the same cap: 2", (surf / "SURFACE.md").read_text())

    def fake_github(self, head_sha, fail=False):
        def get(name, path):
            self.assertEqual(name, "acme/app")
            if fail:
                raise pr.ReviewError("release_unavailable", "403 Resource not accessible")
            if "/jobs?per_page=100" in path:
                return {"total_count": 1, "jobs": [{"name": "Unit", "conclusion": "success",
                                  "steps": [{"name": "Run listing test", "conclusion": "success"}]}]}
            return {"html_url": "https://github.com/acme/app/actions/runs/7", "name": "CI",
                    "head_sha": head_sha, "status": "completed", "conclusion": "success"}
        return get

    def run_with(self, getter):
        orig = pr.github_get
        pr.github_get = getter
        try:
            return self.surface(ci_runs=[{"repo": "app", "run_id": 7}])
        finally:
            pr.github_get = orig

    def test_run_at_reviewed_head_is_evidence(self):
        surf, stats = self.run_with(self.fake_github(self.head))
        rec = json.loads((surf / "evidence" / "ci-7.json").read_text())
        self.assertTrue(rec["read"]); self.assertTrue(rec["head_matches"])
        self.assertEqual(rec["origin"], "gate_output")
        self.assertEqual(rec["jobs"][0]["steps"][0], {"name": "Run listing test", "conclusion": "success"})
        self.assertEqual(stats["evidence"], {"requested": 1, "read": 1, "head_matched": 1})
        self.assertIn("run at the reviewed head, conclusion success", (surf / "SURFACE.md").read_text())

    def test_run_at_another_head_is_written_and_marked(self):
        surf, stats = self.run_with(self.fake_github(self.base))
        rec = json.loads((surf / "evidence" / "ci-7.json").read_text())
        self.assertTrue(rec["read"]); self.assertFalse(rec["head_matches"])
        self.assertEqual(stats["evidence"]["head_matched"], 0)
        self.assertIn("NOT the reviewed head", (surf / "SURFACE.md").read_text())

    def test_unreadable_run_is_recorded_not_raised(self):
        surf, stats = self.run_with(self.fake_github(self.head, fail=True))
        rec = json.loads((surf / "evidence" / "ci-7.json").read_text())
        self.assertFalse(rec["read"]); self.assertIn("403", rec["error"])
        self.assertEqual(stats["evidence"], {"requested": 1, "read": 0, "head_matched": 0})
        self.assertIn("could not be read", (surf / "SURFACE.md").read_text())

    def test_root_file_and_top_level_directory_are_carried(self):
        self.write("Makefile", "all:\n"); self.write("tools/pyproject.toml", "[project]\n")
        self.sh("add", "."); self.sh("commit", "-qm", "more")
        self.base = self.sh("rev-parse", "HEAD")
        self.write("ci.yml", "steps:\n  - run: make -f Makefile\n"); self.sh("commit", "-qam", "use it")
        self.repos[0].update(base=self.base, head=self.sh("rev-parse", "HEAD"))
        surf, stats = self.surface(criteria=["`cd tools && pytest` passes."])
        deps = surf / "dependencies" / "0-app"
        self.assertTrue((deps / "Makefile").exists(), "a root-level file named in a changed file")
        self.assertTrue((deps / "tools/pyproject.toml").exists(), "manifest of a top-level directory")

    def test_every_page_of_jobs_is_written(self):
        head = self.head
        def get(name, path):
            if "/jobs?per_page=100&page=1" in path:
                return {"total_count": 101, "jobs": [{"name": f"j{i}", "conclusion": "success", "steps": []} for i in range(100)]}
            if "/jobs?per_page=100&page=2" in path:
                return {"total_count": 101, "jobs": [{"name": "j100", "conclusion": "success", "steps": []}]}
            return {"head_sha": head, "conclusion": "success"}
        surf, _ = self.run_with(get)
        rec = json.loads((surf / "evidence" / "ci-7.json").read_text())
        self.assertEqual(len(rec["jobs"]), 101)
        self.assertEqual(rec["jobs"][-1]["name"], "j100")

    def test_no_ci_runs_means_no_evidence_folder(self):
        surf, stats = self.surface()
        self.assertFalse((surf / "evidence").exists())
        self.assertEqual(stats["evidence"]["requested"], 0)


if __name__ == "__main__":
    unittest.main()
