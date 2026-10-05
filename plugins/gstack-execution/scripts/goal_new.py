#!/usr/bin/env python3
"""GO-007: draft the parts of a goal folder the agent may not write itself.

The agent drafts GOAL.md and PLAN.md. The goal tests and the holdout come from another family, and the
plain-English reading from a third, so no one model writes the tests, explains them and builds against
them (GO-002, GO-003.3):

  goal_new.py tests <goal dir>    the goal tests, drafted by the gpt family through Codex
  goal_new.py holdout <goal dir>  the holdout, by the same family, written outside the repository with
                                  only its hash entering the folder; the source is never printed
  goal_new.py read <goal dir>     the plain-English reading, by the gemini family through OpenRouter,
                                  printed as the goal pull request's `## Plain-English reading` section

Each refuses (exit 1) rather than write a partial folder. `goal_brief.py check` and `baseline` still
decide whether the folder is a goal; nothing here replaces them.
"""
import hashlib
import os
import re
import subprocess
import sys
import tempfile
import urllib.request
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import goal_brief as gb  # noqa: E402
import goal_checks  # noqa: E402
import peer_review as pr  # noqa: E402

DRAFTER = ("gpt", pr.REVIEWERS["codex"]["model"])
READER_TOOL = "openrouter-gemini"
READER = ("gemini", pr.REVIEWERS[READER_TOOL]["model"])
FILE = re.compile(r"^=====FILE (tests/[\w.-]+\.py)=====\s*$", re.M)
RULES = """Goal tests never import the candidate and never open any file in the candidate's checkout. They run it as a
separate program from the checkout named by the GOAL_CANDIDATE environment variable, for example
subprocess.run([sys.executable, "path/to/tool.py", ...], cwd=os.environ["GOAL_CANDIDATE"], capture_output=True, text=True, timeout=120),
and judge only what it prints, its exit code, and what it writes outside its checkout (give it a temporary folder).
Anything the test needs from the repository is copied into the test as a literal, never read at run time.
stdlib unittest only."""


class Refused(SystemExit):
    def __init__(self, why):
        super().__init__(f"refused: {why}")


def holdouts():
    return Path(os.environ.get("GSTACK_GOAL_HOLDOUTS", "~/.goal-holdouts")).expanduser().resolve()


def load(goal_dir):
    """(goal dir, repo root, brief text, plan text, [(test id, kind)]). Refuses a brief with no goal tests."""
    g = Path(goal_dir).resolve()
    if g.parent.name != "goals" or not (g / "GOAL.md").is_file() or not (g / "PLAN.md").is_file():
        raise Refused(f"{goal_dir} is not goals/<id>/ with GOAL.md and PLAN.md")
    text, errors = (g / "GOAL.md").read_text(), []
    tests = gb.goal_tests(gb.sections(text).get("Goal tests", ""), errors)
    if errors or not tests:
        raise Refused("; ".join(errors) or "the brief names no goal tests")
    return g, g.parent.parent, text, (g / "PLAN.md").read_text(), tests


def unfence(s):
    s = s.strip()
    s = re.sub(r"^```[\w-]*\n", "", s)
    return re.sub(r"\n```$", "", s).strip() + "\n"


def codex(prompt, cwd, timeout=1500):
    """One Codex run, read-only in the repository. Returns its last message."""
    fd, last = tempfile.mkstemp(prefix="goal-new-", suffix=".txt")
    os.close(fd)
    try:
        r = subprocess.run(["codex", "exec", "-C", str(cwd), "-m", DRAFTER[1], "-c", "model_reasoning_effort=high",
                            "--sandbox", "read-only", "--skip-git-repo-check", "--output-last-message", last, prompt],
                           capture_output=True, text=True, stdin=subprocess.DEVNULL, timeout=timeout)
        out = Path(last).read_text()
    finally:
        Path(last).unlink(missing_ok=True)
    if not out.strip():
        raise Refused(f"codex returned nothing (rc {r.returncode}): {(r.stderr or '')[-400:]}")
    return out


