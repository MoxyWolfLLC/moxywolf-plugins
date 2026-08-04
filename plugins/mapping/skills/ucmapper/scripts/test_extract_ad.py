#!/usr/bin/env python3
"""Regression tests for extract_ad.py. No network: every case is a synthetic document.

Run: python3 test_extract_ad.py    (exit 0 all passed, 1 otherwise)

The case that matters most here is the duplicate reference. Rule 3 deliberately keeps two
citations that share a reference when they differ in guidance, parent or genealogy. Until
0.2.0 the parity hash manifest was keyed by reference, so one of those two was overwritten
and never compared -- the parity check reported 0/0/0 while testing a short manifest.
"""

import importlib.util
import os
import sys

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
    check("collision is warned about",
          any("distinct citations" in w for w in warnings))


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
          not any("does not match stats.citations" in w for w in warnings))
    check("nothing is stranded outside the tree",
          not any("unreachable from any root" in w for w in warnings))
    check("the genuine heading-vs-body collision is still reported",
          any("distinct citations" in w for w in warnings))

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
          not any("distinct citations" in w for w in w1))
    check("count reconciles against stats.citations",
          not any("does not match stats.citations" in w for w in w1))
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
    check("orphan parent is warned about",
          any("resolves to no surviving citation" in w for w in warnings))


def main():
    for fn in (test_manifest_covers_every_citation,
               test_parity_catches_a_change_in_a_duplicated_reference,
               test_identical_rows_merge_even_after_a_genuine_collision,
               test_genuinely_distinct_same_reference_rows_are_all_kept,
               test_clean_document_is_stable_and_flat_hashes,
               test_guidance_cleaning,
               test_orphan_parent_becomes_a_root_with_a_warning):
        print(f"\n{fn.__name__}")
        fn()
    print()
    if FAILURES:
        print(f"FAILED ({len(FAILURES)}): {', '.join(FAILURES)}")
        sys.exit(1)
    print("all tests passed")


if __name__ == "__main__":
    main()
