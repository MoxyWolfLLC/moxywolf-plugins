#!/usr/bin/env python3
"""EV-007.2: archive at citation time. Offline — the transport is injected."""
import hashlib, json, sys, tempfile, urllib.parse
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import archive_references as ar

BODY = b"<html>archived page body</html>"


def transport(available=True, save_status=429, seen=None):
    def fake(url, timeout=ar.TIMEOUT):
        if seen is not None:
            seen.append(url)
        if url.startswith(ar.AVAILABILITY):
            key = urllib.parse.unquote(url[len(ar.AVAILABILITY):])
            # the live API rejects a scheme and 429s on a trailing slash; the fake enforces both
            assert not key.startswith("http"), f"lookup sent a scheme: {key}"
            assert not key.endswith("/"), f"lookup sent a trailing slash: {key}"
            if not available:
                return 200, b'{"archived_snapshots": {}}'
            return 200, json.dumps({"archived_snapshots": {"closest": {
                "available": True, "url": "http://web.archive.org/web/2026/" + key}}}).encode()
        if url.startswith(ar.SAVE):
            return save_status, b""
        return 200, BODY
    return fake


def test_the_lookup_key_drops_the_scheme_and_the_trailing_slash():
    """Both measured against the live API: a scheme returns non-JSON, a trailing slash returns 429.
    Neither is a rate limit, and both made every lookup fail."""
    assert ar._lookup_key("https://example.com/") == "example.com"
    assert ar._lookup_key("http://example.com/a/b/") == "example.com/a/b"
    assert ar._lookup_key("https://x.org/p?q=1") == "x.org/p?q=1"


def test_an_archived_url_stores_a_local_copy_and_the_hash_of_what_it_stored():
    with tempfile.TemporaryDirectory() as t:
        d = Path(t)/"snapshots"
        rec = ar.archive_one("https://example.com/post", d, transport())
        assert rec["status"] == "archived"
        assert rec["sha256"] == hashlib.sha256(BODY).hexdigest()
        assert (d/rec["local_copy"]).read_bytes() == BODY, "option (c): the local copy is the point"
        assert rec["archive_url"].startswith("http://web.archive.org/")


def test_persistently_resolvable_identifiers_are_skipped_with_a_reason():
    with tempfile.TemporaryDirectory() as t:
        for url in ("https://doi.org/10.1000/abc", "https://arxiv.org/abs/2502.16161"):
            rec = ar.archive_one(url, Path(t), transport())
            assert rec["status"] == "skipped" and "persistent registry" in rec["why"], rec


def test_a_failed_lookup_is_not_reported_as_no_snapshot():
    """The bug the live run exposed: a malformed query raised, the except folded it into 'nothing
    archived', and the caller then spent a rate-limited save on every reference."""
    def broken(url, timeout=ar.TIMEOUT):
        if url.startswith(ar.AVAILABILITY):
            return 200, b"<html>not json</html>"
        return 200, BODY
    snap, err = ar.wayback_lookup("https://example.com/x", broken)
    assert snap is None and err and "not JSON" in err, (snap, err)


def test_a_genuine_absence_is_distinguishable_from_a_broken_lookup():
    snap, err = ar.wayback_lookup("https://example.com/x", transport(available=False))
    assert snap is None and err is None, "nothing archived is not an error"


def test_a_save_is_only_attempted_when_the_lookup_genuinely_found_nothing():
    """Saves are rate limited for real, so they must not be spent on lookup failures."""
    seen = []
    def broken(url, timeout=ar.TIMEOUT):
        seen.append(url)
        if url.startswith(ar.AVAILABILITY):
            return 200, b"nope"
        return 200, BODY
    with tempfile.TemporaryDirectory() as t:
        ar.archive_one("https://example.com/x", Path(t), broken)
    assert not any(u.startswith(ar.SAVE) for u in seen), "a broken lookup must not burn a save"


def test_an_unreachable_archive_records_the_reason_and_never_raises():
    with tempfile.TemporaryDirectory() as t:
        rec = ar.archive_one("https://nowhere.example/x", Path(t), transport(available=False))
        assert rec["status"] == "unavailable"
        assert rec["local_copy"] is None and rec["sha256"] is None
        assert "rate limited" in rec["why"], rec


def test_an_already_archived_url_is_not_fetched_again():
    seen = []
    with tempfile.TemporaryDirectory() as t:
        d = Path(t)/"s"
        idx = ar.sweep("see https://example.com/post", d, transport(seen=seen))
        before = len(seen)
        ar.sweep("see https://example.com/post", d, transport(seen=seen), existing=idx)
        assert len(seen) == before, "re-running must not re-fetch settled references"


def test_coverage_counts_every_state():
    idx = {"a": {"status": "archived"}, "b": {"status": "skipped"}, "c": {"status": "unavailable"}}
    assert ar.coverage(idx) == {"total": 3, "archived": 1, "skipped": 1, "unavailable": 1}


def test_cited_urls_are_deduplicated_and_trailing_punctuation_is_dropped():
    text = "see https://a.com/x, and https://a.com/x again (https://b.com/y)."
    assert ar.cited_urls(text) == ["https://a.com/x", "https://b.com/y"]


def test_the_gate_counts_the_papers_cited_urls_not_the_index_contents():
    """Reported as blocking by the review of this change. Counting index entries meant a paper
    citing ten unarchived URLs passed on the strength of one archived entry belonging to a
    different paper: coverage computed over the wrong denominator."""
    import json as _json, tempfile as _tf
    import release_gate as rg
    paper = "Cited https://example.com/a and https://gone.example/z."
    with _tf.TemporaryDirectory() as t:
        idx = Path(t)/"i.json"
        idx.write_text(_json.dumps({"https://unrelated.com/other": {"status": "archived"}}))
        status, detail, examined, _ = rg.check_archive_coverage(paper, {"archive_index": str(idx)})
        assert status == rg.SKIP, "an index covering none of this paper's URLs cannot pass"
        assert examined == 0 and "no archive record" in detail

        idx.write_text(_json.dumps({"https://example.com/a": {"status": "archived"},
                                    "https://gone.example/z": {"status": "unavailable"}}))
        status, detail, examined, _ = rg.check_archive_coverage(paper, {"archive_index": str(idx)})
        assert status == rg.PASS and examined == 2, (status, detail, examined)
        assert "of 2 cited" in detail and "unavailable" in detail


def test_the_gate_and_the_archiver_agree_on_what_a_cited_url_is():
    """Two URL extractors meant a URL the archiver recorded could not be matched back to the paper
    that cited it. One producer now; this asserts they are literally the same function."""
    import release_gate as rg
    assert ar.cited_urls is rg.cited_urls
    text = "see https://a.com/x, and https://a.com/x again (https://b.com/y)."
    assert rg.cited_urls(text) == ["https://a.com/x", "https://b.com/y"]


if __name__ == "__main__":
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for fn in tests:
        fn(); print(f"ok  {fn.__name__}")
    print(f"\n{len(tests)} passed")
