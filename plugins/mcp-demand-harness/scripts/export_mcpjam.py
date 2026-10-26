#!/usr/bin/env python3
"""Export the bank as MCPJam v6 eval suites (schemaVersion "2").

    export_mcpjam.py --bank B --capability-map M --profile P --out <repo>/.mcpjam/evals
                     [--include-drafts]

Writes one suite per mode (`<product>-strict.yaml`, `<product>-discovery.yaml`)
plus `<product>-mapping-report.json`. Every case carries an `import` block,
because each one is converted from the bank rather than authored in MCPJam:

  exact         every bank expectation maps to a deterministic MCPJam predicate
                with the same meaning. The note cites the rule (M-1..M-7).
  approximated  something could not be carried over identically (an any-of
                tool choice, a judge rubric). The case is written `disabled`;
                MCPJam runs it only with --allow-approximated <id> and a reason,
                which is the human gate on lossy conversion.

Questions that are parked, drafts, or still need customer input are not
emitted; the mapping report lists each with its reason.

Mapping rules (bank -> MCPJam), cited in import notes:
  M-1 first_tool_any_of [t]   -> firstToolWas t
  M-2 must_call t             -> toolCalledAtLeastOnce t
  M-3 must_not_call t         -> toolNeverCalled t
  M-4 must_contain s          -> responseContains s (case-insensitive, as in the bank)
  M-5 must_not_match p        -> responseMatches ^(?![\\s\\S]*(?:p'))[\\s\\S]*$ where p' is
                                 p with ASCII letters case-folded into classes, since
                                 MCPJam regex takes no flags
  M-6 max_tool_calls n        -> toolCallCountUnder n+1
  M-7 discovery liveness      -> finalAssistantMessageNonEmpty + noToolErrors
Payload checks are not MCPJam assertions; they run in the REST probe, which
calls the tool's endpoint directly. Notes say so where it applies.
"""

from __future__ import annotations

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import demandlib as dl  # noqa: E402

CONVERTER = f"{dl.PLUGIN_NAME}/export_mcpjam"
MAX_TITLE = 200


def case_id(qid: str) -> str:
    return qid.lower()


def map_question(q: dict, persona_name: str) -> tuple[dict, list[str], list[str]]:
    """Return (case, rules_applied, losses)."""
    exp = q.get("expect") or {}
    rules: list[str] = []
    losses: list[str] = []
    assertions: list[dict] = []

    tools_any = exp.get("first_tool_any_of") or []
    if tools_any:
        assertions.append({"type": "firstToolWas", "toolName": tools_any[0]})
        rules.append("M-1")
        if len(tools_any) > 1:
            losses.append(f"bank accepts any of {tools_any} as the first tool; MCPJam has no any-of predicate, so only {tools_any[0]} passes")
    for t in exp.get("must_call") or []:
        assertions.append({"type": "toolCalledAtLeastOnce", "toolName": t})
        rules.append("M-2")
    for t in exp.get("must_not_call") or []:
        assertions.append({"type": "toolNeverCalled", "toolName": t})
        rules.append("M-3")
    for s in exp.get("must_contain") or []:
        assertions.append({"type": "responseContains", "needle": s})
        rules.append("M-4")
    for entry in exp.get("must_not_match") or []:
        pat, cs = dl.pattern_parts(entry)
        assertions.append({"type": "responseMatches", "pattern": dl.negative_whole_response(pat if cs else dl.js_case_fold(pat))})
        rules.append("M-5")
    if exp.get("max_tool_calls"):
        assertions.append({"type": "toolCallCountUnder", "count": int(exp["max_tool_calls"]) + 1})
        rules.append("M-6")
    if q["mode"] == "discovery":
        assertions.append({"type": "finalAssistantMessageNonEmpty"})
        assertions.append({"type": "noToolErrors"})
        rules.append("M-7")

    case: dict = {
        "id": case_id(q["id"]),
        "title": f"{q['id']} {q['text']}"[:MAX_TITLE],
        # MCPJam's intent is an analytics grouping label (<=64 chars, trimmed),
        # not the question's intent prose. Group by persona and kind so a run
        # can be sliced the way the bank is reported.
        "intent": f"{q['persona']}:{q['kind']}"[:64].strip(),
        "scenario": f"Persona: {persona_name}. Evidence: {q['evidence']['class']} ({q['evidence']['source']}).",
        "kind": "regression" if q["mode"] == "strict" else "capability",
        "steps": [{"id": "step-1", "kind": "prompt", "prompt": q["text"]}]
        + [{"id": f"step-{i + 2}", "kind": "prompt", "prompt": t} for i, t in enumerate(q.get("turns") or [])],
    }
    if exp.get("rubric"):
        case["expectedOutput"] = exp["rubric"]
        losses.append("rubric is graded by MCPJam's model judge against expectedOutput, not by a deterministic check")
    if assertions:
        case["assertions"] = assertions
    return case, sorted(set(rules), key=rules.index), losses


