#!/usr/bin/env python3
"""Export the bank as mcp-eval datasets plus the config to run them.

    export_mcpeval.py --bank B --capability-map M --profile P --out <dir> [--target staging]
                      [--include-drafts]

Writes:
  mcpeval.yaml                      server binding, default agent, judge, reporting
  mcpeval.secrets.yaml.example      where the API token and model key go (never filled in)
  <product>-strict.dataset.yaml     checked expectations
  <product>-discovery.dataset.yaml  liveness only; failures point at missing tools
  <product>-mcpeval-mapping.json    per-question mapping and what was skipped

Traps in mcp-eval 0.1.10 this exporter avoids on purpose:
  * Unknown evaluator names are dropped without an error. Every evaluator
    written here is either built in or registered by mcpeval_evaluators.py,
    and run_mcpeval.py refuses to run if any name failed to resolve.
  * An inline `agent_spec:` mapping in a dataset is ignored. The agent is
    declared once as `default_agent` in mcpeval.yaml instead.
  * Case-insensitive regex lower-cases the pattern, which turns \\S into \\s.
    Patterns are written case-sensitive with a leading (?i) instead.
  * mcp-eval's dependency mcp-agent imports mcp.server.fastmcp, which MCP
    Python SDK 2.x renamed.
    Install with `mcp<2` (see the README).

Mapping rules (bank -> mcp-eval):
  E-1 first_tool_any_of -> FirstToolIn(tool_names)        custom, exact
  E-2 must_call t       -> ToolWasCalled(t)
  E-3 must_not_call t   -> ExactToolCount(t, 0)
  E-4 must_contain s    -> ResponseContains(s, case_sensitive=false)
  E-5 must_not_match p  -> NotContains("(?i)"+p, regex=true, case_sensitive=true)
  E-6 max_tool_calls n  -> ToolCallsAtMost(n)               custom, exact
  E-7 rubric            -> LLMJudge(rubric, min_score)       native judge
  E-8 discovery         -> AnsweredWithoutToolErrors         custom
  E-9 every case        -> ToolSequence                      custom recorder, always passes
"""

from __future__ import annotations

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import demandlib as dl  # noqa: E402

CONVERTER = f"{dl.PLUGIN_NAME}/export_mcpeval"
BUILTIN = {"ToolWasCalled", "ExactToolCount", "ResponseContains", "NotContains", "LLMJudge"}
CUSTOM = {"ToolSequence", "FirstToolIn", "ToolCallsAtMost", "AnsweredWithoutToolErrors"}


