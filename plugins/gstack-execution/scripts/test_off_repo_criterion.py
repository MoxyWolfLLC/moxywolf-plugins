#!/usr/bin/env python3
"""XE-025: a criterion about a place the reviewer can't see needs evidence it can. Stdlib, offline."""
import contextlib
import io
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import peer_review as pr  # noqa: E402

# XE-022 criterion 3, verbatim from review 20260925-075306-d939046-6xn07qgh (ledger M-012).
XE022_C3 = ("On the Release Owner's Mac, with `codex` installed and on `PATH`, `test_dispatch_collect.py` "
            "passes 5 of 5, and the round record for the unavailable case names no reviewer model.")
EVIDENCE = "docs/evidence/XE-022-macos-run.md"
HIDDEN = ".github/evidence/run.md"


def repo():
    d = Path(tempfile.mkdtemp())
    run = lambda *a: subprocess.run(["git", "-C", str(d), *a], check=True, capture_output=True)
    run("init", "-q"); run("config", "user.email", "t@t"); run("config", "user.name", "t")
    (d / "README.md").write_text("x\n"); run("add", "."); run("commit", "-qm", "base")
    base = subprocess.run(["git", "-C", str(d), "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
    (d / EVIDENCE).parent.mkdir(parents=True); (d / EVIDENCE).write_text("captured by script\n")
    (d / HIDDEN).parent.mkdir(parents=True); (d / HIDDEN).write_text("captured by script\n")
    run("add", "."); run("commit", "-qm", "evidence")
    head = subprocess.run(["git", "-C", str(d), "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
    return d, base, head


def open_review(criteria, override=False):
    d, base, head = repo()
    pk = {"outcome": "o", "acceptance_criteria": criteria,
          "repos": [{"path": str(d), "base": base, "head": head}], "changed_behavior": "b",
          "exclusions": [], "tests": {}, "release_owner": "dorianatmoxywolf"}
    f = d / "packet.json"; f.write_text(json.dumps(pk))
    pr.REVIEW_DIR = Path(tempfile.mkdtemp())   # read at import; set per test, never a session home
    a = SimpleNamespace(packet=str(f), builder="claude", max_rounds=3, timeout=900,
                        accept_narrow_packet=False, accept_off_repo_criterion=override)
    with contextlib.redirect_stdout(io.StringIO()):   # cmd_open prints the state it writes
        return pr.cmd_open(a)


def refused(criteria):
    try:
        open_review(criteria)
    except pr.ReviewError as e:
        return e
    return None


def test_the_m012_criterion_with_no_evidence_is_refused():
    e = refused([XE022_C3])
    assert e and e.outcome == "unevidenced_off_repo_criterion", e
    assert "Release Owner's Mac" in e.detail


def test_the_same_criterion_naming_existing_evidence_opens_and_records_it():
    st = open_review([XE022_C3 + f" Captured in `{EVIDENCE}`."])
    assert st["off_repo_evidence"] == [{"criterion": XE022_C3 + f" Captured in `{EVIDENCE}`.",
                                         "matched": "Release Owner's Mac", "evidence": EVIDENCE}]
    assert st["off_repo_overridden"] == []


def test_a_named_path_missing_at_the_head_is_refused():
    e = refused([XE022_C3 + " Captured in docs/evidence/XE-999-macos-run.md."])
    assert e and e.outcome == "unevidenced_off_repo_criterion", e


def test_a_directory_is_not_evidence():
    """Replay of review 20260925-091247: XE-023.3 named `docs/evidence/`, a directory, and passed."""
    e = refused([XE022_C3 + " Captured under `docs/evidence/`."])
    assert e and e.outcome == "unevidenced_off_repo_criterion", e


def test_a_hidden_repository_file_is_evidence():
    """Review F1: `.github/...` had its leading dot stripped and was never checked."""
    st = open_review([XE022_C3 + f" Captured in `{HIDDEN}`."])
    assert [x["evidence"] for x in st["off_repo_evidence"]] == [HIDDEN]


def test_an_absolute_or_escaping_path_is_not_evidence():
    """Review F1: `/docs/...` was read as the repository's `docs/...`. Quoted and bare, absolute,
    home-relative and escaping forms all name nothing inside the repository."""
    for ref in (f"`/{EVIDENCE}`", f"/{EVIDENCE}", f"`../{EVIDENCE}`", f"../{EVIDENCE}", f"~/{EVIDENCE}"):
        e = refused([XE022_C3 + f" Captured in {ref}."])
        assert e and e.outcome == "unevidenced_off_repo_criterion", ref


def test_a_criterion_with_no_off_repo_word_opens():
    st = open_review(["`scripts/run_all_tests.py` in CI reports a nonzero count, no failures; the state machine holds."])
    assert st["off_repo_evidence"] == [] and st["off_repo_overridden"] == []


def test_the_override_opens_and_records_itself():
    st = open_review([XE022_C3], override=True)
    assert st["off_repo_overridden"] == [XE022_C3] and st["off_repo_evidence"] == []


# XE-032: DG-001 criterion 9, verbatim. It names the plugin, not the vault.
DG001_C9 = ("`excalidraw-vault` moves 0.1.0 to 0.2.0 in `plugin.json` and its `marketplace.json` entry, and the "
            "top-level marketplace version moves (CI-002). Versions change by surgical text replace; the diff on "
            "both JSON files shows version lines only.")


def test_a_place_word_inside_a_name_is_not_the_place():
    for text in ("excalidraw-vault", "vault/x", "mac_os_x", "mac.py", "notes-locally-cached"):
        assert not pr.OFF_REPO.search(f"the plugin {text} changes"), text


def test_a_place_word_standing_alone_is_still_the_place():
    for text in ("the vault", "the vault.", "the vault's folder", "run locally, then", "on the Release Owner's Mac"):
        assert pr.OFF_REPO.search(f"{text} holds it"), text


def test_dg001_criterion_9_opens_without_the_override():
    assert refused([DG001_C9]) is None


if __name__ == "__main__":
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for fn in tests:
        fn(); print(f"ok  {fn.__name__}")
    print(f"\n{len(tests)} passed")
