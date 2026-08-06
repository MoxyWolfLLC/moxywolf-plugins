#!/usr/bin/env python3
"""Regression tests for extract_ad.py. No network: every case is a synthetic document.

Run: python3 test_extract_ad.py    (exit 0 all passed, 1 otherwise)

The case that matters most here is the duplicate reference. Rule 3 deliberately keeps two
citations that share a reference when they differ in guidance, parent or genealogy. Until
0.2.0 the parity hash manifest was keyed by reference, so one of those two was overwritten
and never compared -- the parity check reported 0/0/0 while testing a short manifest.
"""

import importlib.util
import json
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location("extract_ad", os.path.join(HERE, "extract_ad.py"))
ea = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ea)

FAILURES = []


def check(name: str, condition: bool, detail: str = "") -> None:
    if condition:
        print(f"  ok   {name}")
    else:
        print(f"  FAIL {name} {detail}")
        FAILURES.append(name)


def msgs(warnings: list) -> list:
    """Warning messages. Under schemaVersion 2 a warning is an object, not a string."""
    return [w["message"] for w in warnings]


def classes(warnings: list) -> set:
    return {w["class"] for w in warnings}


def cite(cid, ref, guidance, sort_id, parent=None, genealogy=""):
    return {"id": cid, "reference": ref, "guidance": guidance, "sort_id": sort_id,
            "sort_value": int(cid), "genealogy": genealogy,
            "parent": None if parent is None else {"id": parent}}


def doc(citations, stats=None):
    return {"published_name": "Synthetic Document", "id": "9999", "originator": "test",
            "stats": {"citations": stats if stats is not None else len(citations)},
            "citations": citations}


def test_manifest_covers_every_citation():
    """Two siblings sharing a reference must each get their own manifest entry."""
    d = doc([
        cite("1", "ROOT", "root", "001"),
        cite("2", "DUP", "first variant", "001 001", parent="1"),
        cite("3", "DUP", "second variant", "001 002", parent="1"),
    ], stats=3)
    payload, warnings, meta = ea.transform(d, "9999")
    check("duplicate reference keeps both citations", len(payload["citations"]) == 3,
          f"got {len(payload['citations'])}")
    check("manifest covers every citation",
          len(meta["hashes"]) == len(payload["citations"]),
          f"manifest {len(meta['hashes'])} vs citations {len(payload['citations'])}")
    check("manifest is keyed by elementId", set(meta["hashes"]) == {"1", "2", "3"},
          f"keys {sorted(meta['hashes'])}")
    # Guarded rather than indexed: against a reference-keyed manifest these keys are absent,
    # and a KeyError traceback would abort the run instead of reporting a clean failure.
    check("the two duplicate-reference rows hash differently",
          meta["hashes"].get("2") is not None
          and meta["hashes"].get("2") != meta["hashes"].get("3"),
          f"hashes for 2/3: {meta['hashes'].get('2')}/{meta['hashes'].get('3')}")
    check("collision is warned about", ea.W_REFERENCE_COLLISION in classes(warnings),
          f"classes {sorted(classes(warnings))}")


def test_parity_catches_a_change_in_a_duplicated_reference():
    """A content edit confined to the FIRST of two same-reference rows must be caught.

    This is the exact hole the reference-keyed manifest had: the second row overwrote the
    first, so editing the first changed nothing the diff could see.
    """
    base = [
        cite("1", "ROOT", "root", "001"),
        cite("2", "DUP", "first variant", "001 001", parent="1"),
        cite("3", "DUP", "second variant", "001 002", parent="1"),
    ]
    tampered = [
        cite("1", "ROOT", "root", "001"),
        cite("2", "DUP", "FIRST VARIANT EDITED", "001 001", parent="1"),
        cite("3", "DUP", "second variant", "001 002", parent="1"),
    ]
    _, _, m_a = ea.transform(doc(base, stats=3), "9999")
    _, _, m_b = ea.transform(doc(tampered, stats=3), "9999")
    a, b = m_a["hashes"], m_b["hashes"]
    mismatch = [k for k in set(a) & set(b) if a[k] != b[k]]
    check("edit to the first duplicate row is detected", mismatch == ["2"],
          f"mismatch={mismatch}")


