#!/usr/bin/env python3
"""Validate, summarise, and grow a question bank.

    bank.py validate --bank B [--capability-map M] [--for-export]
    bank.py stats    --bank B
    bank.py add      --bank B --file additions.json [--capability-map M]
    bank.py report   --bank B [--capability-map M] --out demand-report.md

`add` is how expansions enter the bank. It assigns ids, refuses anything that
would make the bank fail validation, and never edits existing questions, so a
bad expansion batch is rejected whole instead of half-applied.
"""

from __future__ import annotations

import argparse
import copy
import datetime as _dt
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import demandlib as dl  # noqa: E402


def _tools(path: str | None):
    if not path:
        return None
    return dl.load_json(path)["mcp"]["tool_names"]


def _routes(path: str | None):
    if not path:
        return None
    return [r["path"] for r in dl.load_json(path)["rest"]["routes"]]


def cmd_validate(a) -> int:
    bank = dl.load_json(a.bank)
    rep = dl.validate_bank(bank, _tools(a.capability_map), a.ratio, for_export=a.for_export, routes=_routes(a.capability_map))
    for f in rep.findings:
        print(f)
    print(f"{'OK' if rep.ok else 'FAIL'} errors={len(rep.errors)} warnings={len(rep.findings) - len(rep.errors)} questions={len(bank['questions'])}")
    return 0 if rep.ok else 1


def cmd_stats(a) -> int:
    import json

    print(json.dumps(dl.bank_stats(dl.load_json(a.bank)), indent=2))
    return 0


def cmd_add(a) -> int:
    bank = dl.load_json(a.bank)
    incoming = dl.load_json(a.file)
    items = incoming if isinstance(incoming, list) else incoming.get("questions", [])
    trial = copy.deepcopy(bank)
    for item in items:
        q = dict(item)
        q.pop("id", None)
        q["id"] = dl.next_question_id(trial)
        q.setdefault("status", "active")
        q.setdefault("priority", 2)
        q.setdefault("surfaces", ["mcp"])
        q.setdefault("expect", {})
        trial["questions"].append(q)
    rep = dl.validate_bank(trial, _tools(a.capability_map), a.ratio, routes=_routes(a.capability_map))
    if not rep.ok:
        for f in rep.errors:
            print(f)
        print(f"REJECTED {len(items)} questions; bank unchanged")
        return 1
    dl.dump_json(trial, a.bank)
    print(f"added={len(items)} total={len(trial['questions'])}")
    for f in rep.findings:
        print(f)
    return 0


def _fmt_counts(d: dict) -> str:
    return ", ".join(f"{k} {v}" for k, v in d.items()) or "none"


def cmd_accept(a) -> int:
    """A named person accepts draft questions they have read. Accepted drafts
    become exportable; the name and date go into the question's history."""
    if not dl.named_person(a.approver):
        print("ERROR --approver must be a named person (first and last name)", file=sys.stderr)
        return 2
    bank = dl.load_json(a.bank)
    want = set(a.ids)
    by_id = {q["id"]: q for q in bank["questions"]}
    missing = sorted(want - set(by_id))
    if missing:
        print(f"ERROR not in bank: {', '.join(missing)}", file=sys.stderr)
        return 2
    n = 0
    for qid in sorted(want):
        q = by_id[qid]
        if q.get("review_status") != "draft":
            print(f"skip {qid}: not a draft")
            continue
        q["review_status"] = "accepted"
        q.setdefault("history", []).append({"action": "accept-draft", "approved_by": a.approver, "on": _dt.date.today().isoformat(), "why": a.note or "Reviewed and accepted."})
        n += 1
    rep = dl.validate_bank(bank, _tools(a.capability_map), a.ratio, routes=_routes(a.capability_map))
    if rep.errors:
        for f in rep.errors:
            print(f, file=sys.stderr)
        print("REJECTED accept would leave the bank invalid; bank unchanged", file=sys.stderr)
        return 1
    dl.dump_json(bank, a.bank)
    print(f"accepted={n} by {a.approver}")
    return 0


