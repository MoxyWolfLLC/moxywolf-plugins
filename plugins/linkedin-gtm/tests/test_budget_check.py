#!/usr/bin/env python3
"""budget_check.py: plan caps sit under the platform ceiling, and red buckets stop the day."""
import datetime as dt
import io
import json
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import batch_ledger as bl  # noqa: E402
import budget_check as bc  # noqa: E402

NOW = dt.datetime(2026, 11, 10, 17, 0, tzinfo=dt.timezone.utc)


def row(limit_type, daily, done=0, **kw):
    r = {"limit_type": limit_type, "daily_limit": daily, "done_today_count": done, "status": "active",
         "risk_level": "none", "hold_till": None, "linkedin_quota_hit_till": None, "delay_in_seconds": 120}
    r.update(kw)
    return r


ROWS = [row("send_connection_requests", 5, 1), row("comment_posts", 5), row("react_posts", 5),
        row("send_messages", 10), row("posting", 4), row("enrichment", 12, 2), row("self_account_sync", 1000, 10)]


class Compute(unittest.TestCase):
    def test_green_day(self):
        b = bc.compute(ROWS, {"ramp_start_date": "2026-11-10"}, now=NOW, today=NOW.date())
        self.assertEqual(b["status"], "green")
        self.assertEqual(b["phase"], "weeks_1_2")
        self.assertEqual(b["buckets"]["send_connection_requests"]["plan_left"], 4)
        self.assertEqual(b["buckets"]["posting"]["plan_cap"], 1)  # plan, not the ceiling of 4
        self.assertEqual(b["buckets"]["enrichment"]["plan_left"], 10)

    def test_plan_never_above_ceiling(self):
        b = bc.compute(ROWS, {"ramp_start_date": "2026-10-01"}, now=NOW, today=NOW.date())
        self.assertEqual(b["phase"], "week_3_plus")
        self.assertEqual(b["buckets"]["send_connection_requests"]["plan_cap"], 5)  # 20 planned, ceiling 5
        self.assertEqual(b["buckets"]["self_account_sync"]["plan_cap"], 1000)  # no target: ceiling

    def test_red_flags(self):
        rows = ROWS + [row("visit_profiles", 8, hold_till="2026-11-11T00:00:00Z"),
                       row("endorse_skills", 5, risk_level="elevated"),
                       row("send_inmails", 5, linkedin_quota_hit_till="2026-11-09T00:00:00Z")]  # past: fine
        b = bc.compute(rows, {}, now=NOW, today=NOW.date())
        self.assertEqual(b["status"], "red")
        self.assertEqual(b["red_outward"], ["endorse_skills", "visit_profiles"])
        self.assertEqual(b["buckets"]["visit_profiles"]["plan_left"], 0)
        self.assertFalse(b["buckets"]["send_inmails"]["red"])

    def test_extract_rows_formats(self):
        items = {"success": True, "items": [{"item": r} for r in ROWS]}
        raw = {"jsonrpc": "2.0", "id": 1, "result": {"content": [{"type": "text", "text": json.dumps(items)}]}}
        self.assertEqual(len(bc.extract_rows(raw)), len(ROWS))
        self.assertEqual(len(bc.extract_rows(items)), len(ROWS))
        self.assertEqual(len(bc.extract_rows(ROWS)), len(ROWS))
        with self.assertRaises(bc.BadInput):
            bc.extract_rows({"items": [{"foo": 1}]})


class BatchCheck(unittest.TestCase):
    def test_over_budget_batch(self):
        lg = bl.new_ledger("2026-11-10", "ln_ac_t", "Dorian Cougias")
        for i in range(5):
            bl.add_item(lg, "connect", {"public_identifier": f"p{i}", "note": "Saw your post on control mapping."},
                        "B", "signal")
        b = bc.compute(ROWS, {}, now=NOW, today=NOW.date())
        pending, over = bc.check_batch(b, lg)
        self.assertEqual(pending["send_connection_requests"], 5)
        self.assertEqual(over["send_connection_requests"]["cut"], 1)  # 1 already spent today


class Cli(unittest.TestCase):
    def test_cli_file_and_exit_codes(self):
        with tempfile.TemporaryDirectory() as d:
            f = Path(d) / "limits.json"
            f.write_text(json.dumps({"success": True, "items": [{"item": r} for r in ROWS]}))
            buf = io.StringIO()
            with redirect_stdout(buf):
                code = bc.main(["--limits", str(f), "--json"])
            self.assertEqual(code, 0)
            self.assertIn("buckets", json.loads(buf.getvalue()))
            f.write_text(json.dumps(ROWS + [row("comment_posts", 5, status="paused")]))
            with redirect_stdout(io.StringIO()):
                self.assertEqual(bc.main(["--limits", str(f)]), 3)

    def test_sample_smart_limits_from_repo_shape(self):
        sample = Path(__file__).resolve().parent / "fixtures" / "smart_limits_sample.json"
        rows = bc.extract_rows(json.loads(sample.read_text()))
        b = bc.compute(rows, {"ramp_start_date": "2026-11-10"}, now=NOW, today=NOW.date())
        self.assertIn("send_connection_requests", b["buckets"])


if __name__ == "__main__":
    unittest.main()
