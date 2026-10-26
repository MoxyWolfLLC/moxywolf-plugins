#!/usr/bin/env python3
"""Read harness results back onto the bank and say what they mean.

    results.py ingest --bank B --capability-map M --out <dir>/gap-report.md \
        [--mcpjam report.json ...] [--mcpeval report.json ...] [--probe results.json ...]

    results.py apply --bank B --proposals <dir>/proposals.json --approver "Full Name" --ids Q-0001 ...

`ingest` never edits the bank. It writes:
  gap-report.md   per persona: what passed, what failed, and the failure
                  pattern (wrong tool, no tool, boundary broken, payload wrong)
  proposals.json  suggested bank changes, e.g. promote a discovery question to
                  strict using the tool sequence it consistently took

`apply` writes accepted proposals into the bank, stamped with the approver.
Promotion turns an observation into a regression test, so a person decides.

Report parsing is deliberately structural: every exported case carries its
bank id (case id `q-0001`, title `Q-0001 ...`, or metadata.bank_id), so any
report that keeps per-case records can be read, whatever the harness version.
"""

from __future__ import annotations

import argparse
import datetime as _dt
import os
import re
import sys
from collections import Counter, defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import demandlib as dl  # noqa: E402

BANK_ID = re.compile(r"\b[qQ]-(\d{4,})\b")
PASS_WORDS = {"passed", "pass", "success", "succeeded", "ok"}
FAIL_WORDS = {"failed", "fail", "error", "errored", "failure"}


def _bank_id(obj: dict) -> str | None:
    md = obj.get("metadata") if isinstance(obj.get("metadata"), dict) else {}
    if md.get("bank_id"):
        return md["bank_id"]
    for k in ("caseId", "case_id", "id", "title", "case_name", "name", "testCaseId"):
        v = obj.get(k)
        if isinstance(v, str):
            m = BANK_ID.search(v)
            if m:
                return f"Q-{m.group(1)}"
    return None


def _verdict(obj: dict) -> bool | None:
    if isinstance(obj.get("passed"), bool):
        return obj["passed"]
    for k in ("verdict", "result", "status", "outcome"):
        v = obj.get(k)
        if isinstance(v, str):
            if v.lower() in PASS_WORDS:
                return True
            if v.lower() in FAIL_WORDS:
                return False
    return None


def _tool_sequence(obj) -> list[str]:
    """Best-effort: tool names in call order, from any toolCalls-like list."""
    seq: list[str] = []

    def walk(o):
        if isinstance(o, dict):
            for k, v in o.items():
                if k in ("toolCalls", "tool_calls", "calls") and isinstance(v, list):
                    for c in v:
                        if isinstance(c, dict):
                            n = c.get("toolName") or c.get("name") or c.get("tool")
                            if isinstance(n, str):
                                seq.append(n)
                elif k == "sequence" and isinstance(v, list) and all(isinstance(x, str) for x in v):
                    seq.extend(v)
                else:
                    walk(v)
        elif isinstance(o, list):
            for x in o:
                walk(x)

    walk(obj)
    return seq


def _tool_count(obj) -> int | None:
    """A tool-call count if the report carries one (mcp-eval: metrics.tool_calls)."""
    m = obj.get("metrics") if isinstance(obj.get("metrics"), dict) else {}
    for v in (m.get("tool_calls"), m.get("tool_call_count"), obj.get("toolCallCount")):
        if isinstance(v, int) and not isinstance(v, bool):
            return v
    return None


def _failed_checks(obj) -> list[str]:
    out: list[str] = []

    def walk(o):
        if isinstance(o, dict):
            name = o.get("name") or o.get("type") or o.get("evaluator") or o.get("check")
            v = _verdict(o)
            if v is False and isinstance(name, str) and not BANK_ID.search(name):
                out.append(name)
            for x in o.values():
                walk(x)
        elif isinstance(o, list):
            for x in o:
                walk(x)

    walk(obj)
    return sorted(set(out))


