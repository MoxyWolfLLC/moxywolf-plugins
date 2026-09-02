#!/usr/bin/env python3
"""Extract a UCF Authority Document into a citations JSON + a self-contained HTML tree.

The transform here is deterministic on purpose: every rule that has an exact form
(the guidance-cleaning regexes, the sort, the dedupe identity test, the FNV-1a hash)
lives in code so two runs of the same document produce byte-identical output, and so
the Python hashes can be compared against a JavaScript implementation without drift.

The judgment calls (is this document's schema what we expect, what is the official
URL, which LicenseStamp class applies) stay with the agent -- see SKILL.md.

Modes
  --recon        Fetch and report the schema reconnaissance only. No files written.
  (default)      Full transform; writes ad-{ID}-citations.json and ad-{ID}-hierarchy.html.
  --parity FILE  Transform a second, independently fetched raw JSON and diff the
                 per-citation hashes against the run built from --raw.

Exit codes: 0 ok, 1 halt (fetch/schema/validation failure), 2 parity mismatch.

Output schema
  The citations document carries schemaVersion 2. Against version 1: warnings[] entries
  are objects ({@type, class, severity, message}) rather than bare strings, and a
  snapshots[] chain records each run's document hash against the previous one. The
  citations[] array and the per-citation FNV-1a hashes are unchanged -- those are what
  parity tests, and they did not move.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import tempfile
import urllib.error
import urllib.request
from datetime import date

API = "https://mapper.unifiedcompliance.com/api/authority-document/{ad}/report"
PAGE = "https://mapper.unifiedcompliance.com/public-comment/index/{ad}"

DOC_SCHEMA_VERSION = 2

BRACE = re.compile(r"\{[^{}]*\}")
WS_RUN = re.compile(r"\s{2,}")
SPACE_BEFORE_PUNCT = re.compile(r"\s+([,.;:!?\)])")


# -------------------------------------------------------------------- warnings

# A warning class names WHAT KIND of thing went wrong; severity says how much it should
# stop a reader. Both are for sorting and filtering downstream -- the message text is
# still the thing a human reads, and every message here is byte-identical to the string
# the same condition emitted under schemaVersion 1.
#
# Severity scale, applied consistently:
#   info    the transform did something worth knowing about; nothing is wrong
#   low     a quirk of the source document, handled, no action needed
#   medium  the output is usable but a human should look at this before publishing
#   high    the output may misrepresent the document; do not publish without resolving
SEVERITIES = ("info", "low", "medium", "high")

W_SCHEMA_DEVIATION = "schema-deviation"
W_EMPTY_DOCUMENT = "empty-document"
W_SORT_UNSAFE = "sort-unsafe"
W_MALFORMED_MARKUP = "malformed-markup"
W_NESTED_BRACE = "nested-brace-markup"
W_OUTPUT_CONVENTION = "output-convention"
W_REFERENCE_COLLISION = "reference-collision"
W_ORPHAN_PARENT = "orphan-parent"
W_SELF_PARENT = "self-parent"
W_PARENT_CYCLE = "parent-cycle"
W_COUNT_RECONCILIATION = "count-reconciliation"
W_UNREACHABLE = "unreachable-citation"
W_NO_ROOTS = "no-roots"
W_EDITION_DRIFT = "edition-drift"


def warn(sink: list, cls: str, severity: str, message: str) -> None:
    """Append one structured warning. Message text is the human-facing part."""
    assert severity in SEVERITIES, f"unknown severity {severity!r}"
    sink.append({
        "@type": "Warning",
        "class": cls,
        "severity": severity,
        "message": message,
    })


def has_class(sink: list, cls: str) -> bool:
    return any(w.get("class") == cls for w in sink)


def warning_messages(sink: list) -> list:
    return [w["message"] for w in sink]


# --------------------------------------------------------------------------- io

def fetch(ad_id: str, dest: str, attempts: int = 2) -> dict:
    """Fetch the report JSON. At most `attempts` tries, then halt -- never spin."""
    url = API.format(ad=ad_id)
    last = None
    for n in range(1, attempts + 1):
        try:
            req = urllib.request.Request(url, headers={"Accept": "application/json"})
            with urllib.request.urlopen(req, timeout=120) as resp:
                if resp.status != 200:
                    last = f"HTTP {resp.status}"
                    continue
                body = resp.read()
            with open(dest, "wb") as fh:
                fh.write(body)
            return json.loads(body.decode("utf-8"))
        except urllib.error.HTTPError as exc:
            last = f"HTTP {exc.code}"
        except (urllib.error.URLError, TimeoutError) as exc:
            last = f"network: {exc}"
        except json.JSONDecodeError as exc:
            halt(f"malformed JSON from {url}: {exc}")
    halt(f"could not fetch {url} after {attempts} attempts ({last})")


def halt(msg: str) -> None:
    print(f"HALT: {msg}", file=sys.stderr)
    sys.exit(1)


def atomic_write(path: str, text: str) -> None:
    """Write to a temp name in the same directory, then rename over the target."""
    folder = os.path.dirname(os.path.abspath(path)) or "."
    os.makedirs(folder, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=folder, prefix=".tmp-", suffix=".part")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(text)
        os.replace(tmp, path)
    except BaseException:
        if os.path.exists(tmp):
            os.unlink(tmp)
        raise


# ------------------------------------------------------------------ recon + text

def doc_citations(doc: dict) -> list:
    for key in ("citations", "Citations"):
        if isinstance(doc.get(key), list):
            return doc[key]
    return []


def recon(doc: dict) -> tuple[list, list]:
    """Report what the document actually looks like. Returns (report, warnings)."""
    report, warnings = [], []
    cites = doc_citations(doc)

    report.append(f"published_name : {doc.get('published_name')!r}")
    report.append(f"id             : {doc.get('id')!r}")
    report.append(f"originator     : {doc.get('originator')!r}")
    stats = (doc.get("stats") or {}).get("citations")
    report.append(f"stats.citations: {stats!r}")
    report.append(f"citations[] len: {len(cites)}")

    for field in ("published_name", "id"):
        if not doc.get(field):
            warn(warnings, W_SCHEMA_DEVIATION, "high",
                 f"document header is missing {field!r} -- schema deviates from the expected shape")
    if stats is None:
        warn(warnings, W_SCHEMA_DEVIATION, "medium",
             "stats.citations is absent -- the count reconciliation in validation cannot run")

    if not cites:
        warn(warnings, W_EMPTY_DOCUMENT, "high",
             "citations[] is empty -- emitting a valid document with no citations rather than inventing content")
        return report, warnings

    required = ("id", "reference", "guidance", "sort_id", "sort_value", "genealogy", "parent")
    missing = sorted({f for c in cites for f in required if f not in c})
    if missing:
        warn(warnings, W_SCHEMA_DEVIATION, "high",
             f"citations are missing expected field(s): {', '.join(missing)} -- adapt deliberately before trusting the transform")

    widths, ragged = set(), []
    for c in cites:
        sid = str(c.get("sort_id") or "")
        for seg in sid.split():
            widths.add(len(seg))
            if seg and not seg.isdigit():
                ragged.append(sid)
    if len(widths) > 1:
        warn(warnings, W_SORT_UNSAFE, "high",
             f"sort_id segments are NOT fixed-width (widths seen: {sorted(widths)}) -- "
             "a lexicographic sort would be unsafe here, so this document was ordered by a "
             "segment-wise NUMERIC sort instead; the ordering is sound, but the document's "
             "own sort_id convention is irregular and worth knowing about")
    if ragged:
        warn(warnings, W_SORT_UNSAFE, "high",
             f"sort_id contains non-numeric segments (e.g. {ragged[0]!r}) -- zero-pad assumption does not hold")

    depths = sorted({len(str(c.get('sort_id') or '').split()) for c in cites})
    report.append(f"sort_id depths : {depths}")
    report.append(f"sort_id widths : {sorted(widths)}")
    report.append("")
    report.append("Sample citations spanning depths:")
    seen_depth = set()
    for c in sorted(cites, key=lambda x: str(x.get("sort_id") or "")):
        d = len(str(c.get("sort_id") or "").split())
        if d in seen_depth or len(seen_depth) >= 5:
            continue
        seen_depth.add(d)
        parent = c.get("parent")
        pid = parent.get("id") if isinstance(parent, dict) else parent
        report.append(
            f"  depth {d}: id={c.get('id')!r} sort_id={c.get('sort_id')!r} "
            f"parent={pid!r} genealogy={c.get('genealogy')!r}"
        )
        report.append(f"           reference={str(c.get('reference'))[:70]!r}")
        report.append(f"           guidance ={str(c.get('guidance'))[:70]!r}")
    return report, warnings


def clean_guidance(text, warnings: list) -> str:
    """Brace spans out, then collapse runs of 2+ whitespace, then tighten punctuation."""
    if not text:
        return ""
    out, passes = str(text), 0
    while True:
        stripped = BRACE.sub("", out)
        if stripped == out:
            break
        out, passes = stripped, passes + 1
        if passes > 20:
            warn(warnings, W_MALFORMED_MARKUP, "medium",
                 "guidance brace-stripping exceeded 20 passes -- possible malformed markup, stopped early")
            break
    # Emitted once per document, not once per citation. Through 0.2.1 the guard was a
    # substring scan over the joined warning text, which happened to work only because the
    # message contains the word it was scanning for. The class check says what was meant.
    if passes > 1 and not has_class(warnings, W_NESTED_BRACE):
        warn(warnings, W_NESTED_BRACE, "low",
             "nested-brace guidance markup found; brace removal ran more than one pass "
             "(the literal single-pass reading of the rule would have left residue)")
    out = WS_RUN.sub(" ", out)
    out = SPACE_BEFORE_PUNCT.sub(r"\1", out)
    return out.strip()


# -------------------------------------------------------------------- transform

def norm_id(value) -> str:
    return "" if value is None else str(value)


def parent_id_of(c: dict) -> str:
    p = c.get("parent")
    if isinstance(p, dict):
        return norm_id(p.get("id"))
    return norm_id(p)


def pad_width(cites: list, default: int = 12) -> int:
    """Infer the zero-pad width used by the API's own genealogy strings."""
    widths = {len(seg) for c in cites for seg in str(c.get("genealogy") or "").split() if seg}
    if len(widths) == 1:
        return widths.pop()
    return max(widths) if widths else default


