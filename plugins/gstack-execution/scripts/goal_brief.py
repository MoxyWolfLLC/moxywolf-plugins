#!/usr/bin/env python3
"""GO-001: a goal is a brief Dorian approved, under one objective, and the approval binds to one tree.

  goal_brief.py check <goal dir> [--design DESIGN.md] [--codeowners .github/CODEOWNERS]
  goal_brief.py verify <id> --pr N [--repo owner/name] [--owner login]   (needs GITHUB_TOKEN;
                run it under `agent_token.py exec --`)
  goal_brief.py --selftest

`check` reads the brief, the plan and the folder against the limits below, which are the
project charter's limits as code: a brief outside them is refused, not negotiated (criterion 5).
It reports how many sections and files it examined, and examining none is a failure (EV-001).
`verify` reads the approving review through the GitHub API and prints the run-record fields.
"""
import json
import math
import os
import re
import subprocess
import sys
import urllib.request
from fnmatch import fnmatchcase
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / ".github"))
from test_codeowners import owners, rules  # noqa: E402  one CODEOWNERS matcher, not two

SECTIONS = ["Serves", "Outcome", "Non-goals", "Scenarios", "Goal tests", "Allowed paths",
            "Spend cap", "Provider budgets", "Max calls", "Max items",
            "Max review rounds per item", "Stop conditions", "Pre-mortem"]
FILES = ["GOAL.md", "PLAN.md", "holdout.sha256"]
NOT_OBJECTIVES = {"Goal", "Constraints and settled decisions", "Boundary tests", "Validation",
                  "Amendments log"}


def sections(text):
    out, cur = {}, None
    for line in text.splitlines():
        m = re.match(r"^##\s+(.+?)\s*$", line)
        if m:
            cur = m.group(1)
            out[cur] = []
        elif cur is not None:
            out[cur].append(line)
    return {k: "\n".join(v).strip() for k, v in out.items()}


def bullets(body):
    return [re.sub(r"^\s*(?:[-*]|\d+\.)\s+", "", l).strip().strip("`")
            for l in body.splitlines() if re.match(r"^\s*(?:[-*]|\d+\.)\s+", l)]


def number(body):
    m = re.search(r"-?\d+(?:\.\d+)?", body.replace(",", ""))
    return float(m.group()) if m else None


def objectives(design_text):
    heads = re.findall(r"^## (.+?)\s*$", design_text, re.M)
    return [h for h in heads if h not in NOT_OBJECTIVES]


def owned_probes(rs, tracked):
    # ponytail: an allowed glob overlaps the gate when it matches any owned tracked file, or a
    # probe file inside an owned directory pattern. fnmatch's * crosses "/", which errs toward refusing.
    probes = [p for p in tracked if owners(rs, p)]
    for pattern, _ in rs:
        p = pattern.lstrip("/")
        probes.append((p[3:] if p.startswith("**/") else p) + ("probe" if p.endswith("/") else ""))
    return probes


def check(goal_dir, design_text, codeowners_text, tracked):
    goal_dir = Path(goal_dir)
    errors, examined = [], 0
    for f in FILES:
        if (goal_dir / f).is_file():
            examined += 1
        else:
            errors.append(f"missing file: {f}")
    if not (goal_dir / "tests").is_dir() or not any((goal_dir / "tests").iterdir()):
        errors.append("missing or empty tests/")
    else:
        examined += 1
    brief = sections((goal_dir / "GOAL.md").read_text()) if (goal_dir / "GOAL.md").is_file() else {}
    for s in SECTIONS:
        if brief.get(s):
            examined += 1
        else:
            errors.append(f"missing or empty section: {s}")

    if brief.get("Serves") and brief["Serves"].splitlines()[0].strip() not in objectives(design_text):
        errors.append(f"Serves names no objective in DESIGN.md: {brief['Serves'].splitlines()[0].strip()}")

    rs = rules(codeowners_text)
    probes = owned_probes(rs, tracked)
    for g in bullets(brief.get("Allowed paths", "")):
        hit = next((p for p in probes if fnmatchcase(p, g)), None)
        if hit:
            errors.append(f"Allowed path {g} reaches a CODEOWNERS path ({hit}); a brief only narrows the charter")

    def bounded(name, lo, hi, integer=True):
        v = number(brief.get(name, ""))
        if v is None or (integer and v != int(v)) or not lo <= v <= hi:
            errors.append(f"{name} must be {'an integer ' if integer else ''}from {lo} to {hi}, got {brief.get(name, '').strip() or 'nothing'}")
            return None
        return v

    max_items = bounded("Max items", 1, 10)
    bounded("Max review rounds per item", 1, 3)
    cap = bounded("Spend cap", 1e-9, math.inf, integer=False)
    bounded("Max calls", 1, math.inf)
    total = 0.0
    for line in bullets(brief.get("Provider budgets", "")):
        v = number(line.split(":", 1)[-1])
        if v is None or not math.isfinite(v) or v <= 0:
            errors.append(f"Provider budget must be a finite positive number: {line}")
        else:
            total += v
    if cap is not None and total > cap:
        errors.append(f"Provider budgets sum to {total:g}, more than the Spend cap {cap:g}")

    if (goal_dir / "PLAN.md").is_file() and max_items is not None:
        n = len([l for l in (goal_dir / "PLAN.md").read_text().splitlines() if re.match(r"^\d+\.\s", l)])
        if n == 0:
            errors.append("PLAN.md lists no items")
        elif n > max_items:
            errors.append(f"PLAN.md lists {n} items, more than Max items {max_items:g}")
    return errors, examined


