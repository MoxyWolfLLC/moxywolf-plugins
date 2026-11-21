#!/usr/bin/env python3
"""review_reconcile.py: dedupe, score and compare findings from many review lanes (GR-002).

Commands
  dedupe  <run_dir>                          merge findings that cite one clause with one class
  score   <run_dir> --key K --manifest M [--meta F]
                                             match findings to a pre-labeled key, one to one
  compare <report> <report>                  apply AC2's stated rule; prints pass or fail and the clause

A run's findings are every `findings.json` under <run_dir> (one `{"findings": [...]}` object per lane,
revision and attempt, checked by GR-001's `review_run.validate_findings`). Nothing here reads a model: matching is set containment on strings.

exit 0 ok (compare: pass), 2 compare fail, 1 refused.

GR-001's `report` supplies `draft_to_decision_s`; `compare` reads it from the report's meta.
"""
import argparse
import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import review_run  # noqa: E402  (GR-001: the findings schema and its validator have one home)

FIELDS, CLASSES = review_run.FIELDS, review_run.CLASSES
BLOCKING = ("behavior_gap", "false_premise")


class Refused(Exception):
    pass


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def manifest_core_sha(path):
    """The manifest's core hash (GR-004): the file read, `width` removed, hashed by GR-001's own rule, so one manifest at two widths names one value."""
    try:
        m = json.loads(Path(path).read_text())
    except (OSError, ValueError) as e:
        raise Refused(f"manifest {path} is not readable JSON: {e}")
    if not isinstance(m, dict) or "width" not in m:
        raise Refused(f"manifest {path} is not a manifest object with a width")
    return review_run.core_sha({k: v for k, v in m.items() if k != "width"})


def dump(obj):
    return json.dumps(obj, indent=2, sort_keys=True) + "\n"


def read_findings(run_dir):
    """Every findings.json under a run, in GR-001's shape {"findings": [...]}, checked by GR-001's own validator."""
    out = []
    for f in sorted(Path(run_dir).rglob("findings.json")):
        try:
            rows = json.loads(f.read_text()).get("findings")
        except (ValueError, AttributeError):
            rows = None   # not JSON, or not an object: validate_findings names which
        for r in rows if isinstance(rows, list) else []:
            if isinstance(r, dict) and r.get("class") not in CLASSES and "class" in r:
                raise Refused(f"{f}: finding {r.get('finding_id')} has class {r['class']!r}, "
                              f"outside {', '.join(CLASSES)}")
        bad = review_run.validate_findings(f)
        if bad:
            raise Refused(f"{f}: {bad}")
        out.extend(rows)
    return out


def dedupe(run_dir):
    """Merge by (cited_clause, class). A clause reported under two classes stays split and is listed."""
    groups = {}
    for r in read_findings(run_dir):
        g = groups.setdefault((r["cited_clause"], r["class"]),
                              {"cited_clause": r["cited_clause"], "class": r["class"], "lanes": set(),
                               "finding_ids": [], "evidence": set(), "asks_change": False})
        g["lanes"].add(r["lane"])
        g["finding_ids"].append(r["finding_id"])
        g["evidence"].update(r["evidence"])
        g["asks_change"] = g["asks_change"] or bool(str(r["smallest_fix"]).strip())
    merged = []
    for key in sorted(groups):
        g = groups[key]
        merged.append({**g, "lanes": sorted(g["lanes"]), "finding_ids": sorted(g["finding_ids"]),
                       "evidence": sorted(g["evidence"])})
    by_clause = {}
    for g in merged:
        by_clause.setdefault(g["cited_clause"], set()).add(g["class"])
    split = sorted(c for c, cl in by_clause.items() if len(cl) > 1)
    return {"merged": merged, "split_by_class": split}