def fnv1a(text: str) -> str:
    h = 0x811C9DC5
    for byte in text.encode("utf-8"):
        h ^= byte
        h = (h * 0x01000193) & 0xFFFFFFFF
    return f"{h:08x}"


def transform(doc: dict, ad_id: str) -> tuple[dict, list, dict]:
    """Returns (payload_without_bibtex, warnings, meta).

    meta["hashes"] is keyed by elementId, never by reference -- see the guard below.
    """
    warnings: list = []
    report, recon_warnings = recon(doc)
    warnings.extend(recon_warnings)

    raw = doc_citations(doc)
    width = pad_width(raw)
    if raw:
        warn(warnings, W_OUTPUT_CONVENTION, "info",
             "output genealogy is the full survivor chain root-first INCLUDING this citation, which "
             "deliberately differs from the API's own genealogy field (ancestors only, except roots which "
             "list themselves); the two fields are not interchangeable")

    # Rule 2 -- sort by (sort_id, id), SEGMENT-WISE NUMERIC.
    #
    # This is identical to the lexicographic sort it replaces whenever segments
    # are fixed-width zero-padded ("001" < "002" and (1,) < (2,) agree, and so
    # do "001 002" < "001 010" and (1,2) < (1,10)), so every document that
    # passes the recon check sorts exactly as before. It differs only where the
    # lexicographic sort was already unsound: AD 4518 (Apptega Common Controls)
    # runs its single segment past 999 into four digits, where "1000" < "999"
    # lexicographically and control 1000 lists before control 999. The skill's
    # rule is that a document whose sort_id isn't fixed-width needs a different
    # sort rather than a warning and a shrug; this is that sort. A non-numeric
    # segment falls back to its string, which still groups sensibly and is
    # still reported by the sort-unsafe warning.
    def _sort_key(c):
        segs = str(c.get("sort_id") or "").split()
        return ([(0, int(sg), "") if sg.isdigit() else (1, 0, sg) for sg in segs],
                norm_id(c.get("id")).zfill(24))
    ordered = sorted(raw, key=_sort_key)

    # Rule 3 -- dedupe by reference, but only when the rows are genuinely identical.
    # by_reference holds EVERY surviving variant of a reference, not just the first one seen.
    # A row has to be tested against all of them: once one genuine collision has been recorded,
    # comparing later rows only against the first survivor means true duplicates arriving after
    # that collision are never merged. ISO/IEC 27002:2022 (AD 4501) is the live case -- the
    # reference '§ 5.17 Control' carries a section-heading row plus two body rows identical to
    # each other, and testing both bodies only against the heading kept both, inflating the
    # count past stats.citations and stranding one of them outside the tree as unreachable.
    survivors: list = []
    by_reference: dict = {}
    remap: dict = {}
    for c in ordered:
        cid = norm_id(c.get("id"))
        ref = str(c.get("reference") or "")
        _pid = parent_id_of(c)
        # The API's genealogy field lists ancestors only, EXCEPT for roots, which list
        # themselves. So for a root the field is a restatement of its own id, and two
        # distinct rows always carry distinct ids: including it here makes the identity
        # test unconditionally false for every root pair, and rule 3 can never merge the
        # API's repeated mandate rows in a flat document. AD 4565 (NERC CIP-003-9) is the
        # live case -- 95 rows, all parent=None, 15 references repeated, every repeat
        # byte-identical in cleaned guidance, and the count came out 95 against
        # stats.citations 75 with 15 false collision warnings. Dropping a tautologically
        # unequal term is not loosening the test; guidance and parent still have to match.
        identity = (
            clean_guidance(c.get("guidance"), warnings),
            _pid,
            str(c.get("genealogy") or "") if _pid else "",
        )
        variants = by_reference.setdefault(ref, [])
        twin = next((v for v in variants if v["identity"] == identity), None)
        if twin is not None:
            twin["merged"].append(cid)
            remap[cid] = twin["id"]           # keep parent links valid
            continue
        if variants:
            # Differs from every variant seen so far. Keep it -- never force-merge to hit
            # stats.citations. Field names are reported against the first variant.
            differs = [
                name for name, a, b in zip(("guidance", "parent", "genealogy"), variants[0]["identity"], identity)
                if a != b
            ]
            warn(warnings, W_REFERENCE_COLLISION, "medium",
                 f"reference {ref!r} now carries {len(variants) + 1} distinct citations "
                 f"(rows {', '.join(v['id'] for v in variants)} and {cid}); row {cid} differs from every "
                 f"prior variant (against the first: {', '.join(differs)}); all kept rather than merged")
        entry = {"id": cid, "raw": c, "identity": identity, "merged": []}
        variants.append(entry)
        survivors.append(entry)
        remap[cid] = cid

    survivor_ids = {e["id"] for e in survivors}
    by_id = {e["id"]: e for e in survivors}

    # Resolve each survivor's parent through the remap.
    resolved_parent: dict = {}
    for e in survivors:
        praw = parent_id_of(e["raw"])
        if not praw:
            resolved_parent[e["id"]] = None
            continue
        target = remap.get(praw)
        if target is None or target not in survivor_ids:
            warn(warnings, W_ORPHAN_PARENT, "high",
                 f"citation {e['id']} ({e['identity'][0][:40]!r}...) has parent id {praw!r} that resolves to no "
                 "surviving citation; the link was excluded and this citation is treated as a root")
            resolved_parent[e["id"]] = None
        elif target == e["id"]:
            warn(warnings, W_SELF_PARENT, "high",
                 f"citation {e['id']} is its own parent after remapping; self-link excluded")
            resolved_parent[e["id"]] = None
        else:
            resolved_parent[e["id"]] = target

    # Rule 5/6 -- ancestor chains with a cycle guard.
    def chain(cid: str) -> list:
        out, seen, cur = [], {cid}, resolved_parent.get(cid)
        while cur:
            if cur in seen:
                warn(warnings, W_PARENT_CYCLE, "high",
                     f"parent chain from citation {cid} revisits id {cur}; the walk was stopped and the cycle excluded")
                break
            seen.add(cur)
            out.append(cur)
            cur = resolved_parent.get(cur)
        out.reverse()                      # root first
        return out

    # Every survivor with a resolved parent is a child of that parent. Through 0.2.1 this
    # loop also deduped children by reference, which contradicted rule 3: rule 3 keeps two
    # rows sharing a reference precisely BECAUSE they are genuinely distinct, and then this
    # filter dropped the second one from its parent's child list, stranding it outside the
    # tree and raising the unreachable-citation warning on a document that was in fact fine.
    # AD 4559 (OMB Circular A-123) is the live case -- 'II. B. ¶ 2 3.' carries both
    # 'Risk Oversight and Assessment' and 'Control Activities' under parent 908424, the
    # count reconciled at 197 against stats.citations 197, and one of the two was reachable
    # from no root. Survivors are already unique by (reference, identity); deduping them
    # again here can only lose data.
    children: dict = {e["id"]: [] for e in survivors}
    for e in survivors:
        p = resolved_parent[e["id"]]
        if p is None:
            continue
        children[p].append(e["id"])

    citations, hashes, labels = [], {}, {}
    for e in survivors:
        cid = e["id"]
        raw_c = e["raw"]
        ref = str(raw_c.get("reference") or "")
        guidance = e["identity"][0]
        ancestors = chain(cid)
        genealogy = [i.zfill(width) for i in ancestors + [cid]]
        parents = [
            {"@type": "Parent", "elementId": a, "reference": str(by_id[a]["raw"].get("reference") or "")}
            for a in ancestors
        ]
        kids = [
            {"@type": "Child", "elementId": k, "reference": str(by_id[k]["raw"].get("reference") or "")}
            for k in children[cid]
        ]
        sort_value = str(raw_c.get("sort_id") or "")
        citations.append({
            "reference": ref,
            "guidance": guidance,
            "hierarchy": {
                "@type": "HierarchyItem",
                "schemaVersion": 1,
                "@id": f"{PAGE.format(ad=ad_id)}#citation-{cid}",
                "elementId": cid,
                "parents": parents,
                "children": kids,
                "sortValue": sort_value,
                "genealogy": genealogy,
            },
        })
        # Hash covers hierarchy shape, not just text. Must match the JS side exactly.
        # Keyed by elementId, NOT by reference. Rule 3 deliberately keeps two citations
        # that share a reference when they differ in guidance, parent or genealogy, so a
        # reference-keyed manifest overwrites one of them and drops it from the parity
        # diff entirely -- a silent hole, since the surviving key still compares clean.
        # AD 4509 (Australian Government ISM) is the live case: 'Personnel awareness'
        # appears under both Telephone systems and Mobile device usage, and the manifest
        # carried 1911 keys for 1912 citations.
        hashes[cid] = fnv1a(
            ref + guidance + ",".join(ancestors) + sort_value + ",".join(genealogy) + str(len(kids))
        )
        labels[cid] = ref

    # Validation.
    # The manifest must cover every citation exactly once, or the parity check in --parity
    # is testing a subset while reporting a clean bill. This is an invariant of the keying
    # above, not a document property, so a violation is a bug in this script -- halt.
    if len(hashes) != len(citations):
        halt(
            f"hash manifest covers {len(hashes)} of {len(citations)} citations; the parity "
            "check would silently skip the remainder. This is a keying bug, not a data problem."
        )

    stats = (doc.get("stats") or {}).get("citations")
    if stats is not None and len(citations) != stats:
        conflicting = [e["id"] for e in survivors if e["merged"]][:20]
        warn(warnings, W_COUNT_RECONCILIATION, "high",
             f"unique-citation count {len(citations)} does not match stats.citations {stats}; "
             f"merged-row survivors sampled: {conflicting}")
    roots = [e["id"] for e in survivors if resolved_parent[e["id"]] is None]
    reachable, stack = set(), list(roots)
    while stack:
        cur = stack.pop()
        if cur in reachable:
            continue
        reachable.add(cur)
        stack.extend(children[cur])
    unreachable = sorted(survivor_ids - reachable)
    if unreachable:
        warn(warnings, W_UNREACHABLE, "high",
             f"{len(unreachable)} citation(s) unreachable from any root, e.g. {unreachable[:10]}")
    if survivors and not roots:
        warn(warnings, W_NO_ROOTS, "high",
             "no root citations found -- every citation claims a parent, which should be impossible")

    payload = {
        "title": doc.get("published_name") or "",
        # The mapper's own Document URL. This is the field the public Comment Report page
        # renders as "Document URL" -- its controller loads the same
        # /api/authority-document/{id}/report endpoint we do and binds {{ad.url}} -- so it
        # is carried here verbatim rather than scraped off an Angular page. It is the
        # PUBLISHER'S url as the mapper holds it, which is not the same claim as
        # bibTexCitation.url: that one is the official URL an agent found and live-verified
        # under step 4, and the two can legitimately differ or disagree. Keep both.
        "documentUrl": doc.get("url") or "",
        "warnings": warnings,
        "citations": citations,
    }
    meta = {
        "hashes": hashes,
        "labels": labels,
        "roots": len(roots),
        "stats": stats,
        "count": len(citations),
        "report": report,
        "originator": doc.get("originator"),
        "documentHash": document_hash(payload["title"], hashes),
    }
    return payload, warnings, meta


