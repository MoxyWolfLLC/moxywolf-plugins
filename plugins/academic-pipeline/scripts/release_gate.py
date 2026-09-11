#!/usr/bin/env python3
"""Mechanical release gate for the academic pipeline (AP-003).

Runs the checks that were previously remembered rather than executed, and names
each one with its result. A failing gate blocks the completion report.

  python3 release_gate.py --paper <paper.md> --requirements <formatting_requirements.json>

Exit 0 when every check passes, 1 when any fails, 2 on a usage error.
ponytail: stdlib only, one file; the renumber pass is reused rather than reimplemented.
"""
import argparse, json, os, re, subprocess, sys, unicodedata

HERE = os.path.dirname(os.path.abspath(__file__))
RENUMBER = os.path.join(HERE, "..", "skills", "bibliography-generator", "scripts", "renumber_citations.py")

# Entries in section_order that are document metadata rather than headings.
DEFAULT_EXEMPT = {"citation"}


def _norm(s):
    s = unicodedata.normalize("NFKC", s).lower().strip()
    s = re.sub(r"^\d+(\.\d+)*\.?\s*", "", s)      # drop a leading section number
    return re.sub(r"[^a-z0-9]+", " ", s).strip()


def check_em_dashes(paper, _req):
    hits = [i for i, l in enumerate(paper.splitlines(), 1) if "—" in l]
    return (not hits), f"{len(hits)} em dash(es)" + (f" at line(s) {hits[:5]}" if hits else "")


def check_forbidden_phrases(paper, req):
    phrases = req.get("moxywolf_constraints", {}).get("forbidden_phrases", [])
    low = paper.lower()
    found = sorted({p for p in phrases if p.lower() in low})
    return (not found), (f"{len(found)} forbidden phrase(s): {found}" if found else "0 forbidden phrases")


def check_sections_present(paper, req):
    order = req.get("academic_requirements", {}).get("section_order", [])
    exempt = {_norm(x) for x in req.get("academic_requirements", {}).get("gate_exempt_sections", [])} | DEFAULT_EXEMPT
    present = set()
    for line in paper.splitlines():
        m = re.match(r"\s*#{1,4}\s+(.*)", line) or re.match(r"\s*\*\*(.+?)\*\*\s*:?\s*$", line)
        if m:
            present.add(_norm(m.group(1)))
    missing = [s for s in order if _norm(s) not in exempt and not any(
        _norm(s) == p or p.startswith(_norm(s)) or _norm(s).startswith(p) for p in present if p)]
    return (not missing), (f"{len(missing)} missing: {missing}" if missing else f"all {len(order)} present")


def check_duplicate_sources(paper, _req):
    """Two reference entries pointing at one work. Dedupe on normalized DOI/URL, not on key."""
    refs = re.split(r"^#{1,3}\s*References\s*$", paper, flags=re.M | re.I)
    body = refs[-1] if len(refs) > 1 else ""
    seen, dupes = {}, []
    for m in re.finditer(r"^(\d+)\.\s+(.*)$", body, flags=re.M):
        num, text = m.group(1), m.group(2)
        link = re.search(r"https?://\S+", text)
        if not link:
            continue
        key = re.sub(r"^https?://(www\.)?", "", link.group(0).rstrip(".,);")).rstrip("/").lower()
        key = re.sub(r"^doi\.org/", "", key)
        if key in seen:
            dupes.append(f"[{seen[key]}] and [{num}] share {key}")
        else:
            seen[key] = num
    return (not dupes), (f"{len(dupes)} duplicate source(s): {dupes}" if dupes else f"{len(seen)} unique sources")


def check_citation_order(paper_path, req):
    if req.get("academic_requirements", {}).get("citation_style", "").lower() != "vancouver":
        return True, "not Vancouver, no numbering to check"
    if not os.path.exists(RENUMBER):
        return False, "renumber_citations.py not found; citation order unverified"
    r = subprocess.run([sys.executable, RENUMBER, paper_path, "--check"], capture_output=True, text=True)
    return r.returncode == 0, (r.stdout or r.stderr).strip().splitlines()[-1] if (r.stdout or r.stderr) else f"exit {r.returncode}"


def run_gate(paper_path, requirements_path):
    with open(paper_path, encoding="utf-8") as fh:
        paper = fh.read()
    with open(requirements_path, encoding="utf-8") as fh:
        req = json.load(fh)
    results = [
        ("em_dashes", *check_em_dashes(paper, req)),
        ("forbidden_phrases", *check_forbidden_phrases(paper, req)),
        ("sections_present", *check_sections_present(paper, req)),
        ("duplicate_sources", *check_duplicate_sources(paper, req)),
        ("citation_order", *check_citation_order(paper_path, req)),
    ]
    return results


def main():
    ap = argparse.ArgumentParser(description="Mechanical release gate for the academic pipeline")
    ap.add_argument("--paper", required=True)
    ap.add_argument("--requirements", required=True)
    ap.add_argument("--json", action="store_true", help="emit machine-readable results")
    a = ap.parse_args()
    for p in (a.paper, a.requirements):
        if not os.path.exists(p):
            print(f"gate: no such file: {p}", file=sys.stderr); sys.exit(2)
    results = run_gate(a.paper, a.requirements)
    failed = [n for n, ok, _ in results if not ok]
    if a.json:
        print(json.dumps({"checks": [{"name": n, "pass": ok, "detail": d} for n, ok, d in results],
                          "failed": failed, "gate": "FAIL" if failed else "PASS"}, indent=2))
    else:
        print("RELEASE GATE")
        for n, ok, d in results:
            print(f"  {'PASS' if ok else 'FAIL'}  {n:<20} {d}")
        print(f"gate: {'FAIL' if failed else 'PASS'}" + (f" ({', '.join(failed)})" if failed else ""))
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
