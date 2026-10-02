#!/usr/bin/env python3
"""GO-005 criteria 1 to 3: a judgment call is a record, and code decides who makes it.

The action type comes from the change, never from the agent's label:
  goal_brief        anything under goals/
  dependency        a dependency manifest or lockfile changed
  external          a hostname or environment variable name the base tree doesn't already have
  unclassified      a file outside the brief's Allowed paths, or on a CODEOWNERS path
  in_envelope_code  none of the above
Only in_envelope_code goes to the council: two votes from families other than the builder's and
each other's, one of them told to argue against the leading option, on options framed by a family
other than the proposer's. A unanimous council decides; a split one escalates. Every other type
goes to Dorian, and the run waits for his answer. goal_run.py keeps the records in the run state.
"""
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import goal_brief as gb  # noqa: E402
import goal_envelope as ge  # noqa: E402

TYPES = ("in_envelope_code", "dependency", "external", "goal_brief", "unclassified")
MANIFESTS = {"package.json", "package-lock.json", "npm-shrinkwrap.json", "pnpm-lock.yaml", "yarn.lock", "bun.lockb",
             "pyproject.toml", "poetry.lock", "Pipfile", "Pipfile.lock", "setup.py", "setup.cfg", "uv.lock",
             "go.mod", "go.sum", "Cargo.toml", "Cargo.lock", "Gemfile", "Gemfile.lock", "composer.json",
             "composer.lock", "build.gradle", "pom.xml", "deno.json", "deno.lock"}
URL_HOST = re.compile(r"[a-z][a-z0-9+.-]*://(?:[^/@\s]*@)?([a-z0-9.-]+)", re.I)
TLDS = ("com|net|org|io|ai|dev|app|co|cloud|sh|so|xyz|me|tv|us|uk|de|eu|ca|au|gov|edu|mil|info|biz|tech|site|online|"
        "run|page|link|ly|gg|fm|to|internal|local|lan|corp|intranet|home|svc|cluster|localdomain|test|example")
BARE_HOST = re.compile(r"(?<![\w.-])((?:[a-z0-9-]+\.)+(?:%s))(?![\w-])" % TLDS, re.I)
IP_HOST = re.compile(r"(?<![\d.])((?:\d{1,3}\.){3}\d{1,3})(?![\d.])")
# Prefixed forms name a variable in any case: os.environ['X'], getenv('x'), process.env.X, ENV['X'],
# ${{ secrets.X }}, ${X}, export X.
ENV_NAME = re.compile(r"""(?:environ(?:\.get)?\s*[\[(]\s*["']|getenv\s*\(\s*["']|process\.env\.|process\.env\[\s*["']|"""
                      r"""ENV\[\s*["']|\$\{\{\s*(?:secrets|env|vars)\.|\$\{|\bexport\s+)([A-Za-z_][A-Za-z0-9_]*)""")
# The bare form is a .env or shell assignment: NAME=value at line start, no space before '='.
# ponytail: a Python line written KEY=x also matches; harmless on the added side (more waits on Dorian).
BARE_NAME = re.compile(r"^\s*([A-Z_][A-Z0-9_]*)=(?!=)", re.M)
SHELL_NAME = re.compile(r"\$([A-Za-z_][A-Za-z0-9_]*)")   # $NAME, no braces


def hosts_in(text):
    """Every hostname or IP literal in text, lower-cased (hostnames aren't case-sensitive)."""
    return {h.lower().rstrip(".") for h in URL_HOST.findall(text) + BARE_HOST.findall(text) + IP_HOST.findall(text)}


def names_in(text):
    """Every environment variable name in text, case kept (names are case-sensitive)."""
    return set(ENV_NAME.findall(text)) | set(BARE_NAME.findall(text)) | set(SHELL_NAME.findall(text))


def is_manifest(path):
    name = path.rsplit("/", 1)[-1]
    return name in MANIFESTS or re.fullmatch(r"requirements[\w.-]*\.(txt|in)", name) is not None


def added_lines(repo, base, head):
    out = ge.git(repo, "diff", "--unified=0", "--no-color", f"{base}...{head}")
    return [ln[1:] for ln in out.splitlines() if ln.startswith("+") and not ln.startswith("+++")]


def base_has(repo, ref, needle, extract, ignore_case):
    """Does the base tree already use exactly this identifier? Lines that contain the text are
    re-parsed, so api.example.com doesn't vouch for example.com and OLD_API_KEY doesn't vouch for
    API_KEY."""
    flags = ["-i"] if ignore_case else []
    r = subprocess.run(["git", "-C", str(repo), "grep", "-h", "-I", "-F", *flags, needle, ref, "--"],
                       capture_output=True, text=True)
    return any(needle in extract(ln) for ln in r.stdout.splitlines())