# ------------------------------------------------------------------- snapshots

def document_hash(title: str, hashes: dict) -> str:
    """One hash standing for the whole document, derived from the parity manifest.

    Deliberately built from `hashes` rather than from the emitted JSON: that manifest is
    exactly what --parity compares, so a document hash that agrees between two runs is the
    same claim the parity check makes, carried forward past the end of the run. Hashing the
    serialized file instead would also move when a warning message or a schema field
    changed, which would make the chain report drift that is ours, not the publisher's.

    sha256 rather than the FNV-1a used per citation: those must match a JavaScript
    implementation byte for byte, this one only has to be hard to collide.
    """
    canon = "\n".join(f"{cid}:{hashes[cid]}" for cid in sorted(hashes))
    return hashlib.sha256(f"{title}\n{len(hashes)}\n{canon}".encode("utf-8")).hexdigest()


def prior_snapshots(json_path: str) -> list:
    """Read the snapshot chain off an existing artifact. Absent or unreadable -> empty.

    A malformed prior file must not take down a fresh extraction, so this never halts; the
    worst case is a chain that restarts, which the drift check reports as a first snapshot
    rather than as silence.
    """
    if not os.path.exists(json_path):
        return []
    try:
        with open(json_path, encoding="utf-8") as fh:
            prior = json.load(fh)
    except (json.JSONDecodeError, OSError):
        return []
    snaps = prior.get("snapshots")
    return snaps if isinstance(snaps, list) else []


