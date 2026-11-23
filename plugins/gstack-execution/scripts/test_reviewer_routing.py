#!/usr/bin/env python3
"""XE-005: a reviewer is independent by what differs, not by its name. Stdlib only."""
import contextlib, os, shutil, subprocess, sys, tempfile
from pathlib import Path
from unittest import mock

import peer_review as pr


@contextlib.contextmanager
def _on_path(*tools):
    """Pretend exactly these CLIs are installed, and no API reviewer's credential resolves (XE-047)."""
    with mock.patch.object(pr.shutil, "which", lambda t: f"/usr/bin/{t}" if t in tools else None), \
            mock.patch.dict(os.environ):
        os.environ.pop("GSTACK_OPENROUTER_ENV", None)
        yield


def test_a_claude_builder_is_never_reviewed_by_a_claude_family_tool():
    """The whole point. Cursor-style harness swaps must not count as independence."""
    assert "claude" not in pr.reviewer_candidates("claude")
    assert pr.family("claude") == "claude"
    for t in pr.reviewer_candidates("claude"):
        assert pr.REVIEWERS[t]["family"] != "claude", t


def test_forcing_a_same_family_reviewer_is_refused_not_accepted():
    try:
        pr.choose_reviewer("claude", forced="claude")
        raise AssertionError("a same-family reviewer must be refused")
    except pr.ReviewError as e:
        assert e.outcome == "reviewer_not_independent", e.outcome
        assert "harness swap" in str(e)


def test_fallback_is_permitted_but_recorded_as_one():
    """An unrecorded fallback is a silent downgrade."""
    with _on_path("codex", "gemini"):
        tool, fb = pr.choose_reviewer("claude")
        assert (tool, fb) == ("codex", False), (tool, fb)
    with _on_path("gemini"):                      # preferred reviewer absent
        tool, fb = pr.choose_reviewer("claude")
        assert (tool, fb) == ("gemini", True), (tool, fb)


def test_no_independent_reviewer_is_unavailable_not_a_pass():
    with _on_path():                              # nothing installed
        try:
            pr.choose_reviewer("claude")
            raise AssertionError("must not silently proceed")
        except pr.ReviewError as e:
            assert e.outcome == "review_unavailable" and "no independent reviewer" in str(e)


def test_every_reviewer_declares_a_family_and_a_floor_that_rejects_its_predecessor():
    for tool, cfg in pr.REVIEWERS.items():
        assert cfg["family"] and cfg["floor"] and cfg["model"], tool
        assert pr.model_ok(tool, cfg["model"]), f"{tool} default model is below its own floor"
    assert not pr.model_ok("gemini", "gemini-2.5-pro")
    assert pr.model_ok("gemini", "gemini-3-pro")
    assert not pr.model_ok("codex", "gpt-5")
    assert not pr.model_ok("claude", "claude-sonnet-5")


def test_truncated_output_is_distinct_from_malformed_output():
    """Different causes, different fixes. Collapsing them makes a headroom problem look like a
    broken reviewer -- the failure mode Gemini already showed this team in the Council run."""
    cut = '{"verdict": "no_blocking_findings", "acceptance": [{"criterion": "a", "met": true'
    assert pr._looks_truncated(cut)
    assert pr._no_json_outcome("no json here at all")[0] == "malformed_output"
    assert pr._no_json_outcome(cut)[0] == "output_truncated"
    # a complete but wrong object is malformed, never truncated
    assert not pr._looks_truncated('{"verdict": "nonsense"}')
    assert not pr._looks_truncated("")


def test_open_records_which_independence_was_obtained():
    pkt = {"outcome": "o", "acceptance_criteria": ["c"], "changed_behavior": "b",
           "exclusions": [], "tests": {"commands": [], "results": "r", "environment": "e"},
           "release_owner": "dorianatmoxywolf", "prior_findings": [],
           "data_use": {"owner": "dorianatmoxywolf", "classification": "internal",
                        "allow_repository": True, "allow_history": True,
                        "allowed_tools": ["claude", "codex", "gemini"], "allowed_commands": [],
                        "output_roots": ["/tmp"]}}
    with _on_path("gemini"):
        tool, fb = pr.choose_reviewer("claude")
    # the record must carry family and fallback, not only the tool name
    assert pr.family(tool) == "gemini" and fb is True
    assert pr.family("codex") == "gpt" != pr.family("claude")


def test_validate_reports_truncation_through_the_real_entry_point():
    """_looks_truncated passing in isolation is not the check that matters. This exercises
    validate(), where the first version referenced an undefined name and would have raised
    NameError instead of any outcome at all."""
    pkt = {"acceptance_criteria": ["c"]}
    cases = [('{"verdict":"no_blocking_findings","acceptance":[{"criterion":"c","met":true',
              "output_truncated"),
             ("the model declined to answer", "malformed_output"),
             ('{"verdict":"nope"}', "malformed_output"),
             # a reviewer that returned NOTHING did not return something wrong
             ("", "empty_output"),
             ("   \n  ", "empty_output")]
    for body, want in cases:
        try:
            pr.validate(body, pkt)
            raise AssertionError(f"{body[:30]!r} should have raised")
        except pr.ReviewError as e:
            assert e.outcome == want, f"{body[:30]!r} -> {e.outcome}, wanted {want}"


def test_no_reviewer_holds_with_an_openrouter_credential_set():
    """XE-047: the review-host env files set GSTACK_OPENROUTER_ENV, and an api reviewer counts as
    installed once its key resolves. Pretending nothing is installed must hide that too."""
    with tempfile.TemporaryDirectory() as d, mock.patch.dict(os.environ):
        key = Path(d) / "openrouter.env"
        key.write_text("OPENROUTER_API_KEY=sk-or-test\n")
        os.environ["GSTACK_OPENROUTER_ENV"] = str(key)
        with _on_path():
            try:
                pr.choose_reviewer("claude")
                raise AssertionError("must not find a reviewer with nothing installed")
            except pr.ReviewError as e:
                assert e.outcome == "review_unavailable", e.outcome
        env = {**os.environ, "GSTACK_PEER_REVIEW_DIR": str(Path(d) / "reviews")}
        out = subprocess.run([sys.executable, str(Path(pr.__file__)), "--selftest"],
                             capture_output=True, text=True, env=env, timeout=600)
        assert out.returncode == 0, out.stdout[-800:] + out.stderr[-800:]


if __name__ == "__main__":
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for t in tests:
        t(); print(f"ok  {t.__name__}")
    print(f"\n{len(tests)} passed")
