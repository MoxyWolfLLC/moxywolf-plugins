#!/usr/bin/env python3
"""Mechanical release gate for the academic pipeline (AP-003, hardened by EV-001).

Runs the checks that were previously remembered rather than executed, and names
each one with its result AND what it examined.

  python3 release_gate.py --paper <paper.md> --requirements <formatting_requirements.json>

Exit 0 when every applicable check passes, 1 when any fails, 2 on a usage error.

EV-001, the rule that governs every check here: a check reports what it examined,
and a check that examined nothing cannot pass. A PASS over zero input is worse
than no check at all, because a missing check leaves the reader's doubt in place
and a false pass retires it. Three of this gate's own checks shipped as false
passes of exactly that kind. So `examined` is part of every result, zero coverage
converts a PASS into a FAIL, and a check that genuinely does not apply returns
SKIP and is printed as SKIP rather than folded into a green line.

ponytail: stdlib only, one file; the renumber pass is reused rather than reimplemented.
"""
import argparse, json, os, re, subprocess, sys, unicodedata

HERE = os.path.dirname(os.path.abspath(__file__))
RENUMBER = os.path.join(HERE, "..", "skills", "bibliography-generator", "scripts", "renumber_citations.py")

PASS, FAIL, SKIP = "pass", "fail", "skip"

# Entries in section_order that are document metadata rather than headings.
DEFAULT_EXEMPT = {"citation"}


def _norm(s):
    s = unicodedata.normalize("NFKC", s).lower().strip()
    s = re.sub(r"^\d+(\.\d+)*\.?\s*", "", s)      # drop a leading section number
    return re.sub(r"[^a-z0-9]+", " ", s).strip()


def check_em_dashes(paper, _req):
    lines = [l for l in paper.splitlines() if l.strip()]
    hits = [i for i, l in enumerate(paper.splitlines(), 1) if "—" in l]
    detail = f"{len(hits)} em dash(es)" + (f" at line(s) {hits[:5]}" if hits else "")
    return (FAIL if hits else PASS), detail, len(lines), "non-empty lines"


def check_forbidden_phrases(paper, req):
    """Coverage is the size of the declared list. An empty list examines nothing:
    the paper is not clean, it is unchecked, and saying PASS would claim otherwise."""
    phrases = req.get("moxywolf_constraints", {}).get("forbidden_phrases", [])
    low = paper.lower()
    found = sorted({p for p in phrases if p.lower() in low})
    detail = f"{len(found)} forbidden phrase(s): {found}" if found else f"0 of {len(phrases)} forbidden phrases present"
    return (FAIL if found else PASS), detail, len(phrases), "declared phrases"


def check_sections_present(paper, req):
    """A required section is present only when a heading matches its name exactly after
    normalization, or matches an alias the requirements declare. Prefix matching is NOT
    used: it let 'Funding mechanisms in prior research' satisfy a required 'Funding'
    declaration, which is a false pass on the check that matters most."""
    acc = req.get("academic_requirements", {})
    order = acc.get("section_order", [])
    exempt = {_norm(x) for x in acc.get("gate_exempt_sections", [])} | DEFAULT_EXEMPT
    aliases = {_norm(k): {_norm(v) for v in vs} for k, vs in acc.get("section_aliases", {}).items()}
    present = set()
    for line in paper.splitlines():
        m = re.match(r"\s*#{1,4}\s+(.*)", line) or re.match(r"\s*\*\*(.+?)\*\*\s*:?\s*$", line)
        if m:
            present.add(_norm(m.group(1)))
    required = [s for s in order if _norm(s) not in exempt]
    missing = [s for s in required if not (_norm(s) in present or (aliases.get(_norm(s), set()) & present))]
    detail = f"{len(missing)} missing: {missing}" if missing else f"all {len(required)} present"
    return (FAIL if missing else PASS), detail, len(required), "required sections"


def _normalize_identifier(text):
    link = re.search(r"https?://\S+", text)
    if not link:
        return None
    key = link.group(0).rstrip(".,);]")
    key = re.sub(r"^https?://(www\.)?", "", key).rstrip("/").lower()
    return re.sub(r"^(dx\.)?doi\.org/", "", key)


def _split_reference_entries(body):
    """Segment a reference list into entries on BOTH boundaries that occur in practice.

    Unnumbered styles (APA, Chicago, MLA) separate entries with a blank line. Vancouver
    numbers them, and numbered entries are often adjacent with no blank line between.
    Splitting on blank lines alone merged adjacent numbered entries into one block, so
    only the first identifier was read and the rest went unexamined.
    """
    entries = []
    for block in re.split(r"\n\s*\n", body):
        if not block.strip():
            continue
        for part in re.split(r"(?m)^(?=\s*\d+\.\s)", block):
            entry = " ".join(part.split())
            if entry:
                entries.append(entry)
    return entries


