#!/usr/bin/env python3
"""CC-002.11: council_cases.py on temporary folders standing in for the vault and staging. No network.
A fake gitleaks (COUNCIL_CASES_GITLEAKS) flags any file containing LEAKYKEY."""
import io, json, os, shutil, sys, tempfile, unittest
from contextlib import redirect_stdout, redirect_stderr
from datetime import timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import council_cases as cc

AUDIENCE = "Dorian and the MoxyWolf Shared Files organizers"


def run(*argv):
    out, err = io.StringIO(), io.StringIO()
    with redirect_stdout(out), redirect_stderr(err):
        rc = cc.main(list(argv))
    return rc, out.getvalue() + err.getvalue()


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.store = str(self.tmp / "council-cases")
        fake = self.tmp / "gitleaks"
        fake.write_text('#!/bin/sh\ngrep -rq LEAKYKEY "$2" && exit 1\nexit 0\n'); fake.chmod(0o755)
        self.env = {"COUNCIL_CASES_GITLEAKS": str(fake), "COUNCIL_CASES_STAGING": str(self.tmp / "staging"),
                    "COUNCIL_CASES_DEVICE": "writer-dev"}
        self.old = {k: os.environ.get(k) for k in self.env}
        os.environ.update(self.env)
        self.n = 0

    def tearDown(self):
        for k, v in self.old.items():
            os.environ.pop(k, None) if v is None else os.environ.__setitem__(k, v)
        shutil.rmtree(self.tmp)

    def init(self, audience=True, **kw):
        args = ["init", "--store", self.store]
        if audience:
            args += ["--audience", AUDIENCE, "--approved-by", "Dorian C", "--words", "Approved for this audience."]
        for e in kw.get("exclude", []):
            args += ["--exclude", e]
        self.assertEqual(run(*args)[0], 0)

    def deliberation(self, rating="positive", query=None, extra=""):
        self.n += 1
        d = {"workspace": "ws-1", "record_id": f"rec-{self.n}", "query": query or f"Question {self.n}? {extra}",
             "context": "Prior decision DR-1.", "responses": [{"model": "m1", "text": "Answer."}],
             "synthesis": "Synthesis.", "rating": rating, "deliberated_at": f"2026-11-17T10:{self.n % 60:02d}:00Z",
             "models": ["m1"]}
        p = self.tmp / f"d{self.n}.json"; p.write_text(json.dumps(d)); return p

    def stage(self, project="moxywolf-plugins", d=None, names=()):
        args = ["stage", "--store", self.store, "--input", str(d or self.deliberation()), "--project", project, "--by", "Dorian C"]
        for n in names:
            args += ["--name", n]
        rc, out = run(*args)
        return rc, out, (out.split("staged ")[1].split(":")[0] if rc == 0 else None)

    def confirm(self, cid, by="Dorian C", audience=AUDIENCE, words="Publish it."):
        return run("confirm", cid, "--store", self.store, "--by", by, "--audience", audience, "--retention", "12m-rule", "--words", words)

    def full(self, project="moxywolf-plugins", d=None):
        rc, out, cid = self.stage(project, d); self.assertEqual(rc, 0, out)
        self.assertEqual(run("scan", cid)[0], 0)
        self.assertEqual(self.confirm(cid)[0], 0)
        rc, out = run("publish", cid, "--store", self.store); self.assertEqual(rc, 0, out)
        return cid

    def S(self):
        return cc.Store(self.store)