def collect_mcpjam_local(report: dict) -> tuple[list[dict], list[str]]:
    """MCPJam `mcpjam test` report (kind eval-local-run). The per-iteration
    tool calls live only in metadata.cases[].iterations[]; the top-level
    cases[] repeats each case without them, so reading both double-counts.
    Returns (records, notes)."""
    recs, notes = [], []
    for c in report["metadata"]["cases"]:
        bid = _bank_id(c)
        if not bid:
            continue
        judge = c.get("judge") or {}
        if judge.get("configured") and judge.get("run") is False:
            notes.append(f"{bid}: MCPJam did not run the LLM judge locally ({judge.get('skipReason')}); rubric is unchecked here")
        for it in c.get("iterations") or []:
            tv = it.get("taskVerdict")
            if tv not in ("passed", "failed"):
                notes.append(f"{bid}: iteration {it.get('iterationNumber')} has no verdict (status {it.get('status')}{', refusal ' + it['refusal'] if it.get('refusal') else ''})")
                continue
            tools = [t["toolName"] for t in it.get("toolCalls") or []]
            failed = [sc["scorerId"] for sc in it.get("scores") or [] if sc.get("passed") is False]
            recs.append({"bank_id": bid, "harness": "mcpjam", "passed": tv == "passed", "tools": tools, "tool_count": len(tools), "failed_checks": sorted(set(failed))})
    return recs, notes


def collect_mcpeval_report(report: dict) -> tuple[list[dict], list[str]]:
    """mcp-eval EvaluationReport.to_dict(): results[] with case_name, passed,
    metrics.tool_calls (a count only) and evaluation_results[]. Tool names come
    from our FirstToolIn / ToolSequence evaluators' details.sequence."""
    recs, notes = [], []
    for r in report.get("results") or []:
        bid = _bank_id(r)
        if not bid:
            continue
        seq: list[str] | None = None
        failed = []
        for ev in r.get("evaluation_results") or []:
            res = ev.get("result") if isinstance(ev.get("result"), dict) else {}
            det = res.get("details") if isinstance(res.get("details"), dict) else {}
            if isinstance(det.get("sequence"), list):
                seq = [str(x) for x in det["sequence"]]
            if ev.get("passed") is False:
                failed.append(ev.get("name") or "evaluator")
            if ev.get("error"):
                notes.append(f"{bid}: evaluator {ev.get('name')} errored: {str(ev['error'])[:120]}")
        if r.get("error"):
            notes.append(f"{bid}: case errored: {str(r['error'])[:120]}")
        count = _tool_count(r)
        if seq is None and count:
            notes.append(f"{bid}: report has a tool count but no sequence; was ToolSequence exported?")
        recs.append({"bank_id": bid, "harness": "mcp-eval", "passed": bool(r.get("passed")), "tools": seq or [], "tool_count": count if count is not None else (len(seq) if seq is not None else None), "failed_checks": sorted(set(failed))})
    return recs, notes


def collect_any(report, harness: str) -> tuple[list[dict], list[str]]:
    if isinstance(report, dict) and report.get("kind") == "eval-local-run" and isinstance(report.get("metadata"), dict) and "cases" in report["metadata"]:
        return collect_mcpjam_local(report)
    if isinstance(report, dict) and isinstance(report.get("results"), list) and any(isinstance(r, dict) and "evaluation_results" in r for r in report["results"]):
        return collect_mcpeval_report(report)
    return collect(report, harness), [f"{harness}: unrecognized report shape, read with the generic walker"]


def collect(report, harness: str) -> list[dict]:
    """Generic fallback: every per-case record in a report, keyed by bank id."""
    found: list[dict] = []

    def walk(o, depth=0):
        if isinstance(o, dict):
            bid = _bank_id(o)
            v = _verdict(o)
            if bid and v is not None:
                tools = _tool_sequence(o)
                count = _tool_count(o)
                if count is None and tools:
                    count = len(tools)
                found.append({"bank_id": bid, "harness": harness, "passed": v, "tools": tools, "tool_count": count, "failed_checks": _failed_checks(o)})
                return
            for x in o.values():
                walk(x, depth + 1)
        elif isinstance(o, list):
            for x in o:
                walk(x, depth + 1)

    walk(report)
    return found


def collect_probe(report) -> list[dict]:
    out = []
    for r in report.get("results", []):
        failed = [c["check"] for layer in r.get("layers", []) for c in layer.get("checks", []) if not c.get("passed")]
        out.append({"bank_id": r["bank_id"], "harness": "probe", "probe_strengths": [layer.get("assertion_strength", "unknown_legacy") for layer in r.get("layers", [])], "passed": bool(r.get("passed")), "tools": [], "tool_count": None, "failed_checks": failed})
    return out