def action_type(repo, goal_id, head, base="origin/main"):
    """(type, reasons) for the goal-authored change on head, by code alone."""
    brief = ge.at(repo, base, f"goals/{goal_id}/GOAL.md") or ""
    codeowners = ge.at(repo, base, ".github/CODEOWNERS") or ""
    allowed = [g.strip("`") for g in gb.bullet_lines("Allowed paths", gb.sections(brief).get("Allowed paths", ""), [])]
    rs = ge.rules(codeowners)
    files = sorted({f for _, fs in ge.goal_commits(repo, base, head) for f in fs})
    if not files:
        return "unclassified", ["the change touches no files"]
    briefs = [f for f in files if f.startswith("goals/")]
    if briefs:
        return "goal_brief", [f"changes {f}" for f in briefs]
    deps = [f for f in files if is_manifest(f)]
    if deps:
        return "dependency", [f"changes {f}" for f in deps]
    lines = added_lines(repo, base, head)
    hosts = sorted({h for ln in lines for h in hosts_in(ln)})
    names = sorted({n for ln in lines for n in names_in(ln)})
    new = [f"new hostname {h}" for h in hosts if not base_has(repo, base, h, hosts_in, True)]
    new += [f"new environment variable {n}" for n in names if not base_has(repo, base, n, names_in, False)]
    if new:
        return "external", new
    outside = [f for f in files if ge.owners(rs, f) or not any(ge.path_in(g, f) for g in allowed)]
    if outside or not allowed:
        return "unclassified", [f"{f} is outside the envelope" for f in outside] or ["the brief lists no Allowed paths"]
    return "in_envelope_code", [f"{len(files)} files, all inside Allowed paths"]


def new_call(n, question, options, proposed_by, framed_by, kind, reasons, commits):
    if len(options) < 2 or len(set(options)) != len(options):
        raise ValueError("a judgment call needs at least two distinct options")
    if kind not in TYPES:
        raise ValueError(f"unknown action type {kind}")
    return {"n": n, "question": question, "options": list(options), "proposed_by": proposed_by,
            "framed_by": framed_by, "type": kind, "type_reasons": reasons, "commits": commits,
            "decider": "council" if kind == "in_envelope_code" else "dorian", "votes": [],
            "status": "open", "choice": None, "dissent": [], "words": None}


def family(model):
    return str(model).split("/", 1)[0].lower()


def council(call, votes, builder):
    """votes: [{'model': fam/model, 'role': 'for'|'against', 'choice': option, 'reason': text}].
    Decides a unanimous in_envelope_code call; escalates a split one to Dorian."""
    if call["status"] != "open" or call["decider"] != "council":
        raise ValueError(f"call {call['n']} isn't open to the council (decider {call['decider']}, {call['status']})")
    fams = [family(v["model"]) for v in votes]
    problems = []
    if len(votes) != 2:
        problems.append(f"the council is two votes, got {len(votes)}")
    if family(builder) in fams:
        problems.append(f"the builder's family {family(builder)} can't vote")
    if len(set(fams)) != len(fams):
        problems.append("the two votes come from one family")
    if sorted(v.get("role") for v in votes) != ["against", "for"]:
        problems.append("one vote argues for the leading option and one against it")
    if family(call["framed_by"]) == family(call["proposed_by"]):
        problems.append("the options were framed by the proposer's own family")
    if any(v.get("choice") not in call["options"] for v in votes):
        problems.append("a vote chose something that isn't one of the options")
    if problems:
        raise ValueError("; ".join(problems))
    call["votes"] = votes
    choices = {v["choice"] for v in votes}
    if len(choices) == 1:
        call.update(status="decided", choice=choices.pop(), dissent=[])
    else:
        call.update(status="escalated", decider="dorian",
                    dissent=[f"{v['model']} ({v['role']}): {v['choice']} - {v.get('reason', '')}" for v in votes])
    return call


def answer(call, choice, words):
    """Dorian's answer, in his words, to a call that's his."""
    if call["decider"] != "dorian" or call["status"] not in ("open", "escalated"):
        raise ValueError(f"call {call['n']} isn't waiting for Dorian")
    if choice not in call["options"]:
        raise ValueError(f"{choice!r} isn't one of the options {call['options']}")
    if not str(words or "").strip():
        raise ValueError("record Dorian's answer in his own words")
    call.update(status="decided", choice=choice, words=words)
    return call


def waiting(calls):
    return [c for c in calls if c["decider"] == "dorian" and c["status"] in ("open", "escalated")]
