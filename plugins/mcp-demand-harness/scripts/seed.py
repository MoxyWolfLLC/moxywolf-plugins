#!/usr/bin/env python3
"""Build and grow the question bank from evidence.

Subcommands (all write only the bank file you name):

  personas   Read the persona table from a product-marketing doc.
  inventory  Import a numbered ICP question inventory (markdown).
  golden     Import a golden set already converted by golden_to_json.mjs.
  evidence   Import real user questions from a CSV/JSONL export
             (telemetry, support, sales notes). Redacts, drops excluded orgs,
             and counts repeats against existing questions instead of adding
             duplicates. The repeat count is the demand signal.

Every imported question records where it came from and how strong that
evidence is. Nothing here calls a network or a model.
"""

from __future__ import annotations

import argparse
import csv
import datetime as _dt
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import demandlib as dl  # noqa: E402

# ------------------------------------------------------------------ helpers


def _load_or_new(path: str, product: str) -> dict:
    if os.path.exists(path):
        return dl.load_json(path)
    return dl.empty_bank(product)


def _tokens(text: str) -> set[str]:
    stop = {"the", "a", "an", "of", "to", "for", "and", "or", "is", "are", "do", "does", "what", "which", "my", "our", "this", "these", "that", "in", "on", "it", "i", "we", "me", "be", "with", "can", "how"}
    return {t for t in dl.normalise_text(text).split() if t not in stop and len(t) > 1}


def similarity(a: str, b: str) -> float:
    ta, tb = _tokens(a), _tokens(b)
    if not ta or not tb:
        return 0.0
    return len(ta & tb) / len(ta | tb)


def best_match(bank: dict, text: str, threshold: float) -> dict | None:
    best, score = None, 0.0
    for q in bank["questions"]:
        s = similarity(text, q["text"])
        if s > score:
            best, score = q, s
    return best if score >= threshold else None


def _today() -> str:
    return _dt.date.today().isoformat()


# ----------------------------------------------------------------- personas


def cmd_personas(a, profile: dict) -> int:
    bank = _load_or_new(a.bank, profile.get("product") or a.product)
    text = open(a.doc, encoding="utf-8").read()
    rows = re.findall(r"^\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|\s*$", text, re.M)
    pmap = profile.get("persona_map", {})
    have = {p["id"] for p in bank["personas"]}
    added = 0
    for name, role, cares in rows:
        if name.lower() == "persona" or set(name) <= set("-: "):
            continue
        pid = pmap.get(name) or re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
        if pid in have:
            continue
        line = text[: text.find(name)].count("\n") + 1
        bank["personas"].append({"id": pid, "name": name, "role_in_purchase": role, "cares_about": cares, "source": f"{a.doc_ref or a.doc}:{line}"})
        have.add(pid)
        added += 1
    dl.dump_json(bank, a.bank)
    print(f"personas added={added} total={len(bank['personas'])}")
    return 0


# ---------------------------------------------------------------- inventory

_INV_LINE = re.compile(r'^\*\*(\d+)\.\s+["\u201c](.+?)["\u201d]\*\*\s*(?:\u00b7|-)?\s*(.*)$')
_INV_SECTION = re.compile(r"^#{2,3}\s+([A-Z])\.\s+(.*)$")
_GATE_KIND = [("BOUNDARY", "boundary"), ("NO-TOOL", "gap"), ("NO-DATA", "gap"), ("OPEN", "gap"), ("LIVE", "live")]


def parse_inventory(text: str) -> list[dict]:
    items, section, section_title = [], None, None
    for n, line in enumerate(text.splitlines(), start=1):
        m = _INV_SECTION.match(line)
        if m:
            section, section_title = m.group(1), m.group(2).strip()
            continue
        m = _INV_LINE.match(line.strip())
        if m and section:
            gate = re.sub(r"\*", "", m.group(3)).strip()
            items.append({"num": m.group(1), "text": m.group(2).strip(), "gate": gate, "section": section, "section_title": section_title, "line": n})
    return items


def _kind_from_gate(gate: str) -> str:
    up = gate.upper()
    for token, kind in _GATE_KIND:
        if token in up:
            return kind
    return "gap"