def test_identical_rows_merge_even_after_a_genuine_collision():
    """Three rows share a reference: a heading, then two bodies identical to each other.

    The two bodies must merge with each other. Through 0.2.0 every row was tested only
    against the FIRST survivor for its reference, so once the heading recorded a collision
    the two identical bodies were never compared and both were kept -- inflating the count
    past stats.citations and stranding one outside the tree. AD 4501 (ISO/IEC 27002:2022,
    reference '§ 5.17 Control') is the document that surfaced it.
    """
    d = doc([
        cite("1", "ROOT", "root", "001"),
        cite("2", "X", "heading text", "001 001", parent="1", genealogy="0000001"),
        cite("3", "X", "identical body", "001 001 001", parent="2", genealogy="0000001 0000002"),
        cite("4", "X", "identical body", "001 001 002", parent="2", genealogy="0000001 0000002"),
    ], stats=3)
    payload, warnings, meta = ea.transform(d, "9999")
    ids = [c["hierarchy"]["elementId"] for c in payload["citations"]]
    check("identical rows merge across a prior collision", ids == ["1", "2", "3"], f"got {ids}")
    check("count reconciles against stats.citations",
          ea.W_COUNT_RECONCILIATION not in classes(warnings))
    check("nothing is stranded outside the tree",
          ea.W_UNREACHABLE not in classes(warnings))
    check("the genuine heading-vs-body collision is still reported",
          ea.W_REFERENCE_COLLISION in classes(warnings))

    child_ids = {k["elementId"] for c in payload["citations"] for k in c["hierarchy"]["children"]}
    dropped = [c["hierarchy"]["elementId"] for c in payload["citations"]
               if c["hierarchy"]["parents"] and c["hierarchy"]["elementId"] not in child_ids]
    check("every non-root citation is some parent's child", dropped == [], f"dropped {dropped}")


def test_genuinely_distinct_same_reference_rows_are_all_kept():
    """Three rows share a reference and all differ. All three survive; none is merged away."""
    d = doc([
        cite("1", "ROOT", "root", "001"),
        cite("2", "X", "variant one", "001 001", parent="1", genealogy="0000001"),
        cite("3", "X", "variant two", "001 002", parent="1", genealogy="0000001"),
        cite("4", "X", "variant three", "001 003", parent="1", genealogy="0000001"),
    ], stats=4)
    payload, warnings, meta = ea.transform(d, "9999")
    check("all three distinct variants survive", len(payload["citations"]) == 4,
          f"got {len(payload['citations'])}")
    check("each variant gets its own manifest entry", len(meta["hashes"]) == 4,
          f"manifest {len(meta['hashes'])}")
    check("all four hashes are distinct", len(set(meta["hashes"].values())) == 4)


def test_clean_document_is_stable_and_flat_hashes():
    d = doc([
        cite("1", "SECTION 1", "heading", "001"),
        cite("2", "1.1", "body text", "001 001", parent="1"),
        cite("3", "1.2", "more body", "001 002", parent="1"),
    ])
    p1, w1, m1 = ea.transform(d, "9999")
    p2, w2, m2 = ea.transform(d, "9999")
    check("transform is deterministic", m1["hashes"] == m2["hashes"])
    check("no collision warning on a clean document",
          ea.W_REFERENCE_COLLISION not in classes(w1))
    check("count reconciles against stats.citations",
          ea.W_COUNT_RECONCILIATION not in classes(w1))
    check("root count is right", m1["roots"] == 1, f"got {m1['roots']}")


def test_guidance_cleaning():
    warnings = []
    check("brace spans are removed",
          ea.clean_guidance("take a {reasonable step} now", warnings) == "take a  now".replace("  ", " "))
    check("runs of 2+ whitespace collapse",
          ea.clean_guidance("a    b", warnings) == "a b")
    check("a lone newline survives (deliberate, pinned so JS can match)",
          ea.clean_guidance("a\nb", warnings) == "a\nb")
    check("space before punctuation is tightened",
          ea.clean_guidance("word , next", warnings) == "word, next")


def test_orphan_parent_becomes_a_root_with_a_warning():
    d = doc([
        cite("1", "ROOT", "root", "001"),
        cite("2", "ORPHAN", "dangling", "001 001", parent="404"),
    ], stats=2)
    payload, warnings, meta = ea.transform(d, "9999")
    check("orphan is kept, not dropped", len(payload["citations"]) == 2)
    check("orphan is treated as a root", meta["roots"] == 2, f"got {meta['roots']}")
    check("orphan parent is warned about", ea.W_ORPHAN_PARENT in classes(warnings),
          f"classes {sorted(classes(warnings))}")
    check("orphan parent is high severity",
          all(w["severity"] == "high" for w in warnings if w["class"] == ea.W_ORPHAN_PARENT))