def build(bank: dict, include_drafts: bool, bank_hash: str) -> tuple[dict[str, list[dict]], list[dict]]:
    personas = {p["id"]: p["name"] for p in bank["personas"]}
    suites: dict[str, list[dict]] = {"strict": [], "discovery": []}
    report: list[dict] = []
    for q in bank["questions"]:
        if "mcp" not in (q.get("surfaces") or []):
            continue
        ok, why = dl.runnable(q, include_drafts)
        if not ok:
            report.append({"bank_id": q["id"], "emitted": False, "reason": why})
            continue
        case, rules, losses = map_question(q, personas.get(q["persona"], q["persona"]))
        if not case.get("assertions") and not case.get("expectedOutput"):
            report.append({"bank_id": q["id"], "emitted": False, "reason": "no expectation maps to MCPJam"})
            continue
        payload_note = " Payload checks for this question run in the REST probe." if q.get("payload") else ""
        if losses:
            case["import"] = {"status": "approximated", "sourceCaseKey": f"questions[{q['id']}]", "note": ("; ".join(losses) + "." + payload_note)[:1000]}
            case["disabled"] = True
        else:
            case["import"] = {"status": "exact", "sourceCaseKey": f"questions[{q['id']}]", "note": (f"Rule-mapped by {', '.join(rules)} ({CONVERTER} {dl.PLUGIN_VERSION}); bank semantics carried over unchanged." + payload_note)[:1000]}
        suites[q["mode"]].append(case)
        report.append({"bank_id": q["id"], "emitted": True, "case_id": case["id"], "suite": q["mode"], "status": case["import"]["status"], "rules": rules, "losses": losses})
    return suites, report


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--bank", required=True)
    ap.add_argument("--capability-map", required=True)
    ap.add_argument("--profile", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--include-drafts", action="store_true")
    ap.add_argument("--iterations", type=int, default=3)
    ap.add_argument("--pass-threshold", type=float, default=0.67)
    a = ap.parse_args(argv)

    bank = dl.load_json(a.bank)
    cmap = dl.load_json(a.capability_map)
    profile = dl.load_profile(a.profile)
    rep = dl.validate_bank(bank, cmap["mcp"]["tool_names"], for_export=True, routes=[r["path"] for r in cmap["rest"]["routes"]])
    if not rep.ok:
        for f in rep.errors:
            print(f, file=sys.stderr)
        print("REFUSED: the bank does not validate for export", file=sys.stderr)
        return 1

    product = bank["product"]
    server = cmap["mcp"]["server_name"]
    model = (profile.get("models") or {}).get("mcpjam", "anthropic/claude-sonnet-4-6")
    bank_hash = dl.sha256_file(a.bank)
    suites, report = build(bank, a.include_drafts, bank_hash)

    os.makedirs(a.out, exist_ok=True)
    report_path = os.path.join(a.out, f"{product}-mapping-report.json")
    dl.dump_json(
        {
            "converter": CONVERTER,
            "converter_version": dl.PLUGIN_VERSION,
            "bank": os.path.basename(a.bank),
            "bank_hash": bank_hash,
            "capability_map_commit": cmap.get("source", {}).get("commit"),
            "rules": {
                "M-1": "first_tool_any_of [t] -> firstToolWas t",
                "M-2": "must_call -> toolCalledAtLeastOnce",
                "M-3": "must_not_call -> toolNeverCalled",
                "M-4": "must_contain -> responseContains (case-insensitive)",
                "M-5": "must_not_match -> responseMatches negative lookahead over the whole response, case-folded",
                "M-6": "max_tool_calls n -> toolCallCountUnder n+1",
                "M-7": "discovery -> finalAssistantMessageNonEmpty + noToolErrors",
            },
            "cases": report,
        },
        report_path,
    )
    report_hash = dl.sha256_file(report_path)

    written = []
    for mode, cases in suites.items():
        if not cases:
            continue
        doc = {
            "schemaVersion": "2",
            "mode": "agentWorkflow",
            "reportingMode": "standard",
            "suite": {
                "id": f"{product}-demand-{mode}",
                "name": f"{product} demand bank ({mode})",
                "description": (
                    "Regression: questions with checked expectations. Fails when tool choice or a boundary regresses."
                    if mode == "strict"
                    else "Capability discovery: no expected tools. Read failures and long tool chains as missing or misshapen tools."
                ),
            },
            "target": {"servers": [{"name": server}]},
            "defaults": {"model": model, "iterations": a.iterations, "passThreshold": a.pass_threshold, "validity": {}},
            "provenance": {
                "sourceFormat": "mcp-demand-bank",
                "sourceHash": bank_hash,
                "converter": CONVERTER,
                "converterVersion": dl.PLUGIN_VERSION,
                "reportHash": report_hash,
            },
            "cases": cases,
        }
        path = os.path.join(a.out, f"{product}-{mode}.yaml")
        dl.write_yaml(
            doc,
            path,
            header=f"GENERATED by {CONVERTER} {dl.PLUGIN_VERSION} from {os.path.basename(a.bank)}. Do not edit; edit the bank and re-export.\nValidate: npx -y @mcpjam/cli@6 cloud eval validate --file {os.path.basename(path)}",
        )
        written.append((path, len(cases), sum(1 for c in cases if c["import"]["status"] == "exact")))

    skipped = [r for r in report if not r["emitted"]]
    for path, n, exact in written:
        print(f"wrote {path} cases={n} exact={exact} approximated={n - exact}")
    print(f"wrote {report_path} skipped={len(skipped)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