class OptIn(Base):
    def test_no_case_on_skip_null_excluded_or_no_audience(self):
        self.init(audience=False)
        self.assertNotEqual(self.stage()[0], 0, "no audience approved")
        self.init()
        self.assertNotEqual(self.stage(d=self.deliberation(rating=None))[0], 0, "skip leaves the rating null")
        self.assertNotEqual(self.stage(d=self.deliberation(rating="skip"))[0], 0)
        self.assertNotEqual(self.stage(project="cki")[0], 0, "OpenControls project")
        self.assertFalse((self.tmp / "staging").exists() and any((self.tmp / "staging").iterdir()))
        self.assertTrue(cc.offer_save(self.S(), "moxywolf-plugins", "neutral"))

    def test_init_excludes_projects_naming_opencontrols(self):
        root = self.tmp / "Projects" / "X" / "00 – Project Hub"; root.mkdir(parents=True)
        (root / "project-surfaces.json").write_text(json.dumps({"project_id": "x-proj", "note": "OpenControls"}))
        run("init", "--store", self.store, "--projects-root", str(self.tmp / "Projects"))
        self.assertIn("x-proj", self.S().cfg["excluded_projects"])
        self.assertIn("living-lexicon", self.S().cfg["excluded_projects"])

    def test_audience_needs_approval_words(self):
        rc, out = run("init", "--store", self.store, "--audience", "anyone")
        self.assertEqual(rc, 2); self.assertIn("approved-by", out)


class Redaction(Base):
    def test_placeholders_names_and_counts(self):
        self.init()
        token = "ghp_" + "a" * 36
        d = self.deliberation(extra=f"mail a@b.com and a@b.com, c@d.org; call 415-555-1212; acct 1234 5678 9012; {token}; Alice Smith met Bob")
        rc, out, cid = self.stage(d=d, names=["Alice Smith=client", "Bob=client"])
        self.assertEqual(rc, 0, out)
        text = (self.tmp / "staging" / cid / "case.md").read_text()
        for gone in ("a@b.com", "c@d.org", "415-555-1212", "1234 5678 9012", token, "Alice Smith", "Bob"):
            self.assertNotIn(gone, text)
        self.assertEqual(text.count("[EMAIL-1]"), 2); self.assertIn("[EMAIL-2]", text)
        self.assertIn("[PHONE-1]", text); self.assertIn("[ACCOUNT-1]", text)
        self.assertIn("[CLIENT-A]", text); self.assertIn("[CLIENT-B]", text)
        m = json.loads((self.tmp / "staging" / cid / "manifest.json").read_text())
        self.assertEqual(m["redaction"], {"secret": 1, "email": 2, "phone": 1, "account": 1, "name": 2})
        self.assertNotIn("a@b.com", json.dumps(m)); self.assertNotIn("Alice", json.dumps(m))
        self.assertIn("[CLIENT-A]", out)
        self.assertEqual(oct((self.tmp / "staging" / cid).stat().st_mode)[-3:], "700")

    def test_same_case_same_id(self):
        self.init()
        d = self.deliberation()
        self.assertEqual(self.stage(d=d)[2], self.stage(d=d)[2])


