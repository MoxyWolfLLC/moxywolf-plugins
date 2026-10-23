#!/usr/bin/env python3
"""EV-014: a ledger run the builder cites reaches the reviewer with its output, read by the dispatcher.
Stdlib, offline. Runs are made by running check_ledger.py as a subprocess, the way a builder runs it."""
import hashlib
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import check_ledger as cl  # noqa: E402
import peer_review as pr  # noqa: E402
from test_check_ledger import fixture, open_review  # noqa: E402

LEDGER = os.path.join(HERE, "check_ledger.py")


def run(d, root, code):
    """One ledger run of `python -c code`; returns (exit code, stdout, the run's ledger line)."""
    env = dict(os.environ, GSTACK_PEER_REVIEW_DIR=str(root))
    r = subprocess.run([sys.executable, LEDGER, "run", "--repo", str(d), "--", sys.executable, "-c", code],
                       cwd=str(d), env=env, capture_output=True, text=True)
    return r.returncode, r.stdout, cl.read(cl.ledger_path(d, "build/x", root))[-1]


def receipt_of(d, root, line):
    return cl.receipts_dir(cl.ledger_path(d, "build/x", root)) / f"{line['id']}.log"


def surface(d, base, head, root, run_ids):
    pr.REVIEW_DIR = root
    repos = [{"path": str(d), "base": base, "head": head}]
    return pr.build_surface(repos, Path(tempfile.mkdtemp()),
                            ledger_runs=[{"repo": str(d), "run_id": i} for i in run_ids])


def test_a_run_keeps_a_receipt_whose_hash_is_on_its_line():
    d, _, _, root = fixture()
    rc, out, line = run(d, root, "import sys; print('nice: 2309 elements'); print('warn', file=sys.stderr)")
    assert rc == 0 and out == "nice: 2309 elements\n", out   # still passed through to the console
    data = receipt_of(d, root, line).read_bytes()
    assert b"nice: 2309 elements" in data and b"warn" in data
    assert line["receipt"] == {"sha256": hashlib.sha256(data).hexdigest(), "bytes": len(data), "truncated": False}


def test_a_long_run_is_truncated_and_says_so():
    d, _, _, root = fixture()
    _, _, line = run(d, root, "print('a' * 50000); print('z' * 50000)")
    data = receipt_of(d, root, line).read_bytes()
    assert line["receipt"]["truncated"] is True and len(data) == line["receipt"]["bytes"] < 70000
    assert data.startswith(b"a" * 1000) and data.rstrip().endswith(b"z" * 1000) and b"bytes omitted" in data
    assert hashlib.sha256(data).hexdigest() == line["receipt"]["sha256"]


def test_a_failing_run_keeps_its_exit_code_and_its_receipt():
    d, _, _, root = fixture()
    rc, _, line = run(d, root, "import sys; print('boom'); sys.exit(4)")
    assert rc == 4 and line["exit_code"] == 4 and b"boom" in receipt_of(d, root, line).read_bytes()


def test_a_named_run_at_the_reviewed_head_is_on_the_surface_verified():
    d, base, head, root = fixture()
    _, _, line = run(d, root, "print('criterion 4 holds')")
    surf, stats = surface(d, base, head, root, [line["id"]])
    rec = json.loads((surf / "evidence" / f"ledger-{line['id']}.json").read_text())
    assert rec["read"] and rec["head_matches"] and rec["receipt_verified"] and rec["exit_code"] == 0, rec
    assert (surf / "evidence" / f"ledger-{line['id']}.log").read_text() == "criterion 4 holds\n"
    text = (surf / "SURFACE.md").read_text()
    assert f"ledger-{line['id']}.json`: run at the reviewed head, exit 0" in text and "sha256 verified" in text
    prov = json.loads((surf / pr.PROVENANCE_FILE).read_text())
    assert prov[f"evidence/ledger-{line['id']}.log"]["source"] == "ledger_receipt"
    assert stats["ledger_runs"][0]["receipt_verified"] is True