def check_duplicate_sources(paper, _req):
    """Two reference entries pointing at one work, in ANY citation style.

    Vancouver numbers its entries; APA, Chicago and MLA do not. Keying on a leading
    number silently skipped every unnumbered style, so the check passed papers it had
    never actually examined.

    Coverage is entries PARSED, not entries compared. A paper whose reference list this
    function cannot find yields zero entries, and the honest report of that is a failure
    to examine rather than an absence of duplicates. This check reported `0 unique
    sources` with a PASS for exactly that input before EV-001.
    """
    refs = re.split(r"^#{1,3}\s*(?:References|Bibliography|Works Cited)\s*$", paper, flags=re.M | re.I)
    body = refs[-1] if len(refs) > 1 else ""
    entries = _split_reference_entries(body)
    seen, dupes, without = {}, [], 0
    for entry in entries:
        key = _normalize_identifier(entry)
        if not key:
            without += 1
            continue
        num = re.match(r"^(\d+)\.", entry)
        label = num.group(1) if num else entry[:38] + ("..." if len(entry) > 38 else "")
        if key in seen:
            dupes.append(f"'{seen[key]}' and '{label}' share {key}")
        else:
            seen[key] = label
    detail = f"{len(dupes)} duplicate source(s): {dupes}" if dupes else f"{len(seen)} unique sources"
    if without:
        detail += f"; {without} entr{'y' if without == 1 else 'ies'} carried no resolvable identifier and could not be compared"
    return (FAIL if dupes else PASS), detail, len(entries), "reference entries"


CITATION_MARKER = re.compile(r"\[\d+(?:\s*[,–-]\s*\d+)*\]")


def check_citation_order(paper_path, req):
    """Vancouver numbering against first appearance, via the bundled renumber pass.

    Coverage is the number of citation markers in the body, counted here rather than
    taken from the subprocess, so a renumber run that silently examined nothing cannot
    report a pass. A non-Vancouver paper is a SKIP: there is no numbering to check, and
    that is a different statement from 'checked and correct'.
    """
    style = req.get("academic_requirements", {}).get("citation_style", "")
    if style.lower() != "vancouver":
        return SKIP, f"citation_style is {style or 'undeclared'}; no numbering to check", 0, "citation markers"
    with open(paper_path, encoding="utf-8") as fh:
        body = re.split(r"^#{1,3}\s*(?:References|Bibliography|Works Cited)\s*$", fh.read(), flags=re.M | re.I)[0]
    markers = len(CITATION_MARKER.findall(body))
    if not os.path.exists(RENUMBER):
        return FAIL, "renumber_citations.py not found; citation order unverified", markers, "citation markers"
    r = subprocess.run([sys.executable, RENUMBER, paper_path, "--check"], capture_output=True, text=True)
    out = (r.stdout or r.stderr).strip()
    detail = out.splitlines()[-1] if out else f"exit {r.returncode}"
    return (PASS if r.returncode == 0 else FAIL), detail, markers, "citation markers"


CHECKS = [
    ("em_dashes", check_em_dashes, "paper"),
    ("forbidden_phrases", check_forbidden_phrases, "paper"),
    ("sections_present", check_sections_present, "paper"),
    ("duplicate_sources", check_duplicate_sources, "paper"),
    ("citation_order", check_citation_order, "path"),
]


def run_gate(paper_path, requirements_path):
    """Returns one record per check: name, status, detail, examined, unit.

    The zero-coverage rule is applied here rather than inside each check, so no future
    check can opt out of it by forgetting to.
    """
    with open(paper_path, encoding="utf-8") as fh:
        paper = fh.read()
    with open(requirements_path, encoding="utf-8") as fh:
        req = json.load(fh)
    results = []
    for name, fn, takes in CHECKS:
        status, detail, examined, unit = fn(paper_path if takes == "path" else paper, req)
        if status == PASS and examined == 0:
            status = FAIL
            detail = f"examined 0 {unit}; a check that examined nothing cannot pass ({detail})"
        results.append({"name": name, "status": status, "detail": detail, "examined": examined, "unit": unit})
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
    failed = [r["name"] for r in results if r["status"] == FAIL]
    skipped = [r["name"] for r in results if r["status"] == SKIP]
    verdict = "FAIL" if failed else "PASS"
    if a.json:
        print(json.dumps({"checks": results, "failed": failed, "skipped": skipped, "gate": verdict}, indent=2))
    else:
        print("RELEASE GATE")
        for r in results:
            print(f"  {r['status'].upper():<4}  {r['name']:<20} examined {r['examined']} {r['unit']:<18} {r['detail']}")
        line = f"gate: {verdict}"
        if failed:
            line += f" ({', '.join(failed)})"
        if skipped:
            line += f"; {len(skipped)} skipped ({', '.join(skipped)}) — skipped is not checked"
        print(line)
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
