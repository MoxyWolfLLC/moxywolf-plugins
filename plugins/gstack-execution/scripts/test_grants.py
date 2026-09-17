#!/usr/bin/env python3
"""XE-002: a grant binds to a scope and re-resolves. Stdlib only; run directly."""
import tempfile
from pathlib import Path

from governance import ONE_SHOT_ONLY, data_permission, grant, resolve


def ledger():
    return Path(tempfile.mkdtemp()) / "grants.jsonl"


def test_pattern_covers_what_prose_would_have_relitigated():
    """The audited session asked four times to bypass review, once per PR, because each
    approval was a sentence about one PR. A pattern grant answers all four."""
    L = ledger()
    grant(L, "vcs.push", "MoxyWolfLLC/*", granted_by="dorian")
    for repo in ("MoxyWolfLLC/crm", "MoxyWolfLLC/stigviewer", "MoxyWolfLLC/oc-website"):
        assert resolve(L, "vcs.push", repo), f"{repo} should be covered by the pattern"
    assert resolve(L, "vcs.push", "SomeoneElse/crm") is None, "the pattern must not overreach"


def test_class_is_exact_even_when_resource_matches():
    L = ledger()
    grant(L, "vcs.push", "MoxyWolfLLC/*", granted_by="dorian")
    assert resolve(L, "review.send_code", "MoxyWolfLLC/crm") is None, \
        "a grant for one class must not answer for another"


def test_excludes_win_over_the_pattern():
    L = ledger()
    grant(L, "review.send_code", "MoxyWolfLLC/*", granted_by="dorian", excludes=["*.env", "*/secrets/*"])
    assert resolve(L, "review.send_code", "MoxyWolfLLC/crm")
    assert resolve(L, "review.send_code", "MoxyWolfLLC/crm/secrets/prod") is None
    assert resolve(L, "review.send_code", "hosted.env") is None


def test_consequential_classes_cannot_be_granted_in_advance():
    """The point of the ledger is to stop re-asking about routine work, not to pre-authorize
    a merge or a real send. No wording, and no scope, buys those in advance."""
    L = ledger()
    for klass in sorted(ONE_SHOT_ONLY):
        for scope in ("project", "session"):
            try:
                grant(L, klass, "*", granted_by="dorian", scope=scope, session="s1")
                raise AssertionError(f"{klass} must not be grantable at scope {scope}")
            except ValueError as e:
                assert "one-shot by construction" in str(e)
        g = grant(L, klass, "MoxyWolfLLC/crm#23", granted_by="dorian", scope="once")
        assert resolve(L, klass, "MoxyWolfLLC/crm#23"), "an unspent once-grant covers its own act"
        assert resolve(L, klass, "MoxyWolfLLC/crm#23", consume=[g["id"]]) is None, \
            "a spent once-grant covers nothing"
        assert resolve(L, klass, "MoxyWolfLLC/crm#24") is None, \
            "a once-grant is bound to its own resource"


def test_session_scope_does_not_leak_between_sessions():
    L = ledger()
    grant(L, "secret.read", "vault/*", granted_by="dorian", scope="session", session="s1")
    assert resolve(L, "secret.read", "vault/github-pat.env", session="s1")
    assert resolve(L, "secret.read", "vault/github-pat.env", session="s2") is None
    assert resolve(L, "secret.read", "vault/github-pat.env") is None


def test_a_grant_records_its_human_and_refuses_an_unknown_class():
    L = ledger()
    try:
        grant(L, "vcs.push", "x/*", granted_by="")
        raise AssertionError("a grant without a granting human must be refused")
    except ValueError as e:
        assert "records the human" in str(e)
    try:
        grant(L, "vibes.deploy", "x/*", granted_by="dorian")
        raise AssertionError("classes are a closed vocabulary")
    except ValueError as e:
        assert "unknown action class" in str(e)
    row = grant(L, "vcs.push", "x/*", granted_by="dorian")
    assert row["granted_by"] == "dorian" and row["id"] and row["granted_at"]


def test_data_permission_still_refuses_without_a_grant():
    """The ledger widens what a packet covers. It never removes the refusal."""
    packet = {"owner": "dorian", "data_use": {"owner": "dorian", "classification": "internal",
              "allow_repository": True, "allow_history": True, "allowed_tools": ["codex"]}}
    data_permission(packet, tool="codex")
    for kwargs in ({}, {"ledger": ledger()}):
        try:
            data_permission(packet, tool="claude-code", **kwargs)
            raise AssertionError("an ungranted destination must still be refused")
        except ValueError as e:
            assert "tool destination denied" in str(e)
    L = ledger()
    grant(L, "review.send_code", "claude-code", granted_by="dorian")
    data_permission(packet, tool="claude-code", ledger=L)  # now covered, no re-prompt


def test_data_permission_owner_and_repository_checks_are_untouched():
    L = ledger()
    grant(L, "review.send_code", "*", granted_by="dorian")
    for bad in ({"owner": "someone-else", "classification": "internal", "allow_repository": True,
                 "allow_history": True, "allowed_tools": []},
                {"owner": "dorian", "classification": "", "allow_repository": True,
                 "allow_history": True, "allowed_tools": []},
                {"owner": "dorian", "classification": "internal", "allow_repository": False,
                 "allow_history": True, "allowed_tools": []}):
        try:
            data_permission({"owner": "dorian", "data_use": bad}, tool="claude-code", ledger=L)
            raise AssertionError("a wildcard grant must not bypass the owner/repository checks")
        except ValueError as e:
            assert "repository/history permission and accountable owner required" in str(e)


if __name__ == "__main__":
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for t in tests:
        t()
        print(f"ok  {t.__name__}")
    print(f"\n{len(tests)} passed")