def test_a_changed_receipt_is_not_verified():
    d, base, head, root = fixture()
    _, _, line = run(d, root, "print('2309')")
    receipt_of(d, root, line).write_text("2310\n")
    surf, _ = surface(d, base, head, root, [line["id"]])
    rec = json.loads((surf / "evidence" / f"ledger-{line['id']}.json").read_text())
    assert rec["read"] and not rec["receipt_verified"] and "does not match" in rec["error"], rec
    assert not (surf / "evidence" / f"ledger-{line['id']}.log").exists()


def test_a_run_at_another_head_is_labelled():
    d, base, head, root = fixture()
    _, _, line = run(d, root, "print('x')")
    surf, _ = surface(d, base, base, root, [line["id"]])   # reviewed head is base; the run was at head
    rec = json.loads((surf / "evidence" / f"ledger-{line['id']}.json").read_text())
    assert rec["head_matches"] is False
    assert "NOT the reviewed head" in (surf / "SURFACE.md").read_text()


def test_a_receipt_with_a_secret_is_withheld():
    d, base, head, root = fixture()
    key = "sb_" + "secret_" + "A" * 30   # built at run time, so the command line carries no key
    _, _, line = run(d, root, "print('key=' + 'sb_' + 'secret_' + 'A' * 30)")
    surf, _ = surface(d, base, head, root, [line["id"]])
    rec = json.loads((surf / "evidence" / f"ledger-{line['id']}.json").read_text())
    assert rec["receipt_verified"] and "likely-secret" in rec["withheld"], rec
    assert not (surf / "evidence" / f"ledger-{line['id']}.log").exists()
    assert key not in (surf / "SURFACE.md").read_text() and key not in json.dumps(rec)


def test_a_command_line_with_a_secret_is_withheld():
    d, base, head, root = fixture()
    key = "sb_secret_" + "B" * 30
    _, _, line = run(d, root, f"k = '{key}'; print('ok')")
    surf, _ = surface(d, base, head, root, [line["id"]])
    rec = json.loads((surf / "evidence" / f"ledger-{line['id']}.json").read_text())
    assert "command withheld" in json.dumps(rec) and key not in json.dumps(rec), rec
    assert key not in (surf / "SURFACE.md").read_text()
    assert (surf / "evidence" / f"ledger-{line['id']}.log").read_text() == "ok\n"


def test_an_old_line_without_a_receipt_still_reads_and_says_so():
    d, base, head, root = fixture()
    _, _, line = run(d, root, "print('x')")
    p = cl.ledger_path(d, "build/x", root)
    old = {k: v for k, v in line.items() if k != "receipt"}
    p.write_text(json.dumps(old) + "\n")
    assert cl.read(p)[0]["id"] == line["id"]
    surf, _ = surface(d, base, head, root, [line["id"]])
    rec = json.loads((surf / "evidence" / f"ledger-{line['id']}.json").read_text())
    assert rec["read"] and not rec["receipt_verified"] and "no receipt" in rec["error"], rec


def test_open_refuses_a_run_id_not_on_the_ledger():
    d, base, head, root = fixture()
    run(d, root, "print('x')")
    try:
        open_review(d, base, head, root, ledger_runs=[{"repo": str(d), "run_id": "0123456789ab"}])
    except pr.ReviewError as e:
        assert e.outcome == "malformed_packet" and "0123456789ab" in e.detail, e.detail
    else:
        raise AssertionError("opened naming a run that is not on the ledger")


def test_open_accepts_a_run_id_on_the_ledger():
    d, base, head, root = fixture()
    _, _, line = run(d, root, "print('x')")
    st = open_review(d, base, head, root, ledger_runs=[{"repo": str(d), "run_id": line["id"]}])
    assert st["outcome"] == "opened"


def test_the_ci_log_net_catches_the_two_new_shapes():
    import ci_log_receipt as clr
    assert clr.LIKELY_SECRET.search("SUPABASE_SERVICE_ROLE_KEY " + "sb_secret_" + "x" * 24)
    assert clr.LIKELY_SECRET.search("Bearer eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.dozjgNryP4J3jVmNHl0w")
    assert not clr.LIKELY_SECRET.search("sb_publishable_" + "x" * 24 + " nice: 2309 elements, 5904 relationships")


if __name__ == "__main__":
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for fn in tests:
        fn(); print(f"ok  {fn.__name__}")
    print(f"\n{len(tests)} passed")