def openrouter(prompt, timeout=300):
    """One OpenRouter completion on the reader's model. Returns (text, model that ran)."""
    body = {"model": READER[1], "max_tokens": 8000, "messages": [{"role": "user", "content": prompt}]}
    req = urllib.request.Request(pr.OPENROUTER_URL, data=json.dumps(body).encode(),
                                 headers={"Authorization": f"Bearer {pr.openrouter_key()}",
                                          "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        env = json.loads(r.read().decode())
    return ((env.get("choices") or [{}])[0].get("message") or {}).get("content") or "", env.get("model") or READER[1]


def cmd_tests(goal_dir, ask=codex):
    g, root, brief, plan, tests = load(goal_dir)
    files = sorted({t.split("::")[0] for t, _ in tests})
    listing = "\n".join(f"- {t} ({k})" for t, k in tests)
    prompt = f"""Draft the goal tests for this goal brief and plan. Output only these files, each introduced by a line
`=====FILE <path>=====` and followed by its full Python source, nothing else: {", ".join(files)}.

Write exactly these unittest methods, no others:
{listing}
An `outcome` test must fail against the repository as it is today and pass once the plan is built. An `invariant`
test must pass today and keep passing. Each method's docstring has a line `Scenario: ` followed by one of the brief's
Scenarios, copied verbatim. Do not add a drafted-by line; it is added for you.

{RULES}

The brief:
{brief}

The plan:
{plan}
"""
    out = ask(prompt, root)
    parts = FILE.split(out)
    got = dict(zip(parts[1::2], map(unfence, parts[2::2])))
    if set(got) != set(files):
        raise Refused(f"the drafter returned {sorted(got)}; the brief names {files}")
    for path, src in got.items():
        src = re.sub(r"^#\s*drafted-by:.*\n", "", src)
        (g / path).parent.mkdir(exist_ok=True)
        (g / path).write_text(f"# drafted-by: {DRAFTER[0]}/{DRAFTER[1]}\n" + src)
    print(f"examined {len(tests)} goal tests in {len(files)} files; wrote {', '.join(files)} "
          f"drafted by {DRAFTER[0]}/{DRAFTER[1]}")
    return 0


def cmd_holdout(goal_dir, ask=codex):
    g, root, brief, plan, tests = load(goal_dir)
    home = holdouts()
    if home == root.resolve() or root.resolve() in home.parents:
        raise Refused(f"{home} is inside the repository; the holdout never lives there")
    prompt = f"""Draft a hidden holdout test module for this goal brief and plan. Output only its Python source.

It catches a build that passes the goal tests without meeting the plan: follow PLAN.md exactly, including which
output stream each message goes to and every exit code it names. One class `Holdout` with 2 to 5 test methods.
You may read goals/{g.name}/tests/ for the approach, copying anything you reuse as literals. No drafted-by line.

{RULES}

The brief:
{brief}

The plan:
{plan}
"""
    hold = unfence(ask(prompt, root))
    try:
        compile(hold, "holdout", "exec")
    except SyntaxError as e:
        raise Refused(f"the holdout doesn't parse: {e.msg} at line {e.lineno}")
    if not re.search(r"^class Holdout\b", hold, re.M):
        raise Refused("the holdout has no class Holdout")
    home.mkdir(mode=0o700, parents=True, exist_ok=True)
    os.chmod(home, 0o700)
    path = home / f"{g.name}.py"
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w") as f:
        f.write(hold)
    os.chmod(path, 0o600)
    sha = hashlib.sha256(hold.encode()).hexdigest()
    (g / "holdout.sha256").write_text(sha + "\n")
    print(json.dumps({"holdout_file": str(path), "lines": len(hold.splitlines()), "sha256": sha,
                      "secret": goal_checks.secret_name(g.name), "environment": "goal-holdout",
                      "drafted_by": f"{DRAFTER[0]}/{DRAFTER[1]}"}, indent=2))
    return 0


def cmd_read(goal_dir, post=openrouter):
    g, root, brief, plan, tests = load(goal_dir)
    fams = gb.drafter(g)
    if not fams or None in fams or READER[0] in fams:
        raise Refused(f"the tests' drafting families are {sorted(map(str, fams))}; the reader must be another family")
    ids = [t for t, _ in tests]
    sources = "\n\n".join(f"=== {f.relative_to(g)} ===\n{f.read_text()}" for f in sorted((g / "tests").glob("*.py")))
    prompt = f"""Read these goal tests and say, in plain English for a non-programmer, exactly what each one checks and
whether it matches its Scenario line in the brief. Name any way a candidate could pass a test without meeting the
scenario. One paragraph per test, each starting with its full ID in backticks: {", ".join(f"`{t}`" for t in ids)}.
No headings, no preamble.

The brief:
{brief}

{sources}"""
    text, model = post(prompt)
    if not pr.model_ok(READER_TOOL, model):
        raise Refused(f"the reading came from {model!r}, below the floor ({pr.REVIEWERS[READER_TOOL]['floor_name']})")
    missed = [t for t in ids if f"`{t}`" not in text]
    if missed:
        raise Refused(f"the reading misses {missed}")
    print(f"## Plain-English reading\n\n{text.strip()}\n\nRead by: {READER[0]}/{model.split('/')[-1]}")
    return 0


def main(argv):
    if len(argv) != 2 or argv[0] not in ("tests", "holdout", "read"):
        print(__doc__, file=sys.stderr)
        return 2
    return {"tests": cmd_tests, "holdout": cmd_holdout, "read": cmd_read}[argv[0]](argv[1])


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
