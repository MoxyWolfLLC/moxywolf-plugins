#!/usr/bin/env python3
"""batch_ledger.py: one batch a day, a named Release Owner, and nothing executable without a decision."""
import datetime as dt
import io
import json
import os
import sys
import tempfile
import unittest
from contextlib import redirect_stdout, redirect_stderr
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import batch_ledger as bl  # noqa: E402

SID = "ln_ac_test"
OWNER = "Dorian Cougias"
T0 = dt.datetime(2026, 11, 10, 18, 15, tzinfo=dt.timezone.utc)
GOOD_COMMENT = ("The crosswalk problem is rarely the mapping itself. It is keeping the mapping current "
                "when the source control changes and nobody owns the diff. Who owns that on your team?")


def ledger():
    return bl.new_ledger("2026-11-10", SID, OWNER, now=T0)


class AddItem(unittest.TestCase):
    def test_comment_gets_account_and_client_reference(self):
        lg = ledger()
        it = bl.add_item(lg, "comment", {"entity_urn": "urn:li:activity:1", "text": GOOD_COMMENT}, "C",
                         "STIG post, 40 comments, on fingerprint")
        self.assertEqual(it["id"], "20261110-001")
        self.assertEqual(it["args"]["linkedin_account_sid"], SID)
        self.assertEqual(it["args"]["client_reference"], "lgtm-20261110-001")
        self.assertEqual(it["tool"], "create_linkedin_comment")
        self.assertEqual(it["bucket"], "comment_posts")
        self.assertEqual(it["status"], "drafted")

    def test_lane_a_outreach_refused_while_held(self):
        lg = ledger()
        with self.assertRaises(bl.LedgerError):
            bl.add_item(lg, "connect", {"public_identifier": "jane", "note": "Liked your post on STIGs."},
                        "A", "partner")
        with self.assertRaises(bl.LedgerError):
            bl.add_item(lg, "dm", {"public_identifier": "jane", "text": "Hi Jane"}, "A", "partner")
        # engagement is fine in Lane A
        bl.add_item(lg, "reaction", {"entity_urn": "urn:li:activity:2", "reaction_type": "like"}, "A", "partner post")
        # released campaign allows outreach
        cfg = {"lanes": {"A": {"mode": "full-outreach"}}}
        bl.add_item(lg, "connect", {"public_identifier": "jane", "note": "Liked your post on STIGs."},
                    "A", "partner", config=cfg)

    def test_em_dash_and_long_note_refused(self):
        lg = ledger()
        with self.assertRaises(bl.LedgerError):
            bl.add_item(lg, "comment", {"entity_urn": "u", "text": "Good point \u2014 agreed " * 10}, "C", "r")
        with self.assertRaises(bl.LedgerError):
            bl.add_item(lg, "connect", {"public_identifier": "x", "note": "a" * 201}, "B", "r")

    def test_unknown_param_and_other_account_refused(self):
        lg = ledger()
        with self.assertRaises(bl.LedgerError):
            bl.add_item(lg, "reaction", {"entity_urn": "u", "reaction_type": "like", "bogus": 1}, "C", "r")
        with self.assertRaises(bl.LedgerError):
            bl.add_item(lg, "reaction", {"entity_urn": "u", "reaction_type": "like",
                                         "linkedin_account_sid": "ln_ac_other"}, "C", "r")

    def test_suppression(self):
        with tempfile.TemporaryDirectory() as d:
            sup = Path(d) / "sup.txt"
            sup.write_text("# no\nhttps://www.linkedin.com/in/StopMe/\n")
            lg = ledger()
            with self.assertRaises(bl.LedgerError):
                bl.add_item(lg, "connect", {"public_identifier": "stopme", "note": "hello there"}, "B", "r",
                            config={"suppression_file": str(sup)})

    def test_reaction_type_enum(self):
        with self.assertRaises(bl.LedgerError):
            bl.add_item(ledger(), "reaction", {"entity_urn": "u", "reaction_type": "LIKE"}, "C", "r")

    def test_missing_reason_refused(self):
        with self.assertRaises(bl.LedgerError):
            bl.add_item(ledger(), "reaction", {"entity_urn": "u", "reaction_type": "like"}, "C", "  ")