def test_every_warning_is_well_formed():
    """Whatever the document does, every warning it produces carries the full shape.

    Cheap to get wrong: a single append() left un-migrated puts a bare string into an array
    of objects, and nothing downstream notices until the HTML viewer prints [object Object]
    or a consumer indexes ['class'] on a str. This walks documents that between them fire
    most of the classes and asserts the shape on every one.
    """
    cases = [
        doc([cite("1", "ROOT", "root", "001"),
             cite("2", "DUP", "a", "001 001", parent="1"),
             cite("3", "DUP", "b", "001 002", parent="1")], stats=3),
        doc([cite("1", "ROOT", "root", "001"),
             cite("2", "ORPHAN", "dangling", "001 001", parent="404")], stats=2),
        doc([cite("1", "R", "take a {nested {brace} span} here", "001")], stats=1),
        doc([], stats=0),
        doc([cite("1", "A", "x", "1"), cite("2", "B", "y", "001 001", parent="1")], stats=99),
    ]
    seen = set()
    bad = []
    for i, d in enumerate(cases):
        _, warnings, _ = ea.transform(d, "9999")
        for w in warnings:
            seen.add(w.get("class"))
            if not isinstance(w, dict):
                bad.append(f"case {i}: not a dict ({type(w).__name__})")
            elif set(w) != {"@type", "class", "severity", "message"}:
                bad.append(f"case {i}: keys {sorted(w)}")
            elif w["@type"] != "Warning" or w["severity"] not in ea.SEVERITIES or not w["message"]:
                bad.append(f"case {i}: {w!r}")
    check("every warning has @type/class/severity/message", bad == [], f"{bad[:3]}")
    check("the walked cases fire several distinct classes", len(seen) >= 5, f"saw {sorted(seen)}")
    check("nested-brace markup warns exactly once per document",
          sum(1 for w in ea.transform(cases[2], "9999")[1]
              if w["class"] == ea.W_NESTED_BRACE) == 1)


def test_document_hash_tracks_citations_not_prose():
    """The chain hash must move when the document moves and hold still otherwise."""
    base = doc([cite("1", "ROOT", "root", "001"),
                cite("2", "1.1", "body text", "001 001", parent="1")], stats=2)
    edited = doc([cite("1", "ROOT", "root", "001"),
                  cite("2", "1.1", "body text EDITED", "001 001", parent="1")], stats=2)
    h1 = ea.transform(base, "9999")[2]["documentHash"]
    h2 = ea.transform(base, "9999")[2]["documentHash"]
    h3 = ea.transform(edited, "9999")[2]["documentHash"]
    check("document hash is deterministic", h1 == h2, f"{h1} vs {h2}")
    check("document hash moves when a citation changes", h1 != h3)
    check("document hash is sha256-shaped", len(h1) == 64 and all(c in "0123456789abcdef" for c in h1))
    # Built from the parity manifest, so a title change alone is a different document but a
    # warning-text or schema-field change is not. That is the property that keeps the chain
    # reporting the publisher's edits rather than ours.
    retitled = dict(base, published_name="Synthetic Document (renamed)")
    check("document hash moves when the title changes",
          ea.transform(retitled, "9999")[2]["documentHash"] != h1)


def test_snapshot_chain_links_and_detects_drift():
    warnings = []
    first = ea.extend_chain([], "aa" * 32, 10, warnings, "2026-08-06")
    check("first snapshot has no previous", first[0]["previousHash"] is None)
    check("first snapshot is not drift", first[0]["drifted"] is False)
    check("first snapshot raises no warning", warnings == [], f"{warnings}")

    same = ea.extend_chain(first, "aa" * 32, 10, warnings, "2026-09-01")
    check("chain grows on a re-run", len(same) == 2)
    check("unchanged document is not drift", same[-1]["drifted"] is False)
    check("unchanged re-run still records the date", same[-1]["runDate"] == "2026-09-01")
    check("unchanged re-run raises no warning", warnings == [], f"{warnings}")

    moved = ea.extend_chain(same, "bb" * 32, 11, warnings, "2026-10-01")
    check("changed document is drift", moved[-1]["drifted"] is True)
    check("previous hash is carried", moved[-1]["previousHash"] == "aa" * 32)
    check("drift raises an edition-drift warning", ea.W_EDITION_DRIFT in classes(warnings),
          f"classes {sorted(classes(warnings))}")
    check("drift is high severity",
          all(w["severity"] == "high" for w in warnings if w["class"] == ea.W_EDITION_DRIFT))