def cmd_inventory(a, profile: dict) -> int:
    bank = _load_or_new(a.bank, profile.get("product") or a.product)
    text = open(a.doc, encoding="utf-8").read()
    items = parse_inventory(text)
    anchors = profile.get("inventory_anchor_personas", {})
    overrides = profile.get("inventory_persona_overrides", {})
    contracts = profile.get("inventory_input_contracts", {})
    persona_ids = {p["id"] for p in bank["personas"]}
    ref = a.doc_ref or a.doc
    added = skipped = 0
    for it in items:
        key = f"{ref}#{it['num']}"
        if any((q.get("evidence") or {}).get("source") == key for q in bank["questions"]):
            skipped += 1
            continue
        persona = overrides.get(it["num"]) or anchors.get(it["section"])
        if persona not in persona_ids:
            print(f"ERROR inventory #{it['num']} maps to persona {persona!r}, which is not in the bank; run `personas` first or fix the profile", file=sys.stderr)
            return 2
        needs = sorted(set(re.findall(r"IN-\d", it["gate"])))
        q = {
            "id": dl.next_question_id(bank),
            "text": it["text"],
            "persona": persona,
            "anchor": it["section_title"],
            "intent": it["text"][:80],
            "mode": "discovery",
            "kind": _kind_from_gate(it["gate"]),
            "surfaces": ["mcp"],
            "priority": 2,
            "status": "active",
            "review_status": "accepted",
            "evidence": {
                "class": "hypothesis",
                "source": key,
                "source_line": it["line"],
                "source_date": a.doc_date,
                "note": "Team-written ICP inventory. A hypothesis about demand, not evidence of it.",
            },
            "historical_gate": f"{it['gate']} (as of {a.doc_date})" if a.doc_date else it["gate"],
            "requires_input": [f"{n}: {contracts.get(n, 'customer-held input')}" for n in needs],
            "expect": {},
        }
        if not q["requires_input"]:
            del q["requires_input"]
        if q["kind"] == "boundary":
            q["expect"]["must_refuse"] = True
            q["expect"]["rubric"] = "The answer declines the part of the request the product cannot stand behind, says why, and offers what it can provide instead."
            q["mode"] = "strict"
            q["why"] = f"Inventory gate {it['gate']}: a confident answer here would claim something the product does not hold."
        bank["questions"].append(q)
        added += 1
    dl.dump_json(bank, a.bank)
    print(f"inventory items={len(items)} added={added} already_present={skipped}")
    return 0


# ------------------------------------------------------------------- golden


def _rx(entry) -> object:
    """golden {$regex, flags} -> bank pattern entry (string if case-insensitive)."""
    if isinstance(entry, dict) and "$regex" in entry:
        if "i" in entry.get("flags", ""):
            return entry["$regex"]
        return {"pattern": entry["$regex"], "case_sensitive": True}
    return str(entry)


_KIND = {"live": "live", "composed": "composed", "boundary": "boundary"}


def golden_to_question(g: dict, qid: str, persona: str, ref: str) -> dict:
    e = g.get("expect") or {}
    kind = _KIND.get(g.get("kind"), "live")
    q = {
        "id": qid,
        "text": g["question"],
        "persona": persona,
        "intent": g["question"][:80],
        "mode": "strict",
        "kind": kind,
        "surfaces": ["mcp", "rest"],
        "priority": 1,
        "status": "active",
        "review_status": "accepted",
        "evidence": {"class": "hypothesis", "source": f"{ref}#{g['id']}", "golden_id": g["id"], "note": "Golden set (team-written, derived from the ICP inventory)."},
        "why": g.get("why", ""),
        "expect": {},
    }
    # A question with no direct call (e.g. a pure-refusal boundary case) has no
    # payload to check; only the model's answer is graded.
    p = q["payload"] = {"tool": g["call"]["tool"], "args": g["call"].get("args", {})} if g.get("call") else {}
    if p and e.get("mustContain"):
        p["must_contain"] = list(e["mustContain"])
    if p and e.get("mustNotContain"):
        p["must_not_match"] = [_rx(x) for x in e["mustNotContain"]]
    if p and e.get("absenceAcceptable"):
        p["absence_acceptable"] = True
    if e.get("absenceAcceptable"):
        q["expect"]["absence_acceptable"] = True

    # The upstream harness grades the model's FIRST tool pick for live and
    # composed questions, and grades the model's TEXT against mustNotContain
    # only for boundary questions. Mirror that split exactly: payload needles
    # never become answer needles, because a model can answer correctly in
    # different words than the payload uses.
    if kind == "boundary":
        if e.get("mustNotContain"):
            q["expect"]["must_not_match"] = [_rx(x) for x in e["mustNotContain"]]
        if e.get("mustRefuse"):
            q["expect"]["must_refuse"] = True
            q["expect"]["rubric"] = "The answer refuses the out-of-scope part, explains the boundary in one sentence, and offers what the product does hold. " + g.get("why", "")
    else:
        q["expect"]["first_tool_any_of"] = [g["expectTool"]] + list(g.get("alsoAcceptable") or [])
    if not p:
        del q["payload"]
        q["surfaces"] = ["mcp"]
    return q


