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
"""

from __future__ import annotations

import argparse
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

BRACE = re.compile(r"\{[^{}]*\}")
WS_RUN = re.compile(r"\s{2,}")
SPACE_BEFORE_PUNCT = re.compile(r"\s+([,.;:!?\)])")


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
            warnings.append(f"document header is missing {field!r} -- schema deviates from the expected shape")
    if stats is None:
        warnings.append("stats.citations is absent -- the count reconciliation in validation cannot run")

    if not cites:
        warnings.append("citations[] is empty -- emitting a valid document with no citations rather than inventing content")
        return report, warnings

    required = ("id", "reference", "guidance", "sort_id", "sort_value", "genealogy", "parent")
    missing = sorted({f for c in cites for f in required if f not in c})
    if missing:
        warnings.append(f"citations are missing expected field(s): {', '.join(missing)} -- adapt deliberately before trusting the transform")

    widths, ragged = set(), []
    for c in cites:
        sid = str(c.get("sort_id") or "")
        for seg in sid.split():
            widths.add(len(seg))
            if seg and not seg.isdigit():
                ragged.append(sid)
    if len(widths) > 1:
        warnings.append(
            f"sort_id segments are NOT fixed-width (widths seen: {sorted(widths)}) -- "
            "lexicographic sort is unsafe on this document; the ordering below is suspect"
        )
    if ragged:
        warnings.append(f"sort_id contains non-numeric segments (e.g. {ragged[0]!r}) -- zero-pad assumption does not hold")

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
            warnings.append("guidance brace-stripping exceeded 20 passes -- possible malformed markup, stopped early")
            break
    if passes > 1 and "nested-brace" not in " ".join(warnings):
        warnings.append(
            "nested-brace guidance markup found; brace removal ran more than one pass "
            "(the literal single-pass reading of the rule would have left residue)"
        )
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
    """Returns (payload_without_bibtex, warnings, hashes_by_reference)."""
    warnings: list = []
    report, recon_warnings = recon(doc)
    warnings.extend(recon_warnings)

    raw = doc_citations(doc)
    width = pad_width(raw)
    if raw:
        warnings.append(
            "output genealogy is the full survivor chain root-first INCLUDING this citation, which "
            "deliberately differs from the API's own genealogy field (ancestors only, except roots which "
            "list themselves); the two fields are not interchangeable"
        )

    # Rule 2 -- sort by (sort_id, id). Lexicographic; only sound if recon confirmed
    # fixed-width segments, which is why a violation is warned about above.
    ordered = sorted(raw, key=lambda c: (str(c.get("sort_id") or ""), norm_id(c.get("id")).zfill(24)))

    # Rule 3 -- dedupe by reference, but only when the rows are genuinely identical.
    survivors: list = []
    by_reference: dict = {}
    remap: dict = {}
    for c in ordered:
        cid = norm_id(c.get("id"))
        ref = str(c.get("reference") or "")
        identity = (
            clean_guidance(c.get("guidance"), warnings),
            parent_id_of(c),
            str(c.get("genealogy") or ""),
        )
        prior = by_reference.get(ref)
        if prior is None:
            entry = {"id": cid, "raw": c, "identity": identity, "merged": []}
            by_reference[ref] = entry
            survivors.append(entry)
            remap[cid] = cid
        elif prior["identity"] == identity:
            prior["merged"].append(cid)
            remap[cid] = prior["id"]          # keep parent links valid
        else:
            # A real collision. Keep both -- never force-merge to hit stats.citations.
            differs = [
                name for name, a, b in zip(("guidance", "parent", "genealogy"), prior["identity"], identity) if a != b
            ]
            warnings.append(
                f"reference {ref!r} appears on rows {prior['id']} and {cid} that differ in "
                f"{', '.join(differs)}; both kept as distinct citations rather than merged"
            )
            entry = {"id": cid, "raw": c, "identity": identity, "merged": []}
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
            warnings.append(
                f"citation {e['id']} ({e['identity'][0][:40]!r}...) has parent id {praw!r} that resolves to no "
                "surviving citation; the link was excluded and this citation is treated as a root"
            )
            resolved_parent[e["id"]] = None
        elif target == e["id"]:
            warnings.append(f"citation {e['id']} is its own parent after remapping; self-link excluded")
            resolved_parent[e["id"]] = None
        else:
            resolved_parent[e["id"]] = target

    # Rule 5/6 -- ancestor chains with a cycle guard.
    def chain(cid: str) -> list:
        out, seen, cur = [], {cid}, resolved_parent.get(cid)
        while cur:
            if cur in seen:
                warnings.append(
                    f"parent chain from citation {cid} revisits id {cur}; the walk was stopped and the cycle excluded"
                )
                break
            seen.add(cur)
            out.append(cur)
            cur = resolved_parent.get(cur)
        out.reverse()                      # root first
        return out

    children: dict = {e["id"]: [] for e in survivors}
    seen_child_ref: dict = {e["id"]: set() for e in survivors}
    for e in survivors:
        p = resolved_parent[e["id"]]
        if p is None:
            continue
        ref = str(e["raw"].get("reference") or "")
        if ref in seen_child_ref[p]:
            continue                        # children unique by reference
        seen_child_ref[p].add(ref)
        children[p].append(e["id"])

    citations, hashes = [], {}
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
        hashes[ref] = fnv1a(
            ref + guidance + ",".join(ancestors) + sort_value + ",".join(genealogy) + str(len(kids))
        )

    # Validation.
    stats = (doc.get("stats") or {}).get("citations")
    if stats is not None and len(citations) != stats:
        conflicting = [e["id"] for e in survivors if e["merged"]][:20]
        warnings.append(
            f"unique-citation count {len(citations)} does not match stats.citations {stats}; "
            f"merged-row survivors sampled: {conflicting}"
        )
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
        warnings.append(f"{len(unreachable)} citation(s) unreachable from any root, e.g. {unreachable[:10]}")
    if survivors and not roots:
        warnings.append("no root citations found -- every citation claims a parent, which should be impossible")

    payload = {
        "title": doc.get("published_name") or "",
        "warnings": warnings,
        "citations": citations,
    }
    meta = {
        "hashes": hashes,
        "roots": len(roots),
        "stats": stats,
        "count": len(citations),
        "report": report,
        "originator": doc.get("originator"),
    }
    return payload, warnings, meta


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
    var w=document.getElementById('w'), box=document.createElement('div'); box.className='warn';
    var b=document.createElement('b'); b.textContent='Warnings ('+DATA.warnings.length+')'; box.appendChild(b);
    var ul=document.createElement('ul');
    DATA.warnings.forEach(function(x){ var li=document.createElement('li'); li.textContent=x; ul.appendChild(li); });
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
    args = ap.parse_args()

    scratch = args.raw or os.path.join(tempfile.gettempdir(), f"ad{args.ad}.json")
    doc = load_raw(args.raw) if args.raw else fetch(args.ad, scratch)

    if args.recon:
        report, warnings = recon(doc)
        print("\n".join(report))
        print("\nWarnings:" if warnings else "\nWarnings: none")
        for w in warnings:
            print(f"  - {w}")
        print(f"\nraw JSON cached at: {scratch}")
        return

    payload, warnings, meta = transform(doc, args.ad)

    if args.parity:
        other_payload, _, other_meta = transform(load_raw(args.parity), args.ad)
        a, b = meta["hashes"], other_meta["hashes"]
        missing = sorted(set(a) - set(b))
        extra = sorted(set(b) - set(a))
        mismatch = sorted(r for r in set(a) & set(b) if a[r] != b[r])
        print(f"counts      : build={meta['count']} parity={other_meta['count']} stats={meta['stats']}")
        print(f"missing     : {len(missing)} {missing[:5]}")
        print(f"extra       : {len(extra)} {extra[:5]}")
        print(f"content diff: {len(mismatch)} {mismatch[:5]}")
        if missing or extra or mismatch:
            print("PARITY FAIL", file=sys.stderr)
            sys.exit(2)
        print("PARITY OK (0/0/0)")
        return

    if not args.out:
        halt("--out is required for a full run")

    bib = None
    if args.bibtex:
        bib = load_raw(args.bibtex)
    ordered = {"title": payload["title"], "bibTexCitation": bib,
               "warnings": payload["warnings"], "citations": payload["citations"]}

    json_path = os.path.join(args.out, f"ad-{args.ad}-citations.json")
    html_path = os.path.join(args.out, f"ad-{args.ad}-hierarchy.html")
    atomic_write(json_path, json.dumps(ordered, indent=2, ensure_ascii=False) + "\n")
    atomic_write(html_path, render_html(ordered, args.ad))

    print("\n".join(meta["report"]))
    print(f"\ncitations   : {meta['count']} (stats.citations={meta['stats']})")
    print(f"roots       : {meta['roots']}")
    print(f"originator  : {meta['originator']!r}")
    print(f"warnings    : {len(warnings)}")
    for w in warnings:
        print(f"  - {w}")
    print(f"\nwrote {json_path}")
    print(f"wrote {html_path}")
    print(f"raw JSON cached at: {scratch}")
    if bib is None:
        print("\nNOTE: bibTexCitation is null -- rerun with --bibtex once the entry is built.")
    print(f"\nhash manifest ({len(meta['hashes'])} refs) for the parity pass:")
    print(json.dumps(meta["hashes"], indent=0, sort_keys=True))


if __name__ == "__main__":
    main()