def extend_chain(snapshots: list, doc_hash: str, count: int, warnings: list, today: str) -> list:
    """Append this run to the chain, warning if the text moved under a stable AD id.

    The file is per AD id and the mapper mints a new AD id per edition, so both ends of a
    link in this chain are the same edition by construction. A hash that moves therefore
    means the publisher edited a published edition in place -- which is the whole reason
    the chain is worth keeping. See DR-002.
    """
    previous = snapshots[-1].get("documentHash") if snapshots else None
    drifted = previous is not None and previous != doc_hash
    if drifted:
        warn(warnings, W_EDITION_DRIFT, "high",
             f"document hash changed from {previous[:12]}... to {doc_hash[:12]}... since the previous "
             f"snapshot ({snapshots[-1].get('runDate')}); the AD id is unchanged, so the publisher edited "
             "a published edition in place rather than issuing a new one -- diff before republishing")
    return snapshots + [{
        "@type": "Snapshot",
        "schemaVersion": 1,
        "runDate": today,
        "documentHash": doc_hash,
        "previousHash": previous,
        "drifted": drifted,
        "citationCount": count,
    }]


# ------------------------------------------------------------------------- html

HTML = """<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>__TITLE__</title>
<style>
 :root{color-scheme:light dark}
 body{font:15px/1.55 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif;margin:0;padding:2rem;
      max-width:70rem;margin-inline:auto;background:Canvas;color:CanvasText}
 h1{font-size:1.4rem;margin:0 0 .25rem}
 .sub{opacity:.7;font-size:.85rem;margin-bottom:1.25rem}
 .bar{display:flex;gap:.5rem;margin-bottom:1rem}
 button{font:inherit;padding:.35rem .8rem;border:1px solid rgba(128,128,128,.45);border-radius:.4rem;
        background:transparent;color:inherit;cursor:pointer}
 button:hover{background:rgba(128,128,128,.14)}
 details{margin:.15rem 0}
 summary{cursor:pointer;padding:.2rem 0}
 .ref{font-weight:650;color:#1f6feb}
 @media (prefers-color-scheme:dark){.ref{color:#6ea8ff}}
 .count{opacity:.55;font-size:.8rem;margin-left:.4rem}
 .guid{opacity:.92}
 .node{border-left:1px solid rgba(128,128,128,.3);margin-left:.55rem;padding-left:.85rem}
 .leaf{padding:.2rem 0}
 .warn{border:1px solid #d29922;border-radius:.5rem;padding:.6rem .9rem;margin-bottom:1.25rem;font-size:.87rem}
 .warn b{display:block;margin-bottom:.3rem}
 .warn li{margin:.15rem 0}
 .wtag{font-size:.72rem;text-transform:uppercase;letter-spacing:.04em;padding:.05rem .35rem;
       border:1px solid currentColor;border-radius:.25rem;opacity:.8;white-space:nowrap}
 .wsev-high{color:#d1242f}
 .wsev-medium{color:#bf8700}
 .wsev-low,.wsev-info,.wsev-none{opacity:.55}
 @media (prefers-color-scheme:dark){.wsev-high{color:#ff8182}.wsev-medium{color:#d4a72c}}
</style></head><body>
<h1 id="t"></h1>
<div class="sub" id="s"></div>
<div id="w"></div>
<div class="bar"><button id="ex">Expand all</button><button id="co">Collapse all</button></div>
<div id="tree"></div>
<script id="data" type="application/json">__JSON__</script>
<script>
(function(){
  var DATA = JSON.parse(document.getElementById('data').textContent);
  // Guard (a): everything user-controlled goes through textContent, never innerHTML.
  function esc(s){ var d=document.createElement('div'); d.textContent = s==null?'':String(s); return d.innerHTML; }

  var byId={}, kids={}, roots=[];
  DATA.citations.forEach(function(c){
    var h=c.hierarchy; byId[h.elementId]=c;
    var p=h.parents.length? h.parents[h.parents.length-1].elementId : null;
    if(p===null){ roots.push(h.elementId); } else { (kids[p]=kids[p]||[]).push(h.elementId); }
  });

  function row(c){
    var h=c.hierarchy, n=(kids[h.elementId]||[]).length;
    var head='<span class="ref">'+esc(c.reference)+'</span>'+(n?'<span class="count">'+n+'</span>':'')
           + ' <span class="guid">'+esc(c.guidance)+'</span>';
    if(!n){ var d=document.createElement('div'); d.className='leaf'; d.innerHTML=head; return d; }
    var det=document.createElement('details');
    var sum=document.createElement('summary'); sum.innerHTML=head; det.appendChild(sum);
    var box=document.createElement('div'); box.className='node';
    kids[h.elementId].forEach(function(k){ box.appendChild(row(byId[k])); });
    det.appendChild(box); return det;
  }

  document.getElementById('t').textContent = DATA.title||'(untitled)';
  document.getElementById('s').textContent = DATA.citations.length+' citations · '+roots.length+' root'+(roots.length===1?'':'s');
  if(DATA.warnings && DATA.warnings.length){
    // schemaVersion 1 emitted bare strings here, 2 emits {class, severity, message}.
    // Both render: an artifact produced before the taxonomy still opens correctly.
    var RANK={high:0,medium:1,low:2,info:3};
    var ws=DATA.warnings.map(function(x){
      return (typeof x==='string') ? {severity:'', cls:'', message:x}
                                   : {severity:x.severity||'', cls:x['class']||'', message:x.message||''};
    }).sort(function(a,b){
      var ra=(a.severity in RANK)?RANK[a.severity]:9, rb=(b.severity in RANK)?RANK[b.severity]:9;
      return ra-rb;
    });
    var w=document.getElementById('w'), box=document.createElement('div'); box.className='warn';
    var b=document.createElement('b'); b.textContent='Warnings ('+ws.length+')'; box.appendChild(b);
    var ul=document.createElement('ul');
    ws.forEach(function(x){
      var li=document.createElement('li');
      if(x.severity||x.cls){
        var tag=document.createElement('span');
        tag.className='wtag wsev-'+(x.severity||'none');
        tag.textContent=x.severity+(x.cls?(' / '+x.cls):'');
        li.appendChild(tag); li.appendChild(document.createTextNode(' '));
      }
      li.appendChild(document.createTextNode(x.message));
      ul.appendChild(li);
    });
    box.appendChild(ul); w.appendChild(box);
  }
  var tree=document.getElementById('tree');
  roots.forEach(function(r){ tree.appendChild(row(byId[r])); });
  document.getElementById('ex').onclick=function(){ document.querySelectorAll('details').forEach(function(d){d.open=true;}); };
  document.getElementById('co').onclick=function(){ document.querySelectorAll('details').forEach(function(d){d.open=false;}); };
})();
</script></body></html>
"""