def cmd_golden(a, profile: dict) -> int:
    bank = _load_or_new(a.bank, profile.get("product") or a.product)
    data = dl.load_json(a.json)
    ref = a.ref or data.get("source", a.json)
    tool_persona = profile.get("tool_personas", {})
    persona_ids = {p["id"] for p in bank["personas"]}
    added = merged = 0
    for g in data["items"]:
        if any((q.get("evidence") or {}).get("golden_id") == g["id"] for q in bank["questions"]):
            continue
        match = best_match(bank, g["question"], a.merge_threshold)
        if match is not None and (match.get("evidence") or {}).get("class") == "hypothesis" and "golden_id" not in match["evidence"]:
            # Same question already came in from the inventory: keep one record,
            # carry both sources, and adopt the golden set's checked expectations.
            persona = match["persona"]
            new = golden_to_question(g, match["id"], persona, ref)
            new["evidence"]["also_in"] = match["evidence"]["source"]
            new["historical_gate"] = match.get("historical_gate")
            new["anchor"] = match.get("anchor")
            if match.get("requires_input"):
                new["requires_input_note"] = "Inventory version needs customer input; the golden version supplies concrete arguments."
            match.clear()
            match.update({k: v for k, v in new.items() if v is not None})
            merged += 1
            continue
        persona = tool_persona.get(g["expectTool"])
        if persona not in persona_ids:
            print(f"ERROR golden {g['id']}: no persona for tool {g['expectTool']}; add it to profile.tool_personas", file=sys.stderr)
            return 2
        bank["questions"].append(golden_to_question(g, dl.next_question_id(bank), persona, ref))
        added += 1
    dl.dump_json(bank, a.bank)
    print(f"golden items={len(data['items'])} added={added} merged_into_inventory={merged}")
    return 0


# ----------------------------------------------------------------- evidence