def classify(q: dict, recs: list[dict]) -> str:
    """Name the failure pattern a person should look at first."""
    if all(r["passed"] for r in recs):
        return "pass"
    exp = q.get("expect") or {}
    tools = [t for r in recs for t in r["tools"][:1]]
    checks = " ".join(c for r in recs for c in r["failed_checks"]).lower()
    if any(r["harness"] == "probe" and not r["passed"] for r in recs):
        return "payload-wrong"
    if q["kind"] == "boundary":
        return "boundary-broken"
    if exp.get("first_tool_any_of") and tools and not set(tools) <= set(exp["first_tool_any_of"]):
        return "wrong-tool"
    model = [r for r in recs if r["harness"] != "probe"]
    if model and all(r.get("tool_count") == 0 for r in model):
        return "no-tool-used"
    if "toolcallcount" in checks or "toolcallsatmost" in checks:
        return "too-many-calls"
    return "answer-failed"


ADVICE = {
    "wrong-tool": "The model reached for a different tool. Tighten the expected tool's description, or the other tool's, so their boundary is clear.",
    "no-tool-used": "The model answered without the server. Either no tool looks relevant (a missing or misnamed tool) or the description hides what it can do.",
    "boundary-broken": "The answer crossed a line the product must not cross. Fix server instructions or the tool's refusal payload before anything else.",
    "payload-wrong": "The direct call returned the wrong thing. This is a data or API bug, not a model problem.",
    "too-many-calls": "The model needed a long chain of calls. Candidate for a composite tool or a better first tool.",
    "answer-failed": "Tools were called but the answer failed its checks. Read the transcript.",
}