def score(run_dir, key_path, manifest_path, meta=None):
    key = json.loads(Path(key_path).read_text())
    for e in key:
        for k in ("key_id", "class", "condition", "evidence_required"):
            if k not in e:
                raise Refused(f"key entry missing {k}: {e}")
    taken, matches, repeats, false_blockers = {}, [], [], []
    # each finding is scored on its own evidence: evidence never pools across findings or lanes
    for r in sorted(read_findings(run_dir), key=lambda r: (str(r["finding_id"]), str(r["lane"]))):
        ev, fid = set(r["evidence"]), r["finding_id"]
        fits = [e["key_id"] for e in key if e["class"] == r["class"] and set(e["evidence_required"]) <= ev]
        free = [k for k in fits if k not in taken]
        if free:
            taken[free[0]] = fid
            matches.append({"key_id": free[0], "finding_id": fid})
        elif fits:
            repeats.append({"key_id": fits[0], "finding_id": fid})
        elif r["class"] in BLOCKING and str(r["smallest_fix"]).strip():
            false_blockers.append(fid)
    misses = [e["key_id"] for e in key if e["key_id"] not in taken]
    return {"counts": {"matches": len(matches), "repeats": len(repeats), "misses": len(misses),
                       "false_blockers": len(false_blockers)},
            "matches": matches, "repeats": repeats, "misses": misses, "false_blockers": false_blockers,
            "key_sha256": sha(key_path), "manifest_sha256": manifest_core_sha(manifest_path), "meta": meta or {}}


def compare(a, b):
    """AC2's rule and nothing else. Returns (passed, clause); refuses what isn't comparable."""
    for r in (a, b):
        m = r.get("meta", {})
        for k in ("width", "budget", "deadline_seconds", "decision", "decision_sound",
                  "decisions_to_dorian", "draft_to_decision_s"):
            if k not in m:
                raise Refused(f"report lacks meta.{k}")
        if m["draft_to_decision_s"] is None:   # GR-001's report gives None when no disposition was recorded
            raise Refused("meta.draft_to_decision_s is null: the run recorded no decision")
        if m["decision_sound"] is not True:
            # soundness is judged upstream (GR-001's acceptance check sets it); this module only requires it
            raise Refused("meta.decision_sound is not true: an unverified decision is not comparable")
    if a["manifest_sha256"] != b["manifest_sha256"]:
        raise Refused("not the same manifest: reports carry different manifest sha256 values")
    for k in ("budget", "deadline_seconds"):
        if a["meta"][k] != b["meta"][k]:
            raise Refused(f"different {k}: reports are not comparable")
    if a["meta"]["width"] == b["meta"]["width"]:
        raise Refused("both runs have the same width; one must be wider")
    narrow, wide = sorted((a, b), key=lambda r: r["meta"]["width"])
    nm, wm = narrow["meta"], wide["meta"]
    if wm["decision"] != nm["decision"]:
        return False, "same sound decision: the runs reached different decisions"
    if not wm["draft_to_decision_s"] < nm["draft_to_decision_s"]:
        return False, "draft-to-decision time: the wider run is not smaller"
    for k in ("misses", "false_blockers"):
        if wide["counts"][k] > narrow["counts"][k]:
            return False, f"{k}: the wider run has more"
    if wm["decisions_to_dorian"] > nm["decisions_to_dorian"]:
        return False, "decisions sent to Dorian: the wider run has more"
    return True, "all clauses hold"


def council_dispute(finding, accepted, ask, packet):
    """Send one disputed finding to Council only when GR-001's ledger accepts the dispatch.

    `accepted()` is the ledger's answer (False while council_gate is closed); `ask(finding)` is the
    decider_council.py call. A refusal leaves the finding open in the next recheck packet or the
    packet for Dorian (proposal section 3). ponytail: both are injected; GR-001's ledger isn't built.
    """
    if not accepted():
        packet.append({"finding_id": finding["finding_id"], "disposition": "open",
                       "why": "council gate closed or dispatch refused"})
        return "open"
    ask(finding)
    return "asked"


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = p.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("dedupe"); s.add_argument("run_dir")
    s = sub.add_parser("score"); s.add_argument("run_dir")
    s.add_argument("--key", required=True); s.add_argument("--manifest", required=True); s.add_argument("--meta")
    s = sub.add_parser("compare"); s.add_argument("a"); s.add_argument("b")
    a = p.parse_args(argv)
    try:
        if a.cmd == "dedupe":
            print(dump(dedupe(a.run_dir)), end="")
        elif a.cmd == "score":
            meta = json.loads(Path(a.meta).read_text()) if a.meta else None
            print(dump(score(a.run_dir, a.key, a.manifest, meta)), end="")
        else:
            ok, clause = compare(json.loads(Path(a.a).read_text()), json.loads(Path(a.b).read_text()))
            print(dump({"result": "pass" if ok else "fail", "clause": clause}), end="")
            return 0 if ok else 2
    except Refused as e:
        print(f"refused: {e}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