def map_question(q: dict, persona_name: str, min_score: float) -> tuple[dict, list[str]]:
    exp = q.get("expect") or {}
    ev: list[dict] = []
    rules: list[str] = []
    if exp.get("first_tool_any_of"):
        ev.append({"FirstToolIn": {"tool_names": list(exp["first_tool_any_of"])}})
        rules.append("E-1")
    for t in exp.get("must_call") or []:
        ev.append({"ToolWasCalled": {"tool_name": t}})
        rules.append("E-2")
    for t in exp.get("must_not_call") or []:
        ev.append({"ExactToolCount": {"tool_name": t, "expected_count": 0}})
        rules.append("E-3")
    for s in exp.get("must_contain") or []:
        ev.append({"ResponseContains": {"text": s, "case_sensitive": False}})
        rules.append("E-4")
    for entry in exp.get("must_not_match") or []:
        pat, cs = dl.pattern_parts(entry)
        ev.append({"NotContains": {"text": pat if cs else "(?i)" + pat, "regex": True, "case_sensitive": True}})
        rules.append("E-5")
    if exp.get("max_tool_calls"):
        ev.append({"ToolCallsAtMost": {"max_calls": int(exp["max_tool_calls"])}})
        rules.append("E-6")
    if exp.get("rubric"):
        ev.append({"LLMJudge": {"rubric": exp["rubric"], "min_score": min_score}})
        rules.append("E-7")
    if q["mode"] == "discovery":
        ev.append({"AnsweredWithoutToolErrors": {}})
        rules.append("E-8")
    if not any("FirstToolIn" in e for e in ev):
        ev.append({"ToolSequence": {}})
        rules.append("E-9")
    case = {
        "name": q["id"],
        "inputs": "\n\n".join([q["text"]] + list(q.get("turns") or [])),
        "metadata": {
            "bank_id": q["id"],
            "persona": q["persona"],
            "persona_name": persona_name,
            "evidence_class": q["evidence"]["class"],
            "evidence_source": q["evidence"]["source"],
            "mode": q["mode"],
            "kind": q["kind"],
            "priority": q.get("priority", 2),
            "rules": sorted(set(rules), key=rules.index),
        },
        "evaluators": ev,
    }
    if q.get("turns"):
        case["metadata"]["note"] = "Follow-up turns are concatenated into one input; mcp-eval datasets are single-turn."
    return case, rules


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--bank", required=True)
    ap.add_argument("--capability-map", required=True)
    ap.add_argument("--profile", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--target", default="staging")
    ap.add_argument("--approver", help="named person approving eval traffic to a target marked requires_named_approval")
    ap.add_argument("--include-drafts", action="store_true")
    ap.add_argument("--min-score", type=float, default=0.8)
    ap.add_argument("--max-iterations", type=int, default=8)
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
    target = (profile.get("targets") or {}).get(a.target)
    if not target:
        print(f"ERROR profile has no target {a.target!r}", file=sys.stderr)
        return 2
    if target.get("requires_named_approval") and not dl.named_person(a.approver):
        print(f"REFUSED target {a.target} requires --approver \"First Last\": this config sends eval traffic there", file=sys.stderr)
        return 2

    product = bank["product"]
    server = cmap["mcp"]["server_name"]
    personas = {p["id"]: p["name"] for p in bank["personas"]}
    models = profile.get("models") or {}

    datasets: dict[str, list[dict]] = {"strict": [], "discovery": []}
    mapping: list[dict] = []
    for q in bank["questions"]:
        if "mcp" not in (q.get("surfaces") or []):
            continue
        ok, why = dl.runnable(q, a.include_drafts)
        if not ok:
            mapping.append({"bank_id": q["id"], "emitted": False, "reason": why})
            continue
        case, rules = map_question(q, personas.get(q["persona"], q["persona"]), a.min_score)
        if not case["evaluators"]:
            mapping.append({"bank_id": q["id"], "emitted": False, "reason": "no expectation maps to mcp-eval"})
            continue
        datasets[q["mode"]].append(case)
        mapping.append({"bank_id": q["id"], "emitted": True, "dataset": q["mode"], "rules": case["metadata"]["rules"]})

    os.makedirs(a.out, exist_ok=True)
    auth = profile.get("auth") or {}
    config = {
        "name": f"{product} demand bank",
        "description": f"Generated by {CONVERTER} {dl.PLUGIN_VERSION}. Target: {a.target}.",
        "provider": models.get("mcp_eval_provider", "anthropic"),
        "model": models.get("mcp_eval_model", "claude-sonnet-5"),
        "default_agent": {
            "name": f"{product}_demand_agent",
            "instruction": f"You are helping a {product} customer. Use the {server} tools to answer. If the product does not hold something, say so plainly instead of guessing.",
            "server_names": [server],
            "max_iterations": a.max_iterations,
        },
        "judge": {"min_score": a.min_score},
        "reporting": {"formats": ["json", "markdown"], "output_dir": "./test-reports", "include_traces": True},
        "execution": {"max_concurrency": 2, "timeout_seconds": 300},
        "mcp": {"servers": {server: {"transport": "streamable_http", "url": target["mcp_url"]}}},
    }
    dl.write_yaml(config, os.path.join(a.out, "mcpeval.yaml"), header=f"GENERATED by {CONVERTER} {dl.PLUGIN_VERSION}. Target {a.target}: {target['mcp_url']}\nSecrets (API token, model key) go in mcpeval.secrets.yaml, which must stay out of git.")
    secrets = {
        "anthropic": {"api_key": "<ANTHROPIC_API_KEY>"},
        "mcp": {"servers": {server: {"headers": {auth.get("header", "Authorization"): f"{auth.get('scheme', 'Bearer')} <{auth.get('token_env', 'API_TOKEN')}>"}}}},
    }
    dl.write_yaml(secrets, os.path.join(a.out, "mcpeval.secrets.yaml.example"), header="Copy to mcpeval.secrets.yaml and fill in. Never commit the filled file.\n" + (auth.get("note") or ""))
    with open(os.path.join(a.out, ".gitignore"), "w", encoding="utf-8") as fh:
        fh.write("mcpeval.secrets.yaml\ntest-reports/\n")

    for mode, cases in datasets.items():
        if not cases:
            continue
        doc = {
            "name": f"{product} demand ({mode})",
            "description": f"From {os.path.basename(a.bank)} {dl.sha256_file(a.bank)}. Custom evaluators require run_mcpeval.py.",
            "server_name": server,
            "cases": cases,
        }
        path = os.path.join(a.out, f"{product}-{mode}.dataset.yaml")
        dl.write_yaml(doc, path, header=f"GENERATED by {CONVERTER} {dl.PLUGIN_VERSION}. Do not edit; edit the bank and re-export.\nRun with run_mcpeval.py, not `mcp-eval dataset`: the custom evaluators must be registered first.")
        print(f"wrote {path} cases={len(cases)}")
    dl.dump_json({"converter": CONVERTER, "converter_version": dl.PLUGIN_VERSION, "bank_hash": dl.sha256_file(a.bank), "target": a.target, "target_url": target["mcp_url"], "requires_named_approval": bool(target.get("requires_named_approval")), "approved_by": a.approver if target.get("requires_named_approval") else None, "cases": mapping}, os.path.join(a.out, f"{product}-mcpeval-mapping.json"))
    print(f"skipped={sum(1 for m in mapping if not m['emitted'])}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