def github(token):
    def get(path):
        req = urllib.request.Request("https://api.github.com/" + path, headers={
            "Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json"})
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.load(r)
    return get


def verify(goal_id, pr, repo, owner, get):
    """Criterion 3. Returns (record, errors)."""
    errors = []
    p = get(f"repos/{repo}/pulls/{pr}")
    head = p["head"]["sha"]
    if not p.get("merged"):
        errors.append(f"PR #{pr} is not merged")
    mine = [r for r in get(f"repos/{repo}/pulls/{pr}/reviews?per_page=100")
            if r["user"]["login"] == owner and r["state"] in ("APPROVED", "CHANGES_REQUESTED", "DISMISSED")]
    last = mine[-1] if mine else None   # his latest decision stands; a later dismissal undoes an approval
    if not last or last["state"] != "APPROVED":
        errors.append(f"no standing APPROVED review by {owner} on PR #{pr}")
    elif last["commit_id"] != head:
        errors.append(f"{owner}'s approval is at {last['commit_id'][:7]}, not the head {head[:7]}")

    def tree(ref):
        hit = [e for e in get(f"repos/{repo}/contents/goals?ref={ref}") if e["name"] == goal_id]
        return hit[0]["sha"] if hit and hit[0]["type"] == "dir" else None
    at_head, at_main = tree(head), tree(p["base"]["ref"])
    if at_head is None:
        errors.append(f"goals/{goal_id}/ does not exist at the head")
    elif at_head != at_main:
        errors.append(f"goals/{goal_id}/ on {p['base']['ref']} ({(at_main or 'missing')[:7]}) differs from the approved tree ({at_head[:7]})")
    record = {"goal": goal_id, "pr": pr, "review_id": last["id"] if last else None,
              "head": head, "tree": at_head}
    return record, errors


def main(argv):
    if argv[:1] == ["--selftest"]:
        return selftest()
    if argv[:1] == ["check"] and len(argv) >= 2:
        args = dict(zip(argv[2::2], argv[3::2]))
        design = Path(args.get("--design", ROOT / "DESIGN.md")).read_text()
        co = Path(args.get("--codeowners", ROOT / ".github/CODEOWNERS")).read_text()
        tracked = subprocess.run(["git", "-C", str(ROOT), "ls-files"], capture_output=True,
                                 text=True).stdout.splitlines()
        errors, examined = check(argv[1], design, co, tracked)
        print(f"examined {examined} sections and files in {argv[1]}")
        if examined == 0:
            errors.append("examined nothing")
        for e in errors:
            print("FAIL:", e)
        return 1 if errors else 0
    if argv[:1] == ["verify"] and len(argv) >= 2:
        args = dict(zip(argv[2::2], argv[3::2]))
        token = os.environ.get("GITHUB_TOKEN")
        if not token or "--pr" not in args:
            print("verify needs --pr N and GITHUB_TOKEN (run under agent_token.py exec --)")
            return 2
        record, errors = verify(argv[1], int(args["--pr"]), args.get("--repo", "MoxyWolfLLC/moxywolf-plugins"),
                                args.get("--owner", "dorianatmoxywolf"), github(token))
        print(json.dumps(record))
        for e in errors:
            print("FAIL:", e)
        return 1 if errors else 0
    print(__doc__)
    return 2


def selftest():
    import tempfile
    design = "## Goal\nx\n## Eleventh objective: goal mode\ny\n## Amendments log\n"
    co = "/.github/ @d\n/plugins/gstack-execution/scripts/peer_review.py @d\n/goals/ @d\n"
    with tempfile.TemporaryDirectory() as t:
        g = Path(t, "g1")
        (g / "tests").mkdir(parents=True)
        (g / "tests" / "test_x.py").write_text("")
        (g / "holdout.sha256").write_text("0" * 64)
        (g / "PLAN.md").write_text("1. one\n2. two\n")
        body = {s: "1" for s in SECTIONS}
        body.update({"Serves": "Eleventh objective: goal mode", "Allowed paths": "- plugins/foo/**",
                     "Provider budgets": "- openrouter: 3\n- gemini: 2", "Spend cap": "$5", "Max items": "3"})
        (g / "GOAL.md").write_text("".join(f"## {k}\n{v}\n\n" for k, v in body.items()))
        errs, n = check(g, design, co, [])
        assert errs == [] and n == len(FILES) + 1 + len(SECTIONS), (errs, n)
        errs, _ = check(g, design.replace("Eleventh", "Twelfth"), co, [])
        assert any("Serves names no objective" in e for e in errs)
    return print("selftest: 2 checks passed") or 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