class Gate(Base):
    def setUp(self):
        super().setUp(); self.init()

    def test_confirm_after_scan_publishes_and_twice_changes_nothing(self):
        cid = self.full()
        before = sorted(p.name for p in (Path(self.store) / "inbox").glob("*.json"))
        rc, out = run("publish", cid, "--store", self.store)
        self.assertIn("already published", out)
        self.assertEqual(before, sorted(p.name for p in (Path(self.store) / "inbox").glob("*.json")))

    def test_refusals(self):
        rc, out, cid = self.stage()
        self.assertIn("no gitleaks receipt", run("publish", cid, "--store", self.store)[1])
        run("scan", cid)
        self.assertIn("not confirmed", run("publish", cid, "--store", self.store)[1])
        self.assertIn("doesn't match", self.confirm(cid, audience="everyone")[1])
        self.assertIn("only the person", self.confirm(cid, by="Mallory")[1])
        os.environ["COUNCIL_CASES_DEVICE"] = "other-dev"
        self.assertIn("only the person", self.confirm(cid)[1])
        os.environ["COUNCIL_CASES_DEVICE"] = "writer-dev"
        f = self.tmp / "staging" / cid / "case.md"; f.write_text(f.read_text() + "\nedit\n")
        self.assertIn("stale", run("publish", cid, "--store", self.store)[1])
        f.write_text(f.read_text() + "LEAKYKEY\n"); run("scan", cid)
        self.assertIn("found secrets", run("publish", cid, "--store", self.store)[1])

    def test_no_gitleaks_binary(self):
        rc, out, cid = self.stage()
        os.environ["COUNCIL_CASES_GITLEAKS"] = ""
        old = os.environ.get("PATH"); os.environ["PATH"] = ""
        try:
            self.assertIn("gitleaks not installed", run("scan", cid)[1])
        finally:
            os.environ["PATH"] = old

    def test_secret_in_confirmation_words_caught_by_manifest_scan(self):
        rc, out, cid = self.stage(); run("scan", cid)
        self.confirm(cid, words="ok LEAKYKEY")
        rc, out = run("publish", cid, "--store", self.store)
        self.assertIn("manifest scan found a secret", out)
        self.assertFalse(any((Path(self.store) / "inbox").glob("*.json")))

    def test_wrong_audience_and_excluded_project(self):
        rc, out, cid = self.stage(); run("scan", cid); self.confirm(cid)
        s = json.loads((Path(self.store) / "store.json").read_text()); s["audience"] = "changed"
        (Path(self.store) / "store.json").write_text(json.dumps(s))
        self.assertIn("confirmed audience", run("publish", cid, "--store", self.store)[1])
        s["audience"] = AUDIENCE; s["excluded_projects"].append("moxywolf-plugins")
        (Path(self.store) / "store.json").write_text(json.dumps(s))
        self.assertIn("excluded", run("publish", cid, "--store", self.store)[1])

    def test_interrupted_copy_finished_by_second_publish(self):
        cid = self.full()
        shutil.rmtree(Path(self.store) / "moxywolf-plugins" / cid)
        self.assertIn("finished the interrupted copy", run("publish", cid, "--store", self.store)[1])
        self.assertTrue((Path(self.store) / "moxywolf-plugins" / cid / "case.md").exists())

    def test_restaging_excluded_or_deleted_refused(self):
        d = self.deliberation()
        cid = self.full(d=d); run("apply", "--store", self.store)
        run("exclude", cid, "--store", self.store, "--reason", "test"); run("apply", "--store", self.store)
        rc, out, same = self.stage(d=d); self.assertEqual(same, cid)
        self.assertIn("is excluded", run("publish", cid, "--store", self.store)[1])
        rc, out, cid2 = self.stage(d=d, names=["Question=topic"])
        self.assertNotEqual(cid, cid2); run("scan", cid2); self.confirm(cid2)
        self.assertIn("already in the store", run("publish", cid2, "--store", self.store)[1])
        shutil.rmtree(Path(self.store) / "moxywolf-plugins" / cid)
        run("delete-record", cid, "--store", self.store); run("apply", "--store", self.store)
        self.assertEqual(self.S().current()[cid]["state"], "deleted")
        self.assertIn("already in the store", run("publish", cid2, "--store", self.store)[1])


class Atomic(Base):
    def setUp(self):
        super().setUp(); self.init()

    def test_apply_refuses_off_writer(self):
        os.environ["COUNCIL_CASES_DEVICE"] = "laptop"
        rc, out = run("apply", "--store", self.store)
        self.assertEqual(rc, 2); self.assertIn("writer-dev", out)

    def test_two_workspaces_in_order_unbroken_chain(self):
        a = self.full()
        os.environ["COUNCIL_CASES_DEVICE"] = "laptop"
        rc, out, b = self.stage(); run("scan", b); self.confirm(b); run("publish", b, "--store", self.store)
        os.environ["COUNCIL_CASES_DEVICE"] = "writer-dev"
        run("apply", "--store", self.store)
        lines = self.S().ledger()
        self.assertEqual([l["case_id"] for l in lines], [a, b])
        self.assertIsNone(lines[0]["prev"])
        self.assertEqual(lines[1]["prev"], cc.sha(json.dumps(lines[0], sort_keys=True)))
        self.assertTrue(all(l["writer"] == "writer-dev" for l in lines))
        self.assertEqual(run("verify", "--store", self.store)[0], 0)

    def test_interrupted_apply_recovered(self):
        cid = self.full(); run("apply", "--store", self.store)
        # killed after the ledger write, before the index and the request move
        (Path(self.store) / "index.json").unlink()
        for p in (Path(self.store) / "inbox" / "applied").glob("*.json"):
            shutil.move(str(p), Path(self.store) / "inbox" / p.name)
        run("apply", "--store", self.store)
        self.assertEqual(len(self.S().ledger()), 1)
        self.assertIn(cid, json.loads((Path(self.store) / "index.json").read_text())["cases"])
        self.assertEqual(self.S().inbox(), [])