_REDACTIONS = [
    (re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}"), "[EMAIL]"),
    (re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b"), "[IP]"),
    (re.compile(r"\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b", re.I), "[UUID]"),
    (re.compile(r"\b(?:sk|pk|svk|svtest|ghp|xox[bap])_[A-Za-z0-9_-]{8,}\b"), "[SECRET]"),
    # Phone-shaped (NANP or +CC with 3-3-4 groups). Looser digit-run patterns
    # ate dates (2026-10-25) and framework runs ("800-53 800-171").
    (re.compile(r"(?<![\w-])(?:\+\d{1,3}[\s.-]?)?\(?\d{3}\)?[\s.-]?\d{3}[\s.-]\d{4}(?![\w-])"), "[NUMBER]"),
    (re.compile(r"\b(?:[a-z0-9-]+\.){2,}(?:mil|gov|com|net|org|local|internal|corp)\b", re.I), "[HOST]"),
]


def redact(text: str) -> tuple[str, list[str]]:
    hits = []
    for rx, token in _REDACTIONS:
        if rx.search(text):
            hits.append(token)
            text = rx.sub(token, text)
    return text, hits


def _rows(path: str):
    if path.endswith(".jsonl"):
        with open(path, encoding="utf-8") as fh:
            for line in fh:
                if line.strip():
                    yield json.loads(line)
    elif path.endswith(".json"):
        data = dl.load_json(path)
        yield from (data if isinstance(data, list) else data.get("rows", []))
    else:
        with open(path, encoding="utf-8", newline="") as fh:
            yield from csv.DictReader(fh)


def cmd_evidence(a, profile: dict) -> int:
    if a.evidence_class not in ("observed", "reported"):
        print("ERROR --class must be observed or reported", file=sys.stderr)
        return 2
    bank = _load_or_new(a.bank, profile.get("product") or a.product)
    excluded = {o.lower() for o in (profile.get("evidence_exclusions") or {}).get("org_names", [])}
    excluded |= {o.lower() for o in a.exclude_org or []}
    persona_ids = {p["id"] for p in bank["personas"]}
    if a.persona and a.persona not in persona_ids:
        print(f"ERROR persona {a.persona} not in bank", file=sys.stderr)
        return 2

    stats = {"rows": 0, "empty": 0, "excluded_org": 0, "counted_against_existing": 0, "added": 0, "redacted": 0}
    for row in _rows(a.file):
        stats["rows"] += 1
        raw = (row.get(a.text_col) or "").strip()
        if not raw:
            stats["empty"] += 1
            continue
        org = (row.get(a.org_col) or "").strip().lower() if a.org_col else ""
        if org and org in excluded:
            stats["excluded_org"] += 1
            continue
        text, hits = redact(raw)
        if hits:
            stats["redacted"] += 1
        seen = (row.get(a.date_col) or "")[:10] if a.date_col else ""
        match = best_match(bank, text, a.count_threshold)
        if match is not None:
            d = match.setdefault("demand", {"observed": 0, "reported": 0, "sources": []})
            d[a.evidence_class] = d.get(a.evidence_class, 0) + 1
            if a.source_name not in d["sources"]:
                d["sources"].append(a.source_name)
            if seen and seen > d.get("last_seen", ""):
                d["last_seen"] = seen
            stats["counted_against_existing"] += 1
            continue
        persona = a.persona or (row.get(a.persona_col) if a.persona_col else None)
        if persona not in persona_ids:
            persona = "unassigned"
            if "unassigned" not in persona_ids:
                bank["personas"].append({"id": "unassigned", "name": "Unassigned", "role_in_purchase": "unknown", "cares_about": "", "source": "evidence import: no persona column; assign during review"})
                persona_ids.add("unassigned")
        ev = {
            "class": a.evidence_class,
            "source": f"{a.source_name}:{row.get(a.id_col) if a.id_col else stats['rows']}",
            "source_date": seen or None,
            "redacted": True,
            "redactions": hits,
            "release_approved_by": None,
            "note": "Imported user words after automatic redaction. Names and free-text identifiers are not reliably caught; review before approving release.",
        }
        bank["questions"].append(
            {
                "id": dl.next_question_id(bank),
                "text": text,
                "persona": persona,
                "intent": text[:80],
                "mode": "discovery",
                "kind": "live",
                "surfaces": ["mcp"],
                "priority": 2,
                "status": "active",
                "review_status": "accepted",
                "evidence": ev,
                "expect": {},
            }
        )
        stats["added"] += 1
    dl.dump_json(bank, a.bank)
    print(" ".join(f"{k}={v}" for k, v in stats.items()))
    return 0


def cmd_approve_release(a, profile: dict) -> int:
    """Stamp a named human's release approval on observed questions."""
    if not dl.named_person(a.approver):
        print("ERROR --approver must be a named person (first and last name)", file=sys.stderr)
        return 2
    bank = dl.load_json(a.bank)
    ids = set(a.ids)
    n = 0
    for q in bank["questions"]:
        ev = q.get("evidence") or {}
        if ev.get("class") != "observed" or ev.get("release_approved_by"):
            continue
        if q["id"] not in ids:
            continue
        ev["release_approved_by"] = a.approver
        ev["release_approved_on"] = _today()
        n += 1
    dl.dump_json(bank, a.bank)
    print(f"approved={n} by {a.approver}")
    return 0


# --------------------------------------------------------------------- main


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--profile")
    ap.add_argument("--product", default="product")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("personas")
    p.add_argument("--bank", required=True)
    p.add_argument("--doc", required=True)
    p.add_argument("--doc-ref", help="repo-relative path recorded as the source")

    p = sub.add_parser("inventory")
    p.add_argument("--bank", required=True)
    p.add_argument("--doc", required=True)
    p.add_argument("--doc-ref")
    p.add_argument("--doc-date", help="date the inventory was written; gates are recorded as of this date")

    p = sub.add_parser("golden")
    p.add_argument("--bank", required=True)
    p.add_argument("--json", required=True, help="output of golden_to_json.mjs")
    p.add_argument("--ref")
    p.add_argument("--merge-threshold", type=float, default=0.5)

    p = sub.add_parser("evidence")
    p.add_argument("--bank", required=True)
    p.add_argument("--file", required=True, help=".csv, .jsonl or .json export")
    p.add_argument("--source-name", required=True, help="e.g. api_access_logs.mcp_intent, zendesk, gong")
    p.add_argument("--class", dest="evidence_class", default="observed")
    p.add_argument("--text-col", required=True)
    p.add_argument("--date-col")
    p.add_argument("--org-col")
    p.add_argument("--id-col")
    p.add_argument("--persona", help="assign every new question to this persona")
    p.add_argument("--persona-col")
    p.add_argument("--exclude-org", action="append")
    p.add_argument("--count-threshold", type=float, default=0.6)

    p = sub.add_parser("approve-release")
    p.add_argument("--bank", required=True)
    p.add_argument("--approver", required=True, help="the named human approving release of redacted user words")
    p.add_argument("--ids", nargs="+", required=True, help="the questions this person read and approved; there is no approve-all")

    a = ap.parse_args(argv)
    profile = dl.load_profile(a.profile)
    return {"personas": cmd_personas, "inventory": cmd_inventory, "golden": cmd_golden, "evidence": cmd_evidence, "approve-release": cmd_approve_release}[a.cmd](a, profile)


if __name__ == "__main__":
    sys.exit(main())