class Decide(unittest.TestCase):
    def setUp(self):
        self.lg = ledger()
        bl.add_item(self.lg, "comment", {"entity_urn": "urn:li:activity:1", "text": GOOD_COMMENT}, "C", "r1")
        bl.add_item(self.lg, "reaction", {"entity_urn": "urn:li:activity:1", "reaction_type": "like"}, "C", "r2")

    def test_must_present_first(self):
        with self.assertRaises(bl.LedgerError):
            bl.decide(self.lg, ["20261110-001"], "approve", OWNER, "DC")

    def test_only_release_owner(self):
        bl.present(self.lg, now=T0)
        for who in ("Amos", "me", "", "Someone Else"):
            with self.assertRaises(bl.LedgerError):
                bl.decide(self.lg, ["20261110-001"], "approve", who, "DC")

    def test_approve_edit_strike(self):
        bl.present(self.lg, now=T0)
        later = T0 + dt.timedelta(seconds=95)
        new = GOOD_COMMENT.replace("Who owns that on your team?", "Curious who owns that diff for you.")
        bl.decide(self.lg, ["20261110-001"], "edit", OWNER, "dc", now=later, new_text=new)
        bl.decide(self.lg, ["20261110-002"], "strike", OWNER, "DC", now=later)
        a, b = self.lg["items"]
        self.assertEqual(a["status"], "edited")
        self.assertEqual(a["args"]["text"], new)
        self.assertEqual(a["decision"]["original_text"], GOOD_COMMENT)
        self.assertEqual(a["decision"]["response_seconds"], 95)
        self.assertEqual(a["decision"]["initials"], "DC")
        self.assertEqual(b["status"], "struck")
        self.assertIsNone(b["approved_args_hash"])

    def test_edit_refuses_em_dash(self):
        bl.present(self.lg, now=T0)
        with self.assertRaises(bl.LedgerError):
            bl.decide(self.lg, ["20261110-001"], "edit", OWNER, "DC", new_text="x \u2014 y " * 20)


class VerifyAndRecord(unittest.TestCase):
    def setUp(self):
        os.environ["LINKEDIN_GTM_TODAY"] = "2026-11-10"
        self.lg = ledger()
        bl.add_item(self.lg, "comment", {"entity_urn": "urn:li:activity:1", "text": GOOD_COMMENT}, "C", "r1")
        bl.add_item(self.lg, "comment", {"entity_urn": "urn:li:activity:2", "text": GOOD_COMMENT}, "C", "r2")
        bl.add_item(self.lg, "reaction", {"entity_urn": "urn:li:activity:3", "reaction_type": "like"}, "C", "r3")
        bl.present(self.lg, now=T0)

    def tearDown(self):
        os.environ.pop("LINKEDIN_GTM_TODAY", None)

    def test_drafted_refused(self):
        with self.assertRaises(bl.LedgerError):
            bl.verify_for_execution(self.lg, "20261110-001")

    def test_tamper_after_approval_refused(self):
        bl.decide(self.lg, ["20261110-001"], "approve", OWNER, "DC")
        bl.verify_for_execution(self.lg, "20261110-001")
        self.lg["items"][0]["args"]["text"] += " Extra."
        with self.assertRaises(bl.LedgerError):
            bl.verify_for_execution(self.lg, "20261110-001")

    def test_other_day_refused(self):
        bl.decide(self.lg, ["20261110-001"], "approve", OWNER, "DC")
        os.environ["LINKEDIN_GTM_TODAY"] = "2026-11-11"
        with self.assertRaises(bl.LedgerError):
            bl.verify_for_execution(self.lg, "20261110-001")

    def test_rate_limit_stops_bucket_not_others(self):
        bl.decide(self.lg, ["20261110-001", "20261110-002", "20261110-003"], "approve", OWNER, "DC")
        bl.record_execution(self.lg, "20261110-001", "rate_limited", retry_after=3600)
        with self.assertRaises(bl.LedgerError):
            bl.verify_for_execution(self.lg, "20261110-002")
        bl.verify_for_execution(self.lg, "20261110-003")  # react_posts still open

    def test_checkpoint_stops_everything(self):
        bl.decide(self.lg, ["20261110-001", "20261110-003"], "approve", OWNER, "DC")
        bl.record_execution(self.lg, "20261110-001", "checkpoint")
        with self.assertRaises(bl.LedgerError):
            bl.verify_for_execution(self.lg, "20261110-003")

    def test_executed_cannot_rerun(self):
        bl.decide(self.lg, ["20261110-001"], "approve", OWNER, "DC")
        bl.record_execution(self.lg, "20261110-001", "executed")
        with self.assertRaises(bl.LedgerError):
            bl.verify_for_execution(self.lg, "20261110-001")
        with self.assertRaises(bl.LedgerError):
            bl.decide(self.lg, ["20261110-001"], "approve", OWNER, "DC")

    def test_drop_only_before_present(self):
        lg = ledger()
        bl.add_item(lg, "reaction", {"entity_urn": "a", "reaction_type": "like"}, "C", "r")
        bl.add_item(lg, "reaction", {"entity_urn": "b", "reaction_type": "like"}, "C", "r")
        bl.drop(lg, ["20261110-001"], "over budget")
        self.assertNotIn("**001.", bl.render(lg))
        it = bl.add_item(lg, "reaction", {"entity_urn": "c", "reaction_type": "like"}, "C", "r")
        self.assertEqual(it["id"], "20261110-003")  # ids stay stable
        bl.present(lg, now=T0)
        with self.assertRaises(bl.LedgerError):
            bl.drop(lg, ["20261110-002"], "late")
        with self.assertRaises(bl.LedgerError):
            bl.verify_for_execution(lg, "20261110-001")

    def test_queue_order_engagement_first(self):
        bl.decide(self.lg, ["20261110-001", "20261110-002", "20261110-003"], "approve", OWNER, "DC")
        kinds = [it["kind"] for it in bl.queue(self.lg)]
        self.assertEqual(kinds, ["reaction", "comment", "comment"])


