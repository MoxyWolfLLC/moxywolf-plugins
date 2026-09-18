#!/usr/bin/env python3
"""XE-010: a packet narrower than the item it claims does not open a review. Stdlib only, offline."""
import peer_review as pr


def packet(coverage=None):
    p = {"outcome": "o", "acceptance_criteria": ["c"], "repos": [], "changed_behavior": "b",
         "exclusions": [], "tests": {}, "release_owner": "dorianatmoxywolf"}
    if coverage is not None:
        p["coverage"] = coverage
    return p


def scored(*probs):
    return {"status": "checked", "criteria":
            [{"item": "XE-005", "criterion_no": i + 1, "declared": f"criterion {i+1}", "probability": p}
             for i, p in enumerate(probs)]}


def test_a_fully_covered_packet_opens():
    ok, status, uncovered = pr.coverage_verdict(packet(scored(0.9, 0.8, 0.72)))
    assert ok and status == "covered" and uncovered == []


def test_an_uncovered_criterion_blocks_and_is_named():
    """The 2026-09-17 case: XE-005 criterion 6 was not in the packet, the review returned 13/13,
    and the criterion shipped unbuilt."""
    ok, status, uncovered = pr.coverage_verdict(packet(scored(0.9, 0.93, 0.94, 0.78, 0.92, 0.13)))
    assert not ok and status == "uncovered"
    assert [c["criterion_no"] for c in uncovered] == [6]


def test_a_missing_probability_counts_as_uncovered():
    """A question that produced no answer has not shown coverage. Absence is not a pass."""
    ok, _, uncovered = pr.coverage_verdict(packet(scored(0.9, None)))
    assert not ok and [c["criterion_no"] for c in uncovered] == [2]


def test_a_report_that_examined_nothing_does_not_pass():
    """EV-001 applied to this report: an empty criteria list is a broken check, not a clean one."""
    ok, status, uncovered = pr.coverage_verdict(packet({"status": "checked", "criteria": []}))
    assert not ok and status == "empty" and uncovered


def test_no_report_opens_but_is_recorded_as_unchecked():
    """Not running this authorises nothing -- the review and the human merge still happen -- so it
    must not block every review on a paid third-party service. It must also never let a reader
    believe coverage was checked when it was not."""
    ok, status, uncovered = pr.coverage_verdict(packet(None))
    assert ok and status == "not_run" and uncovered == []


def test_an_unavailable_scorer_opens_and_says_why():
    ok, status, _ = pr.coverage_verdict(packet({"status": "unavailable", "why": "AI_GATEWAY_API_KEY is not set"}))
    assert ok and status.startswith("unavailable") and "AI_GATEWAY_API_KEY" in status


def test_the_floor_is_the_only_knob_and_it_bites():
    rep = packet(scored(0.55))
    assert pr.coverage_verdict(rep, floor=0.5)[0] is True
    assert pr.coverage_verdict(rep, floor=0.6)[0] is False


def test_the_gate_can_only_ever_add_a_gate():
    """It has no branch that turns a would-be refusal into an approval: every non-blocking path
    returns an EMPTY uncovered list, so nothing it reports can authorise anything."""
    for cov in (None, {"status": "unavailable", "why": "x"}, scored(0.9)):
        ok, _, uncovered = pr.coverage_verdict(packet(cov))
        assert ok is True and uncovered == []
    ok, _, uncovered = pr.coverage_verdict(packet(scored(0.1)))
    assert ok is False and uncovered, "a low score must block, never pass"


if __name__ == "__main__":
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for fn in tests:
        fn(); print(f"ok  {fn.__name__}")
    print(f"\n{len(tests)} passed")