class Integrity(Base):
    def setUp(self):
        super().setUp(); self.init()
        self.cid = self.full(); run("apply", "--store", self.store)
        self.case = Path(self.store) / "moxywolf-plugins" / self.cid

    def test_hand_edit_caught(self):
        (self.case / "case.md").write_text("changed")
        rc, out = run("verify", "--store", self.store)
        self.assertEqual(rc, 1); self.assertIn("case.md doesn't match", out); self.assertIn("not tamper evidence", out)

    def test_removed_line_caught(self):
        b = self.full(); run("apply", "--store", self.store)
        lines = self.S().ledger_path.read_text().splitlines()
        self.S().ledger_path.write_text(lines[1] + "\n")
        rc, out = run("verify", "--store", self.store)
        self.assertEqual(rc, 1); self.assertIn("chain broken", out)

    def test_conflict_copy_stops_everything(self):
        shutil.copy(self.S().ledger_path, Path(self.store) / "ledger (1).jsonl")
        self.assertEqual(run("verify", "--store", self.store)[0], 4)
        self.assertEqual(run("status", "--project", "moxywolf-plugins", "--store", self.store)[0], 4)
        self.assertEqual(run("apply", "--store", self.store)[0], 2)

    def test_pending_case_not_quarantined_and_verify_off_writer_writes_nothing(self):
        os.environ["COUNCIL_CASES_DEVICE"] = "laptop"
        rc, out, b = self.stage(); run("scan", b); self.confirm(b); run("publish", b, "--store", self.store)
        snap = {p: p.stat().st_mtime_ns for p in Path(self.store).rglob("*")}
        self.assertEqual(run("verify", "--store", self.store)[0], 0)
        self.assertEqual(snap, {p: p.stat().st_mtime_ns for p in Path(self.store).rglob("*")})
        os.environ["COUNCIL_CASES_DEVICE"] = "writer-dev"
        # the copy hasn't fully synced yet: apply leaves the add pending and must not quarantine the folder
        (Path(self.store) / "moxywolf-plugins" / b / "case.md").write_text("partial")
        run("apply", "--store", self.store)
        self.assertTrue((Path(self.store) / "moxywolf-plugins" / b).is_dir())
        self.assertEqual(len(self.S().inbox()), 1)

    def test_orphan_folder_quarantined_and_deleted_missing_folder_passes(self):
        orphan = Path(self.store) / "moxywolf-plugins" / "deadbeefdeadbeef"; orphan.mkdir()
        run("apply", "--store", self.store)
        self.assertFalse(orphan.exists()); self.assertTrue(any((Path(self.store) / "quarantine").iterdir()))
        shutil.rmtree(self.case); run("delete-record", self.cid, "--store", self.store)
        self.assertEqual(run("verify", "--store", self.store)[0], 0, "pending delete-record")
        run("apply", "--store", self.store)
        self.assertEqual(run("verify", "--store", self.store)[0], 0, "deleted")