class StatsAndOutputs(unittest.TestCase):
    def test_rubber_stamp_and_too_fast_flags(self):
        lgs = []
        for day in range(6):
            lg = bl.new_ledger(f"2026-11-1{day}", SID, OWNER, now=T0)
            bl.add_item(lg, "reaction", {"entity_urn": f"u{day}", "reaction_type": "like"}, "C", "r")
            bl.present(lg, now=T0)
            bl.decide(lg, [lg["items"][0]["id"]], "approve", OWNER, "DC", now=T0 + dt.timedelta(seconds=5))
            lgs.append(lg)
        s = bl.stats(lgs)
        self.assertTrue(any("RUBBER-STAMP" in f for f in s["flags"]), s)
        self.assertTrue(any("TOO-FAST" in f for f in s["flags"]), s)

    def test_render_has_every_item_and_no_em_dash(self):
        lg = ledger()
        bl.add_item(lg, "comment", {"entity_urn": "urn:li:activity:1", "text": GOOD_COMMENT}, "C", "r1",
                    target={"name": "Jane Roe", "url": "https://www.linkedin.com/feed/update/urn:li:activity:1/"})
        bl.add_item(lg, "accept", {"sid": "ln_ci_1"}, "D", "inbound invite, GRC lead")
        out = bl.render(lg)
        self.assertIn("**001. comment**", out)
        self.assertIn("**002. accept**", out)
        self.assertIn("Jane Roe", out)
        self.assertNotIn("\u2014", out)

    def test_gate_log_commands_and_pending_without_dir(self):
        os.environ["LINKEDIN_GTM_TODAY"] = "2026-11-10"
        try:
            lg = ledger()
            bl.add_item(lg, "reaction", {"entity_urn": "u", "reaction_type": "like"}, "C", "r")
            bl.present(lg, now=T0)
            bl.decide(lg, ["20261110-001"], "approve", OWNER, "DC")
            cmds = bl.gate_log_commands(lg, "/nonexistent/_gate-log")
            self.assertEqual(len(cmds), 1)
            cmd = cmds[0][1]
            self.assertIn("--approver", cmd)
            self.assertIn(OWNER, cmd)
            self.assertIn("signed", cmd)
            self.assertIn("linkedin-gtm:li-approval-batch", " ".join(cmd))
            res = bl.run_gate_log(lg, "/nonexistent/_gate-log")
            self.assertTrue(all("pending" in s for _, s in res))
        finally:
            os.environ.pop("LINKEDIN_GTM_TODAY", None)

    def test_crm_export(self):
        lg = ledger()
        bl.add_item(lg, "reaction", {"entity_urn": "u", "reaction_type": "like"}, "C", "r",
                    target={"name": "Jane Roe", "identifier": "janeroe"})
        self.assertEqual(bl.crm_export(lg), [])  # drafts are not touches
        bl.present(lg, now=T0)
        bl.decide(lg, ["20261110-001"], "approve", OWNER, "DC")
        bl.record_execution(lg, "20261110-001", "executed")
        rows = bl.crm_export(lg)
        self.assertEqual(rows[0]["person"]["identifier"], "janeroe")
        self.assertEqual(rows[0]["approved_by"], OWNER)
        self.assertEqual(rows[0]["channel"], "linkedin")