def render_html(payload: dict, ad_id: str) -> str:
    # Guard (b): a guidance string containing </script> would otherwise close the block.
    blob = json.dumps(payload, ensure_ascii=False).replace("</", "<\\/")
    title = (payload.get("title") or f"Authority Document {ad_id}")
    safe_title = title.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    return HTML.replace("__TITLE__", safe_title).replace("__JSON__", blob)


# ------------------------------------------------------------------------- main

def print_warnings(warnings: list) -> None:
    """Highest severity first, so the thing that should stop a publish reads first."""
    rank = {s: i for i, s in enumerate(reversed(SEVERITIES))}
    for w in sorted(warnings, key=lambda x: rank.get(x.get("severity"), len(SEVERITIES))):
        print(f"  - [{w['severity']}/{w['class']}] {w['message']}")


def load_raw(path: str) -> dict:
    try:
        with open(path, encoding="utf-8") as fh:
            return json.load(fh)
    except json.JSONDecodeError as exc:
        halt(f"malformed JSON in {path}: {exc}")
    except OSError as exc:
        halt(f"cannot read {path}: {exc}")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--ad", required=True, help="Authority Document id, e.g. 4524")
    ap.add_argument("--out", help="output folder (required unless --recon or --parity)")
    ap.add_argument("--raw", help="use this already-fetched JSON instead of fetching")
    ap.add_argument("--bibtex", help="JSON file holding the BibTexCitation object to embed")
    ap.add_argument("--recon", action="store_true", help="schema reconnaissance only, no files written")
    ap.add_argument("--parity", help="second independently fetched raw JSON to diff against --raw")
    ap.add_argument("--today", help="override the snapshot run date (ISO 8601); for tests and backfills")
    args = ap.parse_args()

    scratch = args.raw or os.path.join(tempfile.gettempdir(), f"ad{args.ad}.json")
    doc = load_raw(args.raw) if args.raw else fetch(args.ad, scratch)

    if args.recon:
        report, warnings = recon(doc)
        print("\n".join(report))
        print("\nWarnings:" if warnings else "\nWarnings: none")
        print_warnings(warnings)
        print(f"\nraw JSON cached at: {scratch}")
        return

    payload, warnings, meta = transform(doc, args.ad)

    if args.parity:
        other_payload, _, other_meta = transform(load_raw(args.parity), args.ad)
        a, b = meta["hashes"], other_meta["hashes"]
        names = {**other_meta["labels"], **meta["labels"]}

        def show(ids: list) -> list:
            """elementIds alone are unreadable in a diff; carry the reference alongside."""
            return [f"{i} ({names.get(i, '?')})" for i in ids[:5]]

        missing = sorted(set(a) - set(b))
        extra = sorted(set(b) - set(a))
        mismatch = sorted(k for k in set(a) & set(b) if a[k] != b[k])
        # Asserted independently of the hashes: equal citation counts on both sides, and
        # full manifest coverage on both. Hash agreement over a short manifest is not parity.
        counts_differ = meta["count"] != other_meta["count"]
        coverage = (len(a) == meta["count"] and len(b) == other_meta["count"])

        print(f"counts      : build={meta['count']} parity={other_meta['count']} stats={meta['stats']}")
        print(f"coverage    : {len(a)}/{meta['count']} build, {len(b)}/{other_meta['count']} parity")
        print(f"missing     : {len(missing)} {show(missing)}")
        print(f"extra       : {len(extra)} {show(extra)}")
        print(f"content diff: {len(mismatch)} {show(mismatch)}")
        if counts_differ:
            print(f"COUNT MISMATCH: {meta['count']} vs {other_meta['count']}", file=sys.stderr)
        if not coverage:
            print("MANIFEST DOES NOT COVER EVERY CITATION", file=sys.stderr)
        if missing or extra or mismatch or counts_differ or not coverage:
            print("PARITY FAIL", file=sys.stderr)
            sys.exit(2)
        print("PARITY OK (0/0/0)")
        return

    if not args.out:
        halt("--out is required for a full run")

    bib = None
    if args.bibtex:
        bib = load_raw(args.bibtex)

    json_path = os.path.join(args.out, f"ad-{args.ad}-citations.json")
    html_path = os.path.join(args.out, f"ad-{args.ad}-hierarchy.html")

    # Read the prior artifact BEFORE writing over it. This is the one place the run is not
    # a pure function of its input: the chain needs the previous link, and the previous
    # link lives in the file we are about to replace.
    snapshots = extend_chain(
        prior_snapshots(json_path), meta["documentHash"], meta["count"],
        warnings, args.today or date.today().isoformat(),
    )

    ordered = {"schemaVersion": DOC_SCHEMA_VERSION,
               "title": payload["title"], "documentUrl": payload["documentUrl"],
               "bibTexCitation": bib,
               "warnings": payload["warnings"], "snapshots": snapshots,
               "citations": payload["citations"]}

    atomic_write(json_path, json.dumps(ordered, indent=2, ensure_ascii=False) + "\n")
    atomic_write(html_path, render_html(ordered, args.ad))

    print("\n".join(meta["report"]))
    print(f"\ncitations   : {meta['count']} (stats.citations={meta['stats']})")
    print(f"roots       : {meta['roots']}")
    print(f"originator  : {meta['originator']!r}")
    print(f"doc hash    : {meta['documentHash']}")
    prev = snapshots[-1]["previousHash"]
    if prev is None:
        print(f"snapshots   : {len(snapshots)} (first snapshot of this AD id)")
    elif snapshots[-1]["drifted"]:
        print(f"snapshots   : {len(snapshots)} -- DRIFTED from {prev[:12]}...")
    else:
        print(f"snapshots   : {len(snapshots)} (unchanged since {snapshots[-2]['runDate']})")
    print(f"warnings    : {len(warnings)}")
    print_warnings(warnings)
    print(f"\nwrote {json_path}")
    print(f"wrote {html_path}")
    print(f"raw JSON cached at: {scratch}")
    if bib is None:
        print("\nNOTE: bibTexCitation is null -- rerun with --bibtex once the entry is built.")
    print(f"\nhash manifest ({len(meta['hashes'])} citations, keyed by elementId) for the parity pass:")
    print(json.dumps(meta["hashes"], indent=0, sort_keys=True))


if __name__ == "__main__":
    main()
