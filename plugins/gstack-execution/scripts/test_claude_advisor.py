#!/usr/bin/env python3
"""ME-003: the claude reviewer runs with an advisor, says so in its record, and never quietly runs
without one it asked for.

Stdlib, offline. A fake `claude` on PATH writes its argv to a file and prints a CLI-shaped JSON
envelope, so run_reviewer builds and runs the real command line.
"""
import io
import json
import os
import stat
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import peer_review as pr  # noqa: E402

OUT = {"structured_output": {"verdict": "x"},
       "modelUsage": {"claude-opus-5": {"outputTokens": 900}, "claude-fable-5-2": {"outputTokens": 400}}}


def fake_claude(exit_code=0, stderr=""):
    d = Path(tempfile.mkdtemp(prefix="me003-"))
    argv = d / "argv.json"
    (d / "claude").write_text(
        "#!/usr/bin/env python3\nimport json, sys\n"
        f"open({str(argv)!r}, 'w').write(json.dumps(sys.argv[1:]))\n"
        f"sys.stderr.write({stderr!r})\nprint({json.dumps(json.dumps(OUT))})\nsys.exit({exit_code})\n")
    (d / "claude").chmod((d / "claude").stat().st_mode | stat.S_IEXEC)
    return d, argv


def run(env_extra, **fake):
    d, argv = fake_claude(**fake)
    keep = dict(os.environ)
    os.environ["PATH"] = f"{d}{os.pathsep}{keep.get('PATH', '')}"
    for v in ("GSTACK_CLAUDE_ADVISOR", *pr.ADVISOR_OFF_VARS, "GSTACK_PEER_REVIEW_FAKE_CMD"):
        os.environ.pop(v, None)
    os.environ.update(env_extra)
    try:
        try:
            pr.run_reviewer("claude", "review this", d, 30)
            err = None
        except pr.ReviewError as e:
            err = e
        return (json.loads(argv.read_text()) if argv.exists() else None), err, pr.LAST_REVIEWER_ADVISOR
    finally:
        os.environ.clear(); os.environ.update(keep)


def test_the_flag_is_on_by_default_and_the_advisor_is_seen():
    argv, err, adv = run({})
    assert err is None, err
    i = argv.index("--advisor")
    assert argv[i + 1] == "fable", argv
    assert adv["requested"] == "fable" and adv["seen"] is True and adv["disabled_by_env"] is None, adv


def test_an_advisor_that_out_writes_the_reviewer_is_not_recorded_as_the_reviewer():
    # live, 2026-11-11: Fable as advisor wrote more tokens than the Opus reviewer, and the reviewer was
    # recorded as claude-fable-5-1
    global OUT
    keep = OUT
    OUT = {"structured_output": {"verdict": "x"},
           "modelUsage": {"claude-opus-5": {"outputTokens": 300}, "claude-fable-5-1": {"outputTokens": 1800}}}
    try:
        d, argv = fake_claude()
        old = dict(pr.os.environ)
        pr.os.environ["PATH"] = f"{d}{pr.os.pathsep}{old.get('PATH', '')}"
        for v in ("GSTACK_CLAUDE_ADVISOR", *pr.ADVISOR_OFF_VARS, "GSTACK_PEER_REVIEW_FAKE_CMD"):
            pr.os.environ.pop(v, None)
        try:
            _, model = pr.run_reviewer("claude", "review this", d, 30)
        finally:
            pr.os.environ.clear(); pr.os.environ.update(old)
        assert model == "claude-opus-5", model
        assert pr.LAST_REVIEWER_ADVISOR["seen"] is True, pr.LAST_REVIEWER_ADVISOR
    finally:
        OUT = keep


def test_off_drops_the_flag_and_wins_over_a_disabling_variable():
    argv, err, adv = run({"GSTACK_CLAUDE_ADVISOR": "off", "DISABLE_TELEMETRY": "1"})
    assert err is None and "--advisor" not in argv, (err, argv)
    assert adv["requested"] == "off" and adv["disabled_by_env"] is None, adv


