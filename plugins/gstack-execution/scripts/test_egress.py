#!/usr/bin/env python3
"""TB-003: egress is granted, not filtered. Stdlib only; run directly."""
import ast, re, tempfile
from pathlib import Path

import governance as g

HERE = Path(__file__).resolve().parent
PACKET = {"data_use": {"destinations": ["api.github.com", "*.openrouter.ai"]}}


def ledger():
    return Path(tempfile.mkdtemp()) / "grants.jsonl"


def test_an_ungranted_destination_is_refused_with_the_exact_grant_it_needs():
    try:
        g.check_egress(PACKET, ["https://192.168.1.10:8443/upload"])
        raise AssertionError("an ungranted destination must be refused")
    except g.MissingGrantError as e:
        assert e.grant == g.NetConnectGrant(host="192.168.1.10")
        assert "MissingGrantError: NetConnectGrant(host=192.168.1.10) required for https://192.168.1.10:8443/upload" in str(e)
        assert "data_use.destinations" in str(e) and "'net.connect'" in str(e), "names what would grant it"


def test_a_granted_destination_passes_by_pattern_or_ledger():
    assert g.check_egress(PACKET, ["https://api.github.com/repos/x"])["granted"] == 1
    assert g.check_egress(PACKET, ["eu.openrouter.ai"])["granted"] == 1
    L = ledger()
    try:
        g.check_egress(PACKET, ["https://example.org/a"], ledger=L); raise AssertionError("not yet granted")
    except g.MissingGrantError:
        pass
    g.grant(L, "net.connect", "example.org", granted_by="dorian")
    assert g.check_egress(PACKET, ["https://example.org/a"], ledger=L)["granted"] == 1


def test_refusal_is_the_default_with_no_policy_at_all():
    for dest in ("https://api.github.com", "localhost", ""):
        try:
            g.check_egress({}, [dest]); raise AssertionError(f"{dest!r} passed with no grant")
        except g.MissingGrantError:
            pass


def test_a_policy_that_is_not_a_list_of_patterns_is_refused():
    """Review F1: a scalar "*.example.org" must not become a '*' that grants every host."""
    for bad in ("*.example.org", ["ok.example", ""], [None], {"host": "*"}):
        try:
            g.check_egress({"data_use": {"destinations": bad}}, ["https://unrelated.example"])
            raise AssertionError(f"{bad!r} authorized an unrelated host")
        except g.MissingGrantError:
            raise AssertionError(f"{bad!r} should be refused as a malformed policy, not as a missing grant")
        except ValueError as e:
            assert "must be a list" in str(e)


def test_the_check_reports_what_it_examined():
    r = g.check_egress(PACKET, ["https://api.github.com/a", "https://API.GITHUB.COM/b", "x.openrouter.ai"])
    assert (r["examined"], r["granted"], r["hosts"]) == (3, 3, ["api.github.com", "x.openrouter.ai"])
    assert g.check_egress(PACKET, [])["examined"] == 0


def test_data_permission_checks_a_destination():
    p = {"owner": "d", "data_use": {"owner": "d", "classification": "internal", "allow_repository": True,
                                    "allow_history": True, "destinations": ["api.github.com"]}}
    g.data_permission(p, destination="https://api.github.com/x")
    try:
        g.data_permission(p, destination="https://evil.example/x"); raise AssertionError("refused")
    except g.MissingGrantError as e:
        assert "evil.example" in str(e)


def test_no_list_of_refused_destinations_exists_in_the_source():
    """A denylist passes whatever it hasn't thought of. Nothing may name hosts to refuse."""
    for f in ("governance.py", "task_graph.py"):
        tree = ast.parse((HERE / f).read_text())
        for node in ast.walk(tree):
            names = [t.id for t in getattr(node, "targets", []) if isinstance(t, ast.Name)] if isinstance(node, ast.Assign) else []
            for n in names:
                assert not re.search(r"deny|block|banned|forbid|bad_?(host|dest)", n, re.I), f"{f}: {n} looks like a list of refused destinations"


if __name__ == "__main__":
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for t in tests:
        t()
        print(f"ok  {t.__name__}")
    print(f"\n{len(tests)} passed")