def cmd_report(a) -> int:
    bank = dl.load_json(a.bank)
    cmap = dl.load_json(a.capability_map) if a.capability_map else None
    st = dl.bank_stats(bank)
    qs = dl.active_questions(bank)
    lines = [f"# Demand bank report: {bank['product']}", ""]
    lines += [
        f"Active questions: {st['active_questions']}. Runnable as written: {st['runnable']}. Blocked on customer input: {st['blocked_by_input']}. Drafts awaiting review: {st['drafts']}.",
        "",
        "## Evidence strength",
        "",
        "| Class | Questions | What it means |",
        "|---|---|---|",
    ]
    for cls in dl.EVIDENCE_CLASSES:
        lines.append(f"| {cls} | {st['by_evidence_class'].get(cls, 0)} | {dl.EVIDENCE_MEANING[cls]} |")
    lines += ["", "## Personas", "", "| Persona | Questions | Observed or reported | Strict | Discovery |", "|---|---|---|---|---|"]
    for p in bank["personas"]:
        mine = [q for q in qs if q["persona"] == p["id"]]
        real = sum(1 for q in mine if q["evidence"]["class"] in ("observed", "reported")) + sum(1 for q in mine if (q.get("demand") or {}).get("observed") or (q.get("demand") or {}).get("reported"))
        lines.append(f"| {p['name']} | {len(mine)} | {real} | {sum(1 for q in mine if q['mode'] == 'strict')} | {sum(1 for q in mine if q['mode'] == 'discovery')} |")
    if st["personas_without_questions"]:
        lines += ["", "Personas with no questions at all: " + ", ".join(st["personas_without_questions"]) + "."]
    lines += ["", "Personas with no observed or reported evidence: " + (", ".join(st["personas_without_evidence"]) or "none") + "."]

    if cmap:
        expected = {}
        for q in qs:
            for t in (q.get("expect") or {}).get("first_tool_any_of", [])[:1]:
                expected[t] = expected.get(t, 0) + 1
            if q.get("payload"):
                expected.setdefault(q["payload"]["tool"], expected.get(q["payload"]["tool"], 0))
        lines += ["", "## Tool coverage", "", "| Tool | Questions expecting it first | Has a payload check |", "|---|---|---|"]
        payload_tools = {q["payload"]["tool"] for q in qs if q.get("payload")}
        for t in cmap["mcp"]["tool_names"]:
            lines.append(f"| `{t}` | {expected.get(t, 0)} | {'yes' if t in payload_tools else 'no'} |")
        rest_only = cmap["rest"]["rest_only_routes"]
        match = dl._route_matcher
        all_routes = [r["path"] for r in cmap["rest"]["routes"]]
        covered: dict[str, list[str]] = {r: [] for r in rest_only}
        for q in qs:
            for c in (q.get("rest") or {}).get("calls") or []:
                hits = [r for r in all_routes if match([r])(c.get("path", ""))]
                literal = [r for r in hits if "{" not in r]
                for r in literal or hits:  # /stigs/batch is not /stigs/{slug}
                    if r in covered:
                        covered[r].append(q["id"] + (" (draft)" if q.get("review_status") == "draft" else ""))
        n_cov = sum(1 for v in covered.values() if v)
        lines += ["", f"## REST-only surface ({len(rest_only)} routes no MCP tool reaches)", "",
                  f"An MCP user cannot reach these. {n_cov} have a REST question; the rest have none yet.", "",
                  "| Route | REST questions |", "|---|---|"]
        lines += [f"| `{r}` | {', '.join(covered[r]) or '-'} |" for r in rest_only]

    blocked = [q for q in qs if q.get("requires_input")]
    if blocked:
        lines += ["", "## Blocked on customer input", "", "These are the questions the ICP asks about their own data. They cannot run until an expansion instantiates them with a concrete, synthetic input.", ""]
        by_need: dict[str, list[str]] = {}
        for q in blocked:
            for n in q["requires_input"]:
                by_need.setdefault(n.split(":")[0], []).append(q["id"])
        children: dict[str, list[str]] = {}
        for q in qs:
            par = (q.get("evidence") or {}).get("parent")
            if par:
                children.setdefault(par, []).append(q["id"] + (" draft" if q.get("review_status") == "draft" else ""))
        for n, ids in sorted(by_need.items()):
            lines.append(f"- {n}: {len(ids)} question{'s' if len(ids) != 1 else ''} ({', '.join(ids)})")
        lines += ["", "| Blocked question | Instantiated by |", "|---|---|"]
        lines += [f"| {q['id']} | {', '.join(children.get(q['id'], [])) or 'not yet'} |" for q in blocked]
    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    with open(a.out, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")
    print(f"wrote {a.out}")
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name in ("validate", "stats", "add", "accept", "report"):
        p = sub.add_parser(name)
        p.add_argument("--bank", required=True)
        p.add_argument("--capability-map")
        p.add_argument("--ratio", type=float, default=dl.DEFAULT_GENERATED_RATIO)
        if name == "validate":
            p.add_argument("--for-export", action="store_true")
        if name == "add":
            p.add_argument("--file", required=True)
        if name == "report":
            p.add_argument("--out", required=True)
        if name == "accept":
            p.add_argument("--ids", nargs="+", required=True, help="drafts this person read; there is no accept-all")
            p.add_argument("--approver", required=True)
            p.add_argument("--note")
    a = ap.parse_args(argv)
    return {"validate": cmd_validate, "stats": cmd_stats, "add": cmd_add, "accept": cmd_accept, "report": cmd_report}[a.cmd](a)


if __name__ == "__main__":
    sys.exit(main())
