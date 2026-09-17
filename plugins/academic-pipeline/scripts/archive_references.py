#!/usr/bin/env python3
"""EV-007.2: archive every cited URL, and store the snapshot and its hash.

A citation to a bare URL is a promise that a reader can see what you saw. Link rot breaks that
promise silently: the citation still looks fine. So each cited URL gets an archived snapshot, a
local copy, and a hash, recorded beside the bibliography.

Storage is BOTH (Dorian, 2026-09-17): the Wayback reference for durability that outlives this
repository, and a local copy for durability that outlives archive.org.

What the hash means, stated because it is easy to over-read: it covers the ARCHIVED SNAPSHOT, not
the live page. Hashing live HTML detects nothing useful -- ads, timestamps and session tokens
change on every fetch, so the hash would differ every time. This proves "this is the page I cited",
not "the page has not changed". Drift detection needs content extraction and is a different feature.

DOIs, arXiv ids and PubMed ids are skipped and recorded as skipped: they already resolve through a
persistent registry, so a snapshot adds bytes and no durability.

ponytail: stdlib urllib, no requests, no API key. The transport is injectable so the tests never
touch the network. Wayback's save endpoint is rate limited (observed HTTP 429 on 2026-09-17), so an
existing snapshot is preferred over forcing a new one, and a refused save is a RECORDED STATE rather
than a failure -- a citation is never blocked on an archive being reachable.
"""
import argparse, hashlib, json, os, re, sys, urllib.error, urllib.parse, urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from release_gate import canonical_work, cited_urls   # one producer of identity and of cited URLs

AVAILABILITY = "https://archive.org/wayback/available?url="
SAVE = "https://web.archive.org/save/"
INDEX_NAME = "archive-index.json"
TIMEOUT = 45

SKIP_KINDS = {"doi", "arxiv", "pmid"}              # persistent resolvers; a snapshot adds nothing


