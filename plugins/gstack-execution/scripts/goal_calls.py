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
LABELS = r"(?:[a-z0-9-]+\.)+[a-z][a-z0-9-]{1,62}"     # dotted name ending in a letter label, any suffix
# In code, a quoted string that is wholly a dotted name and the value of a host-like key are hostnames
# whatever the suffix; in a config file every dotted name is. ponytail: "README.md" counts too, which
# sends it to Dorian, the safe side.
QUOTED_HOST = re.compile(r"""["'`](%s)(?::\d+)?["'`]""" % LABELS, re.I)
CONFIG_HOST = re.compile(r"""[\w-]*(?:host|server|domain|endpoint|url|uri|addr|address|origin|proxy|registry|dsn)[\w-]*"""
                         r"""["']?\s*[:=]\s*["']?(%s)""" % LABELS, re.I)
ANY_HOST = re.compile(r"(?<![\w.-])(%s)(?![\w-])" % LABELS, re.I)
CONFIG_EXT = (".yml", ".yaml", ".json", ".toml", ".ini", ".cfg", ".conf", ".properties", ".xml", ".tf", ".tfvars",
              ".hcl", ".plist", ".env")
IP_HOST = re.compile(r"(?<![\d.])((?:\d{1,3}\.){3}\d{1,3})(?![\d.])")
# Forms that set or read the process environment, in any case: os.environ['X'], getenv('x'),
# process.env.X, ENV['X'], ${{ secrets.X }}, export X. Only these vouch for a name from the base.
ENV_NAME = re.compile(r"""(?:environ(?:\.get)?\s*[\[(]\s*["']|getenv\s*\(\s*["']|process\.env\.|process\.env\[\s*["']|"""
                      r"""ENV\[\s*["']|\$\{\{\s*(?:secrets|env|vars)\.|\bexport\s+)([A-Za-z_][A-Za-z0-9_]*)""")
# Forms that may be an environment variable or an ordinary one: ${X}, $X, NAME=value at line start.
# They count in added lines (the safe side); NAME= vouches from the base only in a .env file.
BRACE_NAME = re.compile(r"\$\{([A-Za-z_][A-Za-z0-9_]*)")
SHELL_NAME = re.compile(r"\$([A-Za-z_][A-Za-z0-9_]*)")
BARE_NAME = re.compile(r"^\s*([A-Z_][A-Z0-9_]*)=(?!=)", re.M)


def is_config(path):
    name = path.rsplit("/", 1)[-1]
    return name.startswith(".env") or name.endswith(CONFIG_EXT)


def hosts_in(text, path=""):
    """Every hostname or IP literal in text, lower-cased (hostnames aren't case-sensitive)."""
    found = (URL_HOST.findall(text) + BARE_HOST.findall(text) + QUOTED_HOST.findall(text)
             + CONFIG_HOST.findall(text) + IP_HOST.findall(text) + (ANY_HOST.findall(text) if is_config(path) else []))
    return {h.lower().rstrip(".") for h in found}


def names_in(text):
    """Every name in added text that may be an environment variable, case kept."""
    return (set(ENV_NAME.findall(text)) | set(BRACE_NAME.findall(text)) | set(SHELL_NAME.findall(text))
            | set(BARE_NAME.findall(text)))


def vouching_names(text, path):
    """Names the base text proves are environment variables: the env forms anywhere, NAME= in .env
    files. A Python, shell or Makefile assignment, or a $X read, proves nothing."""
    name = path.rsplit("/", 1)[-1]
    found = set(ENV_NAME.findall(text))
    if name.startswith(".env") or name.endswith(".env"):
        found |= set(BARE_NAME.findall(text))
    return found


def is_manifest(path):
    name = path.rsplit("/", 1)[-1]
    return name in MANIFESTS or re.fullmatch(r"requirements[\w.-]*\.(txt|in)", name) is not None


def base_has(repo, ref, needle, extract, ignore_case):
    """Does the base tree already use exactly this identifier? Each file that contains the text is
    re-parsed whole, so a reference split across lines still counts, api.example.com doesn't vouch
    for example.com, and OLD_API_KEY doesn't vouch for API_KEY."""
    flags = ["-i"] if ignore_case else []
    r = subprocess.run(["git", "-C", str(repo), "grep", "-l", "--null", "-I", "-F", *flags, needle, ref, "--"],
                       capture_output=True, text=True)
    for where in filter(None, r.stdout.split("\0")):   # <ref>:<path>
        path = where[len(ref) + 1:]
        if needle in extract(ge.at(repo, ref, path) or "", path):
            return True
    return False


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
    # Whole changed files, not added lines: a getenv( on one line and its name on the next is still
    # one reference. Unchanged references in those files are vouched for by the same file in the base.
    texts = {}
    for f in files:
        try:
            texts[f] = ge.at(repo, head, f) or ""
        except UnicodeDecodeError:                      # code can't read it, so code can't type it
            return "unclassified", [f"{f} is binary"]
    hosts = sorted({h for f, t in texts.items() for h in hosts_in(t, f)})
    names = sorted({n for t in texts.values() for n in names_in(t)})
    new = [f"new hostname {h}" for h in hosts if not base_has(repo, base, h, hosts_in, True)]
    new += [f"new environment variable {n}" for n in names if not base_has(repo, base, n, vouching_names, False)]
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


PROVIDERS = {"claude": "claude", "anthropic": "claude", "gpt": "gpt", "openai": "gpt",
             "gemini": "gemini", "google": "gemini", "deepseek": "deepseek"}
TRANSPORT_PREFIXES = {"openrouter"}
MODEL_FAMILY = re.compile(r"^(?:(claude)-|(gpt)-|(gemini)-|(deepseek)-)")


def family(model):
    """The canonical family of a model id in family/model, provider/model or bare-model form
    (anthropic/claude-opus-5 and claude/opus are both claude). Unknown or contradictory ids are refused."""
    parts = [x for x in str(model).lower().split("/") if x]
    if not parts:
        raise ValueError(f"no model id in {model!r}")
    named = set()
    for x in parts[:-1]:
        if x in TRANSPORT_PREFIXES:
            continue
        if x not in PROVIDERS:
            raise ValueError(f"unknown provider {x!r} in {model!r}")
        named.add(PROVIDERS[x])
    m = MODEL_FAMILY.match(parts[-1])
    if m:
        named.add(next(g for g in m.groups() if g))
    elif len(parts) == 1 and parts[0] in PROVIDERS:
        named.add(PROVIDERS[parts[0]])
    if len(named) != 1:
        raise ValueError(f"can't tell one family from {model!r}" + (f" ({sorted(named)})" if named else ""))
    return named.pop()


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