def test_prior_snapshots_is_forgiving():
    with tempfile.TemporaryDirectory() as tmp:
        missing = os.path.join(tmp, "nope.json")
        check("absent artifact yields an empty chain", ea.prior_snapshots(missing) == [])

        broken = os.path.join(tmp, "broken.json")
        with open(broken, "w", encoding="utf-8") as fh:
            fh.write("{not json")
        check("malformed artifact yields an empty chain rather than halting",
              ea.prior_snapshots(broken) == [])

        v1 = os.path.join(tmp, "v1.json")
        with open(v1, "w", encoding="utf-8") as fh:
            json.dump({"title": "old", "warnings": ["a bare string"], "citations": []}, fh)
        check("a schemaVersion 1 artifact yields an empty chain, not a crash",
              ea.prior_snapshots(v1) == [])


def test_end_to_end_write_chains_across_two_runs():
    """The write path is where the chain actually has to work: read prior, then overwrite."""
    script = os.path.join(HERE, "extract_ad.py")
    d = doc([cite("1", "ROOT", "root", "001"),
             cite("2", "1.1", "body text", "001 001", parent="1")], stats=2)
    edited = doc([cite("1", "ROOT", "root", "001"),
                  cite("2", "1.1", "body text EDITED", "001 001", parent="1")], stats=2)

    def run(raw_doc, out, day):
        raw = os.path.join(out, f"raw-{day}.json")
        with open(raw, "w", encoding="utf-8") as fh:
            json.dump(raw_doc, fh)
        proc = subprocess.run(
            [sys.executable, script, "--ad", "9999", "--raw", raw, "--out", out, "--today", day],
            capture_output=True, text=True)
        with open(os.path.join(out, "ad-9999-citations.json"), encoding="utf-8") as fh:
            return json.load(fh), proc

    with tempfile.TemporaryDirectory() as tmp:
        doc1, p1 = run(d, tmp, "2026-08-06")
        check("run exits clean", p1.returncode == 0, p1.stderr[-200:])
        check("artifact declares schemaVersion 2", doc1.get("schemaVersion") == 2)
        check("first run writes one snapshot", len(doc1.get("snapshots", [])) == 1)
        check("warnings are objects on disk",
              all(isinstance(w, dict) and "class" in w for w in doc1["warnings"]),
              f"{doc1['warnings'][:1]}")

        doc2, _ = run(d, tmp, "2026-09-01")
        check("re-running the same document appends rather than replaces",
              len(doc2["snapshots"]) == 2)
        check("no drift on an unchanged re-run", doc2["snapshots"][-1]["drifted"] is False)
        check("citations are unchanged across the re-run",
              doc2["citations"] == doc1["citations"])

        doc3, p3 = run(edited, tmp, "2026-10-01")
        check("edited document is recorded as drift", doc3["snapshots"][-1]["drifted"] is True)
        check("edited document warns about edition drift",
              ea.W_EDITION_DRIFT in {w["class"] for w in doc3["warnings"]})
        check("the chain links back to the prior hash",
              doc3["snapshots"][-1]["previousHash"] == doc2["snapshots"][-1]["documentHash"])
        check("drift is reported on stdout", "DRIFTED" in p3.stdout, p3.stdout[-200:])


def main():
    for fn in (test_manifest_covers_every_citation,
               test_parity_catches_a_change_in_a_duplicated_reference,
               test_identical_rows_merge_even_after_a_genuine_collision,
               test_genuinely_distinct_same_reference_rows_are_all_kept,
               test_clean_document_is_stable_and_flat_hashes,
               test_guidance_cleaning,
               test_orphan_parent_becomes_a_root_with_a_warning,
               test_every_warning_is_well_formed,
               test_document_hash_tracks_citations_not_prose,
               test_snapshot_chain_links_and_detects_drift,
               test_prior_snapshots_is_forgiving,
               test_end_to_end_write_chains_across_two_runs):
        print(f"\n{fn.__name__}")
        # An exception in one case must not abort the rest of the suite. Running this file
        # against an older extract_ad.py is a normal thing to do -- it is how the repo
        # states what a change actually fixed -- and against a version predating a feature
        # the reference raises rather than returning a wrong answer. That is a failure, and
        # it should be counted next to the others instead of truncating the report.
        try:
            fn()
        except Exception as exc:                                  # noqa: BLE001
            print(f"  ERROR {fn.__name__}: {type(exc).__name__}: {exc}")
            FAILURES.append(f"{fn.__name__} (raised {type(exc).__name__})")
    print()
    if FAILURES:
        print(f"FAILED ({len(FAILURES)}): {', '.join(FAILURES)}")
        sys.exit(1)
    print("all tests passed")


if __name__ == "__main__":
    main()