def _open(url, timeout=TIMEOUT):
    req = urllib.request.Request(url, headers={"User-Agent": "gstack-archive/1.0"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.status, r.read()


def _lookup_key(url):
    """The availability API accepts the scheme-less form ONLY.

    Measured 2026-09-17, both by running it against the live API rather than the mock:

      url=example.com   -> HTTP 200 with a snapshot
      url=example.com/  -> HTTP 429
      url=https://example.com/ -> not JSON

    The trailing slash is not a rate limit despite the 429 it returns, and the scheme breaks the
    query outright. Passing the full URL made every lookup fail, and the original except clause
    turned that into a plausible-looking "no snapshot exists" -- a query bug wearing an answer's
    clothes, which then spent a genuinely rate-limited save on every reference.
    """
    return re.sub(r"^https?://", "", url).rstrip("/")


def wayback_lookup(url, opener=_open):
    """(snapshot_url, error). Cheap, and not rate limited.

    Returns a distinct error rather than folding a failed lookup into "no snapshot": they have
    different causes and a caller that cannot tell them apart will retry the wrong thing.
    """
    try:
        status, body = opener(AVAILABILITY + urllib.parse.quote(_lookup_key(url), safe="/:@!$&'()*+,;=~"))
        if status != 200:
            return None, f"availability lookup returned HTTP {status}"
        snap = (json.loads(body).get("archived_snapshots") or {}).get("closest") or {}
        if snap.get("available"):
            return snap.get("url"), None
        return None, None                                   # looked, genuinely nothing there
    except ValueError as e:
        return None, f"availability response was not JSON ({e})"
    except (urllib.error.URLError, OSError, TimeoutError) as e:
        return None, f"availability lookup unreachable: {type(e).__name__}"


def wayback_save(url, opener=_open):
    """(snapshot_url, reason). Rate limited in practice, so the reason travels with the failure."""
    try:
        status, _ = opener(SAVE + url)
        if status == 429:
            return None, "wayback save is rate limited (HTTP 429)"
        if status >= 400:
            return None, f"wayback save returned HTTP {status}"
        snap, err = wayback_lookup(url, opener)
        return snap, err
    except urllib.error.HTTPError as e:
        return None, f"wayback save returned HTTP {e.code}"
    except (urllib.error.URLError, OSError, TimeoutError) as e:
        return None, f"wayback unreachable: {type(e).__name__}"


def archive_one(url, snapshot_dir, opener=_open):
    """One reference's archive record. Never raises; a failure is a recorded state."""
    ident, kind = canonical_work(url)
    if kind in SKIP_KINDS:
        return {"url": url, "status": "skipped", "identity": ident,
                "why": f"{kind} resolves through a persistent registry; a snapshot adds no durability"}

    snap, lookup_err = wayback_lookup(url, opener)
    saved_reason = lookup_err
    if not snap:
        # only spend a rate-limited save when the lookup genuinely found nothing
        if lookup_err is None:
            snap, saved_reason = wayback_save(url, opener)
    if not snap:
        return {"url": url, "status": "unavailable", "identity": ident,
                "why": saved_reason or "no snapshot exists and none could be made",
                "local_copy": None, "sha256": None}

    try:
        status, body = opener(snap)
        if status != 200 or not body:
            return {"url": url, "status": "unavailable", "identity": ident, "archive_url": snap,
                    "why": f"snapshot exists but did not fetch (HTTP {status})",
                    "local_copy": None, "sha256": None}
    except (urllib.error.URLError, OSError, TimeoutError) as e:
        return {"url": url, "status": "unavailable", "identity": ident, "archive_url": snap,
                "why": f"snapshot fetch failed: {type(e).__name__}", "local_copy": None, "sha256": None}

    digest = hashlib.sha256(body).hexdigest()
    Path(snapshot_dir).mkdir(parents=True, exist_ok=True)
    local = Path(snapshot_dir) / f"{digest[:16]}.html"
    local.write_bytes(body)
    return {"url": url, "status": "archived", "identity": ident, "archive_url": snap,
            "local_copy": str(local.name), "sha256": digest, "bytes": len(body)}


def sweep(text, snapshot_dir, opener=_open, existing=None):
    """Archive every cited URL not already recorded. Returns the index."""
    index = dict(existing or {})
    for url in cited_urls(text):
        if index.get(url, {}).get("status") == "archived":
            continue                                # already has a snapshot and a hash
        index[url] = archive_one(url, snapshot_dir, opener)
    return index


def coverage(index):
    """What the record actually says, for a gate to report without touching the network."""
    by = {}
    for rec in index.values():
        by[rec["status"]] = by.get(rec["status"], 0) + 1
    return {"total": len(index), "archived": by.get("archived", 0),
            "skipped": by.get("skipped", 0), "unavailable": by.get("unavailable", 0)}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--references", required=True, help="bibliography or paper file containing cited URLs")
    ap.add_argument("--snapshots", help="snapshot directory (default: <references dir>/snapshots)")
    a = ap.parse_args(argv)
    src = Path(a.references)
    snaps = Path(a.snapshots) if a.snapshots else src.parent / "snapshots"
    idx_path = snaps / INDEX_NAME
    existing = json.loads(idx_path.read_text()) if idx_path.exists() else {}
    index = sweep(src.read_text(errors="replace"), snaps, existing=existing)
    snaps.mkdir(parents=True, exist_ok=True)
    idx_path.write_text(json.dumps(index, indent=2, sort_keys=True))
    c = coverage(index)
    print(json.dumps({"index": str(idx_path), **c}, indent=2))
    for url, rec in sorted(index.items()):
        if rec["status"] == "unavailable":
            print(f"  unavailable: {url} — {rec['why']}", file=sys.stderr)
    return 0            # never blocks: an unreachable archive is reported, not fatal


def _selftest():
    import tempfile
    calls = []

    def fake(url, timeout=TIMEOUT):
        calls.append(url)
        if url.startswith(AVAILABILITY):
            target = urllib.parse.unquote(url[len(AVAILABILITY):])
            assert not target.startswith("http"), f"lookup must use the scheme-less form, got {target}"
            if "norecord" in target:
                return 200, b'{"archived_snapshots": {}}'
            return 200, json.dumps({"archived_snapshots": {"closest": {
                "available": True, "url": "http://web.archive.org/web/2026/" + target}}}).encode()
        if url.startswith(SAVE):
            return 429, b""
        return 200, b"<html>archived page body</html>"

    with tempfile.TemporaryDirectory() as t:
        d = Path(t) / "snapshots"
        assert _lookup_key("https://example.com/a") == "example.com/a"
        rec = archive_one("https://example.com/post", d, fake)
        assert rec["status"] == "archived" and rec["sha256"] and rec["local_copy"], rec
        assert (d / rec["local_copy"]).read_bytes() == b"<html>archived page body</html>"
        assert rec["sha256"] == hashlib.sha256(b"<html>archived page body</html>").hexdigest()

        skip = archive_one("https://doi.org/10.1000/abc", d, fake)
        assert skip["status"] == "skipped" and "persistent registry" in skip["why"], skip

        gone = archive_one("https://norecord.example.com/x", d, fake)
        assert gone["status"] == "unavailable" and "rate limited" in gone["why"], gone
        assert gone["local_copy"] is None and gone["sha256"] is None

        idx = sweep("see https://example.com/post and https://doi.org/10.1000/abc", d, fake)
        assert coverage(idx) == {"total": 2, "archived": 1, "skipped": 1, "unavailable": 0}, coverage(idx)

        before = len(calls)
        idx2 = sweep("see https://example.com/post", d, fake, existing=idx)
        assert len(calls) == before, "an already-archived URL must not be fetched again"
        assert coverage(idx2)["archived"] == 1
    print("archive_references selftest ok")
    return 0


if __name__ == "__main__":
    sys.exit(_selftest() if "--selftest" in sys.argv else main())