def test_a_disabling_variable_with_an_advisor_requested_is_review_unavailable():
    for var in pr.ADVISOR_OFF_VARS:
        argv, err, adv = run({var: "1"})
        assert argv is None, "the CLI must not run"
        assert err and err.outcome == "review_unavailable" and var in str(err), err
        assert adv["disabled_by_env"] == var, adv


def test_a_launch_failure_is_review_unavailable_and_names_the_advisor():
    argv, err, adv = run({"GSTACK_CLAUDE_ADVISOR": "fable"}, exit_code=1,
                         stderr="Error: Fable as the advisor needs the usage-credits consent; run /model fable")
    assert err and err.outcome == "review_unavailable" and "advisor fable requested" in str(err), err


def test_seen_is_null_with_a_reason_when_families_match():
    seen, why = pr.advisor_seen(json.dumps(OUT), "opus", "claude-opus-5")
    assert seen is None and "share a model family" in why, why
    seen, why = pr.advisor_seen("not json", "fable", "claude-opus-5")
    assert seen is None and why, why


def _loop(run):
    """test_unknowns' cmd_open / cmd_round / cmd_release harness, with claude as the reviewer."""
    import test_unknowns as tu
    L = tu._Loop([])
    pr.choose_reviewer = lambda builder, forced=None, require_installed=True: ("claude", False)
    pr.run_reviewer = run
    with tu.contextlib.redirect_stdout(io.StringIO()):
        L.st = pr.cmd_open(L.ns(builder="codex", packet=str(L.pfile), max_rounds=3, timeout=30)); L.rid = L.st["review_id"]
    return L, tu


def test_a_refused_advisor_is_in_the_saved_round_record():   # review F1
    for var in pr.ADVISOR_OFF_VARS:
        def refuse(tool, prompt, root, timeout, schema=None, named=()):
            pr.LAST_REVIEWER_ADVISOR = None
            return pr.claude_advisor({var: "1"})
        os.environ.pop("GSTACK_CLAUDE_ADVISOR", None)
        L, _ = _loop(refuse)
        try:
            assert L.round() == "review_unavailable"
            rec = L.record(1)
            assert rec["reviewer_advisor"]["disabled_by_env"] == var and rec["reviewer_advisor"]["requested"] == "fable", rec
        finally:
            L.close()


def test_the_handoff_says_an_unverified_advisor_was_unverified():   # review F2
    def ok(tool, prompt, root, timeout, schema=None, named=()):
        pr.LAST_REVIEWER_ADVISOR = {"requested": "fable", "seen": None, "seen_reason": "claude reported no modelUsage",
                                    "disabled_by_env": None}
        return L_reply, "claude-opus-5"
    import test_unknowns as tu
    global L_reply
    L_reply = json.dumps({"verdict": "no_blocking_findings", "findings": [], "blocker_resolutions": [], "unknowns": [],
                          "acceptance": [{"criterion": "f(1) == 2", "met": True, "evidence": "a.py:2"},
                                         {"criterion": "f(None) is handled", "met": True, "evidence": "a.py:2"}]})
    L, _ = _loop(ok)
    err = io.StringIO()
    try:
        assert L.round() == "no_blocking_findings", L.record(1).get("error")
        with tu.contextlib.redirect_stdout(io.StringIO()), tu.contextlib.redirect_stderr(err):
            try:
                pr.cmd_release(L.ns(review_id=L.rid, target="main", coverage_exception="release it, fixture-human",
                                    observation=["read a.py :: git -C " + str(L.d) + " show HEAD:a.py"]))
            except pr.ReviewError as e:
                assert e.outcome == "awaiting_human_release", e
        rel = pr.load(pr.REVIEW_DIR / L.rid, "release.json")
        assert "UNVERIFIED: claude reported no modelUsage" in rel["advisor_note"], rel.get("advisor_note")
        assert "UNVERIFIED" in err.getvalue()
        assert pr.advisor_note({"requested": "off"}).startswith("advisor: off") and pr.advisor_note(None) is None
        assert "ran" in pr.advisor_note({"requested": "fable", "seen": True})
    finally:
        L.close()


if __name__ == "__main__":
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for fn in tests:
        fn(); print(f"ok  {fn.__name__}")
    print(f"\n{len(tests)} passed")
