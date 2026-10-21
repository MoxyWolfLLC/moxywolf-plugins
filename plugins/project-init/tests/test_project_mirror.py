"""SM-007 criterion 6: the mirror plan is decided by sha256 against the sidecar, and by nothing else."""
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import project_mirror as pm  # noqa: E402

HUB = pm.HUB


class ProjectMirror(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name) / "Taskade"
        hub = self.root / "Demo" / HUB
        hub.mkdir(parents=True)
        (self.root / "_Shared Files" / "_shared-memory").mkdir(parents=True)
        self.surfaces = hub / "project-surfaces.json"
        self.surfaces.write_text(json.dumps({"workspace": {"path": "Taskade/Demo"}}), encoding="utf-8")
        (hub / "cowork-project-instructions.md").write_text("instructions v1\n", encoding="utf-8")
        (hub / "cowork-session-handoff.md").write_text("handoff v1\n", encoding="utf-8")
        (self.root / pm.SHARED_INDEX).write_text("index v1\n", encoding="utf-8")
        self.project, self.docs = pm.load(self.surfaces)

    def tearDown(self):
        self.tmp.cleanup()

    def plan(self):
        return pm.plan(self.root, self.project, self.docs)

    def record_all(self, p):
        for e in p["write"]:
            pm.record(self.root, self.project, e["path"], e["sha256"])

    def test_defaults_to_the_four(self):
        self.assertEqual(len(self.docs), 4)
        self.assertIn(pm.SHARED_INDEX, self.docs)

    def test_first_plan_writes_everything_then_nothing(self):
        p = self.plan()
        self.assertEqual(sorted(e["path"] for e in p["write"]), sorted(self.docs))
        self.assertEqual(p["unchanged"], [])
        self.assertEqual(p["missing"], [])
        self.record_all(p)
        q = self.plan()
        self.assertEqual(q["write"], [])
        self.assertEqual(sorted(e["path"] for e in q["unchanged"]), sorted(self.docs))
        self.assertTrue(all(e["mirrored_at"] for e in q["unchanged"]))

    def test_one_edit_moves_exactly_that_path(self):
        self.record_all(self.plan())
        (self.root / "Demo" / HUB / "cowork-session-handoff.md").write_text("handoff v2\n", encoding="utf-8")
        p = self.plan()
        self.assertEqual([e["path"] for e in p["write"]], [f"Demo/{HUB}/cowork-session-handoff.md"])
        self.assertEqual(len(p["unchanged"]), 3)

    def test_missing_and_outside_root_are_named(self):
        self.docs = self.docs + ["Demo/nope.md", "../escape.md"]
        p = self.plan()
        reasons = {m["path"]: m["reason"] for m in p["missing"]}
        self.assertEqual(reasons["Demo/nope.md"], "not on disk")
        self.assertEqual(reasons["../escape.md"], "outside the Taskade root")

    def test_record_writes_only_the_sidecar(self):
        before = {str(p) for p in self.root.rglob("*") if p.is_file()}
        self.record_all(self.plan())
        after = {str(p) for p in self.root.rglob("*") if p.is_file()}
        self.assertEqual(after - before, {str(self.root / "Demo" / HUB / pm.SIDECAR)})
        self.assertEqual(sorted(os.listdir(self.tmp.name)), ["Taskade"])


if __name__ == "__main__":
    unittest.main()
