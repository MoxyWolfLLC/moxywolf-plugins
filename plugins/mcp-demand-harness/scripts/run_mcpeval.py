#!/usr/bin/env python3
"""Load (and optionally run) exported mcp-eval datasets with the custom
evaluators registered.

    run_mcpeval.py --dir <export dir> --check            # load + verify, no network
    run_mcpeval.py --dir <export dir> --run strict       # run one dataset

Run from an environment with `pip install "mcpevals==0.1.10" "mcp<2"`.

--check is the handoff test: it proves every case loads and that every
evaluator named in the YAML resolved to a class. mcp-eval's loader skips unknown
names without a word, so a count mismatch here is a check that would never
have run, and this script fails on it.

--run makes real calls: model API spend, and traffic to the configured MCP
target. The target is whatever mcpeval.yaml names; run the exporter with
--target production only after a named approval (see GOVERNANCE.md).
"""

from __future__ import annotations

import argparse
import asyncio
import glob
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)


def _yaml_evaluator_counts(path: str) -> dict[str, int]:
    """Count evaluator entries per case straight from the YAML text.

    The exporter writes a fixed shape, so the count is read without a YAML
    library: each case's `evaluators:` list items are `- <Name>:` lines.
    """
    counts: dict[str, int] = {}
    case = None
    in_ev = False
    ev_indent = None
    for line in open(path, encoding="utf-8"):
        m = re.match(r'^\s*- name: "?([^"]+)"?\s*$', line)
        if m:
            case = m.group(1)
            counts[case] = 0
            in_ev = False
            continue
        if re.match(r"^\s*evaluators:\s*$", line):
            in_ev = True
            ev_indent = None
            continue
        if in_ev and case:
            m = re.match(r"^(\s*)- ([A-Za-z]+):", line)
            if m:
                if ev_indent is None:
                    ev_indent = len(m.group(1))
                if len(m.group(1)) == ev_indent:
                    counts[case] += 1
            elif line.strip() and ev_indent is not None and (len(line) - len(line.lstrip())) < ev_indent:
                in_ev = False
    return counts


def check(dirpath: str) -> int:
    import mcpeval_evaluators  # noqa: F401  registers custom evaluators
    from mcp_eval.datasets import Dataset

    if not mcpeval_evaluators.HAVE_MCP_EVAL:
        print("ERROR mcp-eval is not importable here", file=sys.stderr)
        return 3
    bad = 0
    files = sorted(glob.glob(os.path.join(dirpath, "*.dataset.yaml")))
    if not files:
        print("ERROR no *.dataset.yaml files", file=sys.stderr)
        return 2
    for f in files:
        ds = Dataset.from_file(f)
        expected = _yaml_evaluator_counts(f)
        loaded = {c.name: len(c.evaluators) for c in ds.cases}
        dropped = {k: (expected.get(k, 0), v) for k, v in loaded.items() if expected.get(k, 0) != v}
        missing_cases = set(expected) - set(loaded)
        print(f"{os.path.basename(f)}: cases={len(ds.cases)} evaluators={sum(loaded.values())}")
        for k, (want, got) in sorted(dropped.items()):
            print(f"  DROPPED {k}: yaml has {want} evaluators, mcp-eval loaded {got}")
            bad += 1
        for k in sorted(missing_cases):
            print(f"  MISSING case {k}")
            bad += 1
    print("OK" if not bad else f"FAIL {bad} problems")
    return 0 if not bad else 1


def run(dirpath: str, which: str, out_prefix: str | None) -> int:
    import mcpeval_evaluators  # noqa: F401
    from mcp_eval.datasets import Dataset

    rc = check(dirpath)
    if rc:
        return rc
    for mp in glob.glob(os.path.join(dirpath, "*-mcpeval-mapping.json")):
        with open(mp, encoding="utf-8") as fh:
            m = json.load(fh)
        if m.get("requires_named_approval") and not m.get("approved_by"):
            print(f"REFUSED {os.path.basename(mp)}: target {m.get('target')} needs a named approver; re-export with --approver", file=sys.stderr)
            return 2
        print(f"target {m.get('target')} {m.get('target_url')}" + (f" approved by {m['approved_by']}" if m.get("approved_by") else ""))
    files = [f for f in glob.glob(os.path.join(dirpath, f"*-{which}.dataset.yaml"))]
    if len(files) != 1:
        print(f"ERROR expected one *-{which}.dataset.yaml, found {len(files)}", file=sys.stderr)
        return 2
    os.chdir(dirpath)  # mcp-eval reads mcpeval.yaml / mcpeval.secrets.yaml from cwd
    ds = Dataset.from_file(os.path.basename(files[0]))

    async def task(inputs, agent, session):
        return await agent.generate_str(inputs)

    report = asyncio.run(ds.evaluate(task))
    prefix = out_prefix or f"test-reports/{which}"
    os.makedirs(os.path.dirname(prefix) or ".", exist_ok=True)
    with open(f"{prefix}.json", "w", encoding="utf-8") as fh:
        json.dump(report.to_dict(), fh, indent=2, default=_jsonable)
    print(f"{report.passed_cases}/{report.total_cases} passed; report {prefix}.json")
    return 0


def _jsonable(o):
    """to_dict() leaves EvaluatorResult as a pydantic object. default=str would
    flatten it to a repr and lose details.sequence, which results.py reads."""
    if hasattr(o, "model_dump"):
        return o.model_dump(mode="json")
    return str(o)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--dir", required=True)
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--check", action="store_true")
    g.add_argument("--run", choices=["strict", "discovery"])
    ap.add_argument("--out", help="report path prefix (default test-reports/<dataset>)")
    a = ap.parse_args(argv)
    return check(a.dir) if a.check else run(a.dir, a.run, a.out)


if __name__ == "__main__":
    sys.exit(main())
