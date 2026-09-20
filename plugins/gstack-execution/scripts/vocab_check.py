#!/usr/bin/env python3
"""XE-011 criterion 3: do the contract files and DESIGN.md use the vocabulary, and only it?

  vocab_check.py [--repo <root>]      exit 0 clean, 1 on a failure, and says what it examined
  vocab_check.py --selftest

Fails on: an item status outside the vocabulary; a vocabulary definition restated verbatim in a
contract file (one home, XE-008); examining zero files or zero term uses (EV-001). Reports, and does
not fail on, backticked snake_case tokens that are not vocabulary ids: most are code identifiers,
and a check that cannot tell the two apart must not be dressed as a gate.

ponytail: verbatim match only for restated definitions. A paraphrase is not caught; the ceiling is
named here rather than implied away. Upgrade path: fuzzy match if paraphrase shows up in practice.
"""
import json
import re
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
REFS = HERE.parent / "skills" / "gstack-execution" / "references"
STATUS = re.compile(r"^\*\*Status:\*\*\s*(\S+?)(?=[.;,:]|\s|$)")
TERM = re.compile(r"`([a-z]+(?:_[a-z]+)+)`")


def check(files, vocab):
    ids = {c["id"] for c in vocab["concepts"]}
    statuses = {c["id"] for c in vocab["concepts"] if c["group"] == "item_status"}
    defs = {c["id"]: c["skos:definition"] for c in vocab["concepts"]}
    report = {"files": 0, "term_uses": 0, "resolved": 0, "unresolved": {}, "status_lines": 0, "failures": []}
    for f in files:
        if not f.is_file():
            report["failures"].append(f"{f}: missing; a moved file is not a clean one")
            continue
        report["files"] += 1
        text = f.read_text(encoding="utf-8")
        for n, line in enumerate(text.splitlines(), 1):
            m = STATUS.match(line)
            if m:
                report["status_lines"] += 1
                if m.group(1) not in statuses:
                    report["failures"].append(f"{f.name}:{n}: status {m.group(1)!r} is not one of {sorted(statuses)}")
            for t in TERM.findall(line):
                report["term_uses"] += 1
                if t in ids:
                    report["resolved"] += 1
                else:
                    report["unresolved"][t] = report["unresolved"].get(t, 0) + 1
        for cid, d in defs.items():
            if d in text:
                report["failures"].append(f"{f.name}: restates the definition of {cid!r}; cite the id instead")
    if report["files"] == 0:
        report["failures"].append("examined no files")
    if report["term_uses"] == 0:
        report["failures"].append("found no term uses; a check over nothing is not a pass")
    return report


def default_files(repo):
    return [repo / "DESIGN.md", REFS / "peer-review-contract.md", REFS / "design-doc-template.md"]


def main(argv):
    if "--selftest" in argv:
        return selftest()
    repo = Path(argv[argv.index("--repo") + 1]) if "--repo" in argv else HERE.parents[2]
    vocab = json.loads((REFS / "vocabulary.json").read_text())
    r = check(default_files(repo), vocab)
    print(f"vocabulary {vocab['version']}: examined {r['files']} files, {r['status_lines']} status lines, "
          f"{r['term_uses']} term uses ({r['resolved']} resolve, {sum(r['unresolved'].values())} do not)")
    if r["unresolved"]:
        print("not vocabulary ids (reported, not failed): " + ", ".join(sorted(r["unresolved"])))
    for x in r["failures"]:
        print("FAIL " + x)
    return 1 if r["failures"] else 0


def selftest():
    vocab = {"concepts": [{"id": "done", "group": "item_status", "skos:definition": "every criterion met"},
                          {"id": "stale_link", "group": "verify_outcome", "skos:definition": "a link resolved elsewhere"}]}
    with tempfile.TemporaryDirectory() as t:
        good = Path(t, "good.md"); good.write_text("**Status:** done. merged.\nreports `stale_link`.\n")
        bad = Path(t, "bad.md"); bad.write_text("**Status:** built, partially.\n`stale_link`\n")
        dup = Path(t, "dup.md"); dup.write_text("`stale_link` means a link resolved elsewhere.\n")
        empty = Path(t, "empty.md"); empty.write_text("nothing here\n")
        assert check([good], vocab)["failures"] == []
        assert any("'built'" in x for x in check([bad], vocab)["failures"])
        assert any("restates" in x for x in check([dup], vocab)["failures"])
        assert any("no term uses" in x for x in check([empty], vocab)["failures"])
        assert any("no files" in x for x in check([], vocab)["failures"])
        assert any("missing" in x for x in check([Path(t, "gone.md")], vocab)["failures"])
    print("selftest ok")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