def cmd_ingest(a) -> int:
    bank = dl.load_json(a.bank)
    by_id = {q["id"]: q for q in bank["questions"]}
    personas = {p["id"]: p["name"] for p in bank["personas"]}
    recs: list[dict] = []
    notes: list[str] = []
    for path, harness in [(p, "mcpjam") for p in a.mcpjam or []] + [(p, "mcp-eval") for p in a.mcpeval or []]:
        got, nts = collect_any(dl.load_json(path), harness)
        recs += got
        notes += nts
    for path in a.probe or []:
        recs += collect_probe(dl.load_json(path))
    unknown = sorted({r["bank_id"] for r in recs if r["bank_id"] not in by_id})
    grouped: dict[str, list[dict]] = defaultdict(list)
    for r in recs:
        if r["bank_id"] in by_id:
            grouped[r["bank_id"]].append(r)
    if not grouped:
        print("ERROR no per-case results carrying a bank id were found in the reports", file=sys.stderr)
        return 2

    rows = []
    proposals = []
    for qid, rs in sorted(grouped.items()):
        q = by_id[qid]
        pattern = classify(q, rs)
        rate = sum(r["passed"] for r in rs) / len(rs)
        model_rs = [r for r in rs if r["harness"] != "probe"]
        firsts = Counter(r["tools"][0] for r in model_rs if r["tools"])
        rows.append({"q": q, "pattern": pattern, "rate": rate, "n": len(rs), "harnesses": sorted({r["harness"] for r in rs}), "firsts": firsts})
        if q["mode"] == "discovery" and pattern == "pass" and firsts and len(model_rs) >= a.min_runs:
            tool, count = firsts.most_common(1)[0]
            if count / len(model_rs) >= a.stability:
                proposals.append({"bank_id": qid, "action": "promote-to-strict", "set": {"mode": "strict", "expect.first_tool_any_of": [tool]}, "why": f"Passed all {len(model_rs)} model runs and chose {tool} first in {count}. Promoting makes that choice a regression test.", "needs_why": True})
        if q["mode"] == "discovery" and pattern == "no-tool-used":
            proposals.append({"bank_id": qid, "action": "tool-gap", "set": {}, "why": "No run used any tool. Record as a candidate missing capability; do not change the bank until a tool exists."})

    lines = [f"# Gap report: {bank['product']}", "", f"Ingested {len(recs)} case results across {len(grouped)} questions on {_dt.date.today().isoformat()}.", ""]
    strengths = Counter(x for r in recs for x in r.get('probe_strengths',[]))
    if strengths:
        lines += ['## Probe assertion coverage', '', 'A pass reflects the recorded assertions, not proof of answer quality. Legacy reports have unknown assertion strength.', '', '| Strength | Layers |', '|---|---|']
        lines += [f'| {kind} | {strengths[kind]} |' for kind in ('structured','content','negative_only','liveness','unknown_legacy') if strengths[kind]]
        lines += ['']
    if unknown:
        lines += [f"Results for ids not in this bank (stale export?): {', '.join(unknown)}.", ""]
    counts = Counter(r["pattern"] for r in rows)
    lines += ["## Failure patterns", "", "| Pattern | Questions | What to do |", "|---|---|---|"]
    for pat in ["boundary-broken", "payload-wrong", "wrong-tool", "no-tool-used", "too-many-calls", "answer-failed"]:
        if counts.get(pat):
            lines.append(f"| {pat} | {counts[pat]} | {ADVICE[pat]} |")
    lines.append(f"| pass | {counts.get('pass', 0)} | |")
    for pid, pname in personas.items():
        mine = [r for r in rows if r["q"]["persona"] == pid]
        if not mine:
            continue
        lines += ["", f"## {pname}", "", "| Question | Evidence | Mode | Pass rate | Pattern | First tool seen |", "|---|---|---|---|---|---|"]
        for r in sorted(mine, key=lambda r: (r["pattern"] == "pass", r["q"]["id"])):
            q = r["q"]
            first = ", ".join(f"{t} x{c}" for t, c in r["firsts"].most_common(2)) or "none"
            text = q["text"].replace("|", "/")
            lines.append(f"| {q['id']} {text[:90]} | {q['evidence']['class']} | {q['mode']} | {r['rate']:.0%} of {r['n']} | {r['pattern']} | {first} |")
    if notes:
        lines += ["", "## Harness notes", ""] + [f"- {n}" for n in sorted(set(notes))]
    lines += ["", f"## Proposals ({len(proposals)})", "", "Written to proposals.json. Nothing is applied until a named person runs `results.py apply`."]
    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    with open(a.out, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")
    dl.dump_json({"bank_hash": dl.sha256_file(a.bank), "proposals": proposals}, os.path.join(os.path.dirname(os.path.abspath(a.out)), "proposals.json"))
    print(f"questions={len(grouped)} " + " ".join(f"{k}={v}" for k, v in sorted(counts.items())) + f" proposals={len(proposals)}")
    return 0


def cmd_apply(a) -> int:
    if not dl.named_person(a.approver):
        print("ERROR --approver must be a named person (first and last name)", file=sys.stderr)
        return 2
    doc = dl.load_json(a.proposals)
    if doc.get("bank_hash") != dl.sha256_file(a.bank):
        print("ERROR the bank changed after these proposals were written; re-run ingest", file=sys.stderr)
        return 2
    bank = dl.load_json(a.bank)
    props = doc["proposals"]
    by_id = {q["id"]: q for q in bank["questions"]}
    applied = 0
    for p in props:
        if p["bank_id"] not in a.ids:
            continue
        if not p.get("set"):
            continue
        q = by_id.get(p["bank_id"])
        if q is None:
            continue
        for key, val in p["set"].items():
            if key.startswith("expect."):
                q.setdefault("expect", {})[key.split(".", 1)[1]] = val
            else:
                q[key] = val
        if p.get("needs_why") and not q.get("why"):
            q["why"] = f"Promoted from discovery: {p['why']}"
        q.setdefault("history", []).append({"action": p["action"], "approved_by": a.approver, "on": _dt.date.today().isoformat(), "why": p["why"]})
        applied += 1
    rep = dl.validate_bank(bank)
    if not rep.ok:
        for f in rep.errors:
            print(f)
        print("REJECTED: applying these proposals would make the bank invalid; nothing written")
        return 1
    dl.dump_json(bank, a.bank)
    print(f"applied={applied} by {a.approver}")
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("ingest")
    p.add_argument("--bank", required=True)
    p.add_argument("--capability-map")
    p.add_argument("--out", required=True)
    p.add_argument("--mcpjam", nargs="*")
    p.add_argument("--mcpeval", nargs="*")
    p.add_argument("--probe", nargs="*")
    p.add_argument("--min-runs", type=int, default=3)
    p.add_argument("--stability", type=float, default=0.8)
    p = sub.add_parser("apply")
    p.add_argument("--bank", required=True)
    p.add_argument("--proposals", required=True)
    p.add_argument("--approver", required=True)
    p.add_argument("--ids", nargs="+", required=True, help="the proposals this person read and approved; there is no approve-all")
    a = ap.parse_args(argv)
    return cmd_ingest(a) if a.cmd == "ingest" else cmd_apply(a)


if __name__ == "__main__":
    sys.exit(main())