class Retention(Base):
    def setUp(self):
        super().setUp(); self.init()

    def test_dates_by_state_pending_exclude_due_and_removal(self):
        a = self.full(); b = self.full(); run("apply", "--store", self.store)
        cur = self.S().current()
        self.assertEqual(cur[a]["state"], "active_held_out"); self.assertIsNone(cur[a]["delete_after"])
        self.assertEqual(cur[b]["state"], "active_proposal")
        self.assertEqual(cc.parse(cur[b]["delete_after"]), cc.parse(cur[b]["published_at"]) + timedelta(days=365))
        m = json.loads((Path(self.store) / "moxywolf-plugins" / a / "manifest.json").read_text())
        self.assertEqual(m["retention_rule"], cc.RULE); self.assertNotIn("delete_after", m)
        run("exclude", a, "--store", self.store, "--reason", "client asked")
        self.assertEqual(cc.effective_state(self.S(), a, self.S().current()[a]), "excluded", "before apply")
        self.assertNotIn(a, [c[0] for c in cc.eligible(self.S(), cc.now())])
        self.assertIn(a, run("due", "--store", self.store)[1])
        run("retire", b, "--store", self.store); run("apply", "--store", self.store)
        cur = self.S().current()
        self.assertEqual(cur[a]["state"], "excluded"); self.assertEqual(cur[b]["state"], "retired")
        self.assertGreater(cc.parse(cur[b]["delete_after"]), cc.now() + timedelta(days=364))
        rc, out = run("delete-record", a, "--store", self.store)
        self.assertIn("delete the case folder first", out)
        shutil.rmtree(Path(self.store) / "moxywolf-plugins" / a)
        run("delete-record", a, "--store", self.store); run("apply", "--store", self.store)
        line = self.S().current()[a]
        self.assertEqual(line["state"], "deleted"); self.assertFalse(cc.fully_removed(line))
        run("cleared", a, "--where", "drive_trash", "--store", self.store); run("apply", "--store", self.store)
        self.assertTrue(cc.fully_removed(self.S().current()[a]))


class Readiness(Base):
    def setUp(self):
        super().setUp(); self.init()
        self.ids = [self.full() for _ in range(20)]
        run("apply", "--store", self.store)
        cur = self.S().current()
        self.held = [c for c in self.ids if cur[c]["state"] == "active_held_out"]
        self.prop = [c for c in self.ids if cur[c]["state"] == "active_proposal"]

    def status(self):
        return run("status", "--project", "moxywolf-plugins", "--store", self.store)

    def test_quarter_rule_gives_15_5_ready(self):
        self.assertEqual((len(self.prop), len(self.held)), (15, 5))
        rc, out = self.status()
        self.assertEqual(rc, 0, out); self.assertIn("ready", out); self.assertIn("operational starting point", out)

    def test_14_5_not_ready(self):
        run("exclude", self.prop[0], "--store", self.store, "--reason", "t")
        rc, out = self.status(); self.assertEqual(rc, 3); self.assertIn("not ready: 14/15 proposal, 5/5 held-out", out)

    def test_15_4_not_ready(self):
        run("exclude", self.held[0], "--store", self.store, "--reason", "t")
        rc, out = self.status(); self.assertEqual(rc, 3); self.assertIn("not ready: 15/15 proposal, 4/5 held-out", out)

    def test_expired_doesnt_count(self):
        real = cc.now
        cc.now = lambda: real() + timedelta(days=400)
        try:
            rc, out = self.status()
        finally:
            cc.now = real
        self.assertEqual(rc, 3); self.assertIn("0/15 proposal, 5/5 held-out", out)


class Compaction(Base):
    def test_case_survives_its_memory_record(self):
        self.init()
        d = self.deliberation(); cid = self.full(d=d); run("apply", "--store", self.store)
        d.unlink()  # the council-memory record is gone; nothing reads it
        self.assertEqual(run("verify", "--store", self.store)[0], 0)
        self.assertIn(cid, [c[0] for c in cc.eligible(self.S(), cc.now())])


if __name__ == "__main__":
    unittest.main()