class Cli(unittest.TestCase):
    def test_new_add_present_decide_roundtrip(self):
        with tempfile.TemporaryDirectory() as d:
            cfg = Path(d) / "c.json"
            cfg.write_text(json.dumps({"account_sid": SID, "release_owner": OWNER,
                                       "timezone": "America/Los_Angeles"}))
            buf = io.StringIO()
            with redirect_stdout(buf):
                self.assertEqual(bl.main(["new", "--ledger-dir", d, "--date", "2026-11-10", "--config", str(cfg)]), 0)
            path = buf.getvalue().strip()
            with redirect_stdout(io.StringIO()):
                self.assertEqual(bl.main(["add", "--ledger", path, "--kind", "reaction", "--lane", "C",
                                          "--args", '{"entity_urn": "u", "reaction_type": "like"}',
                                          "--reason", "on fingerprint"]), 0)
            with redirect_stderr(io.StringIO()):
                self.assertEqual(bl.main(["decide", "--ledger", path, "--items", "1", "--decision", "approve",
                                          "--approver", OWNER, "--initials", "DC"]), 2)  # not presented
            with redirect_stdout(io.StringIO()):
                self.assertEqual(bl.main(["present", "--ledger", path]), 0)
                self.assertEqual(bl.main(["decide", "--ledger", path, "--items", "1", "--decision", "approve",
                                          "--approver", OWNER, "--initials", "DC"]), 0)
            self.assertEqual(bl.load(path)["items"][0]["status"], "approved")
            with redirect_stderr(io.StringIO()):
                self.assertEqual(bl.main(["new", "--ledger-dir", d, "--date", "2026-11-10",
                                          "--config", str(cfg)]), 2)  # one batch a day



PAGES_CFG = {"long_form": {"pages": {
    "STIGViewer": {"organization_id": "100890591"},
    "FrontierFounder": {"organization_id": "110215000"},
    "MoxyWolf LLC": {"organization_id": "108120951"}}}}
TEASER = "The full breakdown is in the comments. One question for you: who owns the diff?"


class PagePosts(unittest.TestCase):
    def test_page_post_needs_a_configured_page(self):
        with self.assertRaises(bl.LedgerError):
            bl.add_item(ledger(), "post", {"text": TEASER, "author_organization_id": "999"}, "OWN", "teaser",
                        target={"page": "STIGViewer", "page_chosen_by": OWNER}, config=PAGES_CFG)

    def test_page_post_needs_dorians_choice_for_this_piece(self):
        with self.assertRaises(bl.LedgerError):
            bl.add_item(ledger(), "post", {"text": TEASER, "author_organization_id": "100890591"}, "OWN",
                        "teaser", target={"page": "STIGViewer"}, config=PAGES_CFG)
        with self.assertRaises(bl.LedgerError):
            bl.add_item(ledger(), "post", {"text": TEASER, "author_organization_id": "100890591"}, "OWN",
                        "teaser", target={"page": "STIGViewer", "page_chosen_by": "Amos"}, config=PAGES_CFG)

    def test_page_name_must_match_the_id(self):
        with self.assertRaises(bl.LedgerError):
            bl.add_item(ledger(), "post", {"text": TEASER, "author_organization_id": "100890591"}, "OWN",
                        "teaser", target={"page": "FrontierFounder", "page_chosen_by": OWNER}, config=PAGES_CFG)

    def test_chosen_page_post_is_drafted_and_rendered(self):
        lg = ledger()
        bl.add_item(lg, "post", {"text": TEASER, "author_organization_id": "100890591"}, "OWN", "teaser",
                    target={"page": "STIGViewer", "page_chosen_by": OWNER}, config=PAGES_CFG)
        self.assertIn("Posts as page: STIGViewer (chosen by Dorian Cougias)", bl.render(lg))

if __name__ == "__main__":
    unittest.main()
