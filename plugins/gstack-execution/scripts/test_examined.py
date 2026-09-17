#!/usr/bin/env python3
"""EV-008: record what a review examined, not only what it found."""
import os, tempfile, time
from pathlib import Path
import peer_review as pr


def surface(t):
    r = Path(t); (r/"CHANGE.diff").write_text("d"*80)
    (r/"changed").mkdir(); (r/"changed"/"a.py").write_text("a"*80)
    (r/"callers").mkdir(); (r/"callers"/"b.py").write_text("b"*80)
    pr._age_atimes(r)
    return r


def test_reads_are_observable_by_construction_not_by_luck():
    """Aging atime below mtime makes every read observable. That is the guarantee the record
    depends on, so it is the only thing asserted here.

    The naive scheme (atime == mtime, as a freshly written file has it) is NOT asserted against,
    because it is flaky rather than broken: measured runs detected 0 of 6, then 1 of 5, and the
    first version of this test asserted "never detects" and passed in the gate while failing
    standalone. A flaky instrument is worse than a broken one -- it produces intermittently wrong
    records that look like measurements -- and a test that asserts flakiness is flaky itself.
    """
    with tempfile.TemporaryDirectory() as t:
        r = Path(t)
        forced = []
        for i in range(8):
            q = r/f"f{i}"; q.write_text("x"*80)
            st = q.stat(); os.utime(q, ns=(st.st_mtime_ns - 2_000_000_000, st.st_mtime_ns))
            b = q.stat().st_atime_ns
            q.read_text()
            forced.append(q.stat().st_atime_ns != b)
        assert all(forced), f"aged atimes must make every read observable, got {forced}"


def test_only_the_files_actually_opened_are_reported():
    with tempfile.TemporaryDirectory() as t:
        r = surface(t)
        before = pr._atime_map(r)
        (r/"changed"/"a.py").read_text()
        rep = pr.examined_report(before, r, {})
        assert rep["examined"] == ["changed/a.py"], rep
        assert rep["offered_count"] == 3, rep


def test_a_review_that_stayed_inside_the_diff_is_visible_as_such():
    """EV-008.2. 'No findings' from a reviewer that opened only the diff is a different event from
    'no findings' after it read the callers, and the record has to tell them apart."""
    with tempfile.TemporaryDirectory() as t:
        r = surface(t)
        before = pr._atime_map(r)
        (r/"CHANGE.diff").read_text()
        rep = pr.examined_report(before, r, {})
        assert rep["looked_beyond_the_diff"] is False, rep
        assert rep["examined_beyond_the_diff"] == [], rep


def test_reading_a_caller_counts_as_going_beyond_the_diff():
    with tempfile.TemporaryDirectory() as t:
        r = surface(t)
        before = pr._atime_map(r)
        (r/"callers"/"b.py").read_text()
        rep = pr.examined_report(before, r, {})
        assert rep["looked_beyond_the_diff"] is True
        assert rep["examined_beyond_the_diff"] == ["callers/b.py"], rep


def test_examining_nothing_is_recorded_as_nothing_not_omitted():
    with tempfile.TemporaryDirectory() as t:
        r = surface(t)
        rep = pr.examined_report(pr._atime_map(r), r, {})
        assert rep["read_tracking"] == "available"
        assert rep["examined"] == [] and rep["examined_count"] == 0, rep


def test_an_unmeasurable_filesystem_says_so_rather_than_reporting_nothing_examined():
    """The failure this must never produce: 'the reviewer examined nothing' when the truth is
    'reads could not be measured'. A false accusation of laziness is worse than no measurement."""
    rep = pr.examined_report(None, Path("/tmp"), {})
    assert rep["read_tracking"] == "unavailable"
    assert "examined" not in rep, "an unmeasurable run must not report an empty examined list"
    assert "not measured" in rep["why"]


def test_the_probe_agrees_with_reality():
    """The first probe wrote a file and read it without aging atime, so it reported the instrument
    broken while the instrument worked -- disabling a check that functions."""
    with tempfile.TemporaryDirectory() as t:
        r = surface(t)
        assert pr.read_tracking_probe(r) is True
        before = pr._atime_map(r)
        (r/"changed"/"a.py").read_text()
        assert pr.examined_report(before, r, {})["examined"] == ["changed/a.py"]


if __name__ == "__main__":
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for fn in tests:
        fn(); print(f"ok  {fn.__name__}")
    print(f"\n{len(tests)} passed")
