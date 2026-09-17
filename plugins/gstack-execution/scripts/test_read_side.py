#!/usr/bin/env python3
"""EV-006: the read side of the fake-edge test. Stdlib only."""
import task_graph as tg


# Realistic node ids: the graph builds 'claim-<id>', 'proof-<id>', 'review-<n>'.
NODE = {"id": "n", "depends_on": ["claim-7", "proof-3"], "checks": ["c"]}
DEPS = {"claim-7": {"findings": []}, "proof-3": {"findings": []}}


def test_a_dependency_the_result_never_mentions_is_reported():
    result = {"evidence": ["consulted claim-7"], "findings": [], "coverage": ["c"]}
    assert tg.unreferenced_dependencies(result, NODE, DEPS) == ["proof-3"]


def test_a_dependency_cited_anywhere_in_the_result_counts_as_referenced():
    """Evidence, a finding, or sources all count -- the check asks whether the result shows any
    sign of the dependency, not where."""
    for result in (
        {"evidence": ["claim-7", "proof-3"], "findings": []},
        {"evidence": ["x"], "findings": [{"id": "f", "detail": "per claim-7 and proof-3"}]},
        {"evidence": ["x"], "sources": {"claim-7": {}, "proof-3": {}}},
    ):
        assert tg.unreferenced_dependencies(result, NODE, DEPS) == [], result


def test_reporting_preserves_declaration_order():
    result = {"evidence": ["nothing relevant"]}
    assert tg.unreferenced_dependencies(result, NODE, DEPS) == ["claim-7", "proof-3"]


def test_a_dependency_id_is_matched_as_a_whole_token_not_a_substring():
    """The first version scanned for a naked substring, so dependency 'a' was 'referenced' by the
    word 'relevant'. Short ids would then almost never be flagged and the check would under-report
    in silence."""
    node = {"id": "n", "depends_on": ["a"], "checks": ["c"]}
    deps = {"a": {"findings": []}}
    assert tg.unreferenced_dependencies({"evidence": ["nothing relevant here"]}, node, deps) == ["a"]
    assert tg.unreferenced_dependencies({"evidence": ["consulted a directly"]}, node, deps) == []


def test_a_dependency_that_was_not_declared_is_not_reported():
    """The check is about declared edges. A node cannot have a fake edge it never declared."""
    node = {"id": "n", "depends_on": ["claim-7"], "checks": ["c"]}
    assert tg.unreferenced_dependencies({"evidence": ["x"]}, node, DEPS) == ["claim-7"]


def test_a_declared_dependency_absent_from_the_dependency_map_is_skipped():
    """Declared but not supplied is a graph error the validator owns, not a fake edge."""
    node = {"id": "n", "depends_on": ["claim-7", "missing"], "checks": ["c"]}
    assert tg.unreferenced_dependencies({"evidence": ["claim-7"]}, node, DEPS) == []


def test_the_report_node_surfaces_candidate_fake_edges_with_their_caveat():
    packet = {"repos": [], "owner": "dorianatmoxywolf", "builder": "claude"}
    node = {"id": "report", "kind": "report", "checks": [], "depends_on": ["n1"], "outputs": ["report.json"]}
    deps = {"n1": {"findings": [], "unreferenced_dependencies": ["proof-3"]}}
    out = tg.worker(node, packet, deps, root=None)
    assert out["unreferenced_dependencies"] == {"n1": ["proof-3"]}
    assert "n1 -> proof-3" in out["summary"]
    assert "not proof of unused" in out["summary"], "the caveat must travel with the claim"


def test_a_clean_run_says_nothing_about_fake_edges():
    packet = {"repos": [], "owner": "dorianatmoxywolf", "builder": "claude"}
    node = {"id": "report", "kind": "report", "checks": [], "depends_on": ["n1"], "outputs": ["report.json"]}
    out = tg.worker(node, packet, {"n1": {"findings": [], "unreferenced_dependencies": []}}, root=None)
    assert out["unreferenced_dependencies"] == {}
    assert "fake edge" not in out["summary"].lower()


if __name__ == "__main__":
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for fn in tests:
        fn(); print(f"ok  {fn.__name__}")
    print(f"\n{len(tests)} passed")
