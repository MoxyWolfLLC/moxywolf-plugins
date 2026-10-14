#!/usr/bin/env python3
"""MR-003: every call is classified against an ontology, and only the calls that carry a model
choice ask Jev.

Three hooks and two commands, stdlib only:

  route.py session-start   (hook JSON on stdin)  opens the session ledger
  route.py pre-tool-use    (hook JSON on stdin)  classifies the call; may return updatedInput
  route.py session-end     (hook JSON on stdin)  appends the session summary line
  route.py score --dir D                         counts a ledger directory
  route.py aar --dir D --date YYYY-MM-DD         one day's after-action report (CS-007)
  route.py cos-run start <id> | end              the live /cos run id, recorded by the hook in the session ledger (CS-007)
  route.py --selftest

The hard limit: a hook cannot change the model answering the current turn. Only a subagent launch
(the Agent tool's `model`) is rewritten. Script classes that choose their own model are recorded,
not rewritten. A hook never blocks a call and never raises: a failure is a ledger line and the
call proceeds unchanged.
"""
import json
import os
import re
import sys
import time
import urllib.request
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
ONTOLOGY = HERE.parent / "references" / "call-ontology.json"
TIERS = ("floor", "standard", "light")
FIELDS = ("class", "tool", "match", "carries_model", "default_tier", "ask")
MODEL_ID = os.environ.get("GSTACK_COVERAGE_MODEL", "typesafe-ai/jev")
GATEWAY = "https://ai-gateway.vercel.sh/v4/ai"
JEV_TIMEOUT = 8
FLOOR_LOCKED = {"review-subagent"}   # MR-003.7: never moved below floor, whatever Jev says
FLOOR_RULES = {"risky", "trust_boundary", "cross_file"}
FLOOR_LOCKED_DEPARTMENTS = {"security"}   # CS-007: the security department never drops below floor either
DEPARTMENTS = ("finance", "people", "it-operations", "security", "pmo", "operations", "corporate-strategy",
               "customer-experience", "sales-department", "marketing-department")
CLAIM_CHECKS = "claim-checks.jsonl"
# CS-007: the run id is session state. The hook watches the `route.py cos-run start <id>` and `cos-run end`
# commands go by (it sees every Bash call) and records them in the session's own ledger, so two sessions in
# one project never share a run (F12, review 20261014-082908). COS_RUN_ID in the environment is an explicit
# override for runners that set it.
# the path is letters, digits and _ . / ~ $ { } : @ + = - only (so `${CLAUDE_PLUGIN_ROOT}/...` fits), quoted or not;
# a comment mark, an operator, a backtick or $( can't appear anywhere in the command
_PATH = r"[A-Za-z0-9_./~${}:@+=-]*route\.py"
# horizontal whitespace only between tokens: a newline inside the invocation is two shell commands, not one
COS_RUN_FULL = re.compile(r"""^\s*(?:python3?(?:\.\d+)?[ \t]+)?(?:"%s"|'%s'|%s)[ \t]+cos-run[ \t]+(?:start[ \t]+([A-Za-z0-9._-]+)|(end))[ \t]*\n?\s*$""" % (_PATH, _PATH, _PATH))
TOO_FEW = 10                          # CS-007.6: a rate under this many observations is a lead, not a finding
PROMPT_HEAD = 4000

# MR-002's bars, copied under the same names; nothing is imported from gstack-execution.
RISKY_BAR = 0.70
UPGRADE_BAR = 0.30
DOWNGRADE_BAR = 0.60
HAS_TESTS_BAR = 0.50
THRESHOLDS = {"risky": RISKY_BAR, "upgrade": UPGRADE_BAR, "downgrade": DOWNGRADE_BAR, "has_tests": HAS_TESTS_BAR}
BARS = {"risky": RISKY_BAR, "trust_boundary": UPGRADE_BAR, "cross_file": UPGRADE_BAR, "docs_only": DOWNGRADE_BAR, "has_tests": HAS_TESTS_BAR}

QUESTIONS = {
    "trust_boundary": {"type": "boolean",
        "instructions": "Does this task change code on a trust boundary: authentication, authorization, payment, credentials or secrets, the agent's GitHub token or app, a repository ruleset, a CI workflow, or anything that decides what an agent may do?",
        "criteria": {"true": "The task's description or prompt changes such code.", "false": "Nothing in the task touches such code."}},
    "cross_file": {"type": "boolean",
        "instructions": "Does this task need reasoning across more than one source file at once: a change in one file that only makes sense together with a change in another, a protocol between a writer and a reader, or a contract several files must agree on?",
        "criteria": {"true": "The task requires coordinated changes in two or more files, or a shape two or more files must agree on.", "false": "The task can be done inside one file, or it is not code."}},
    "docs_only": {"type": "boolean",
        "instructions": "Is this task documentation, reading, summarizing, configuration, a status line, or a version move only, with no change to executable code or tests?",
        "criteria": {"true": "The task is satisfied by reading or by editing prose, configuration or version strings.", "false": "The task changes executable code or a test."}},
    "has_tests": {"type": "boolean",
        "instructions": "Does the task name executable tests it must add or make pass (a test file, a suite, a CI job that reports counts)?",
        "criteria": {"true": "The task names a test file, suite or CI check by name.", "false": "No executable test is named."}},
    "risky": {"type": "boolean",
        "instructions": "Does this task change code that touches production data, money, credentials or secrets, or an irreversible action: a migration, a deletion of tracked files, a send, a payment, a merge to a protected branch?",
        "criteria": {"true": "The task changes such code or performs such an action.", "false": "Nothing in the task touches production data, money, credentials, secrets or an irreversible action."}},
}
RULES = [("risky", "floor", lambda a: a["risky"]),
         ("trust_boundary", "floor", lambda a: a["trust_boundary"]),
         ("cross_file", "floor", lambda a: a["cross_file"]),
         ("docs_only", "light", lambda a: a["docs_only"] and not a["has_tests"]),
         ("default", "standard", lambda a: True)]


def now():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


# ---- ontology ----

def load_table(path=ONTOLOGY):
    """The table, or a reason it is refused. Every entry has all six fields; tiers are the three or none."""
    try:
        t = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError) as e:
        return None, f"ontology {path} could not be read: {e}"
    if not isinstance(t, dict) or not isinstance(t.get("classes"), list) or not t.get("version"):
        return None, f"ontology {path} needs a version and a classes list"
    tiers = t.get("tiers") or {}
    if set(tiers) != set(TIERS):
        return None, f"ontology {path} must map exactly {list(TIERS)} to model names"
    if not all(isinstance(v, str) and v for v in tiers.values()):
        return None, f"ontology {path} tiers must map to model names"
    for i, c in enumerate(t["classes"]):
        if not isinstance(c, dict):
            return None, f"ontology {path} entry {i} is not an object"
        missing = [f for f in FIELDS if f not in c]
        if missing:
            return None, f"ontology {path} entry {i} lacks {missing}"
        if not (isinstance(c["class"], str) and c["class"] and isinstance(c["tool"], str) and c["tool"]):
            return None, f"ontology {path} entry {i} needs string class and tool"
        if not isinstance(c["carries_model"], bool) or not isinstance(c["ask"], bool):
            return None, f"ontology {path} entry {c['class']} needs boolean carries_model and ask"
        if c["default_tier"] not in TIERS + ("none",):
            return None, f"ontology {path} entry {c['class']} has default_tier {c['default_tier']!r}; use floor, standard, light or none"
        if c["match"] is not None:
            if not isinstance(c["match"], dict):
                return None, f"ontology {path} entry {c['class']} has a non-object match"
            for k, rx in c["match"].items():
                try:
                    re.compile(rx if isinstance(rx, str) else None)
                except (re.error, TypeError) as e:
                    return None, f"ontology {path} entry {c['class']} match {k!r} is not a regex: {e}"
    return t, None


def load_table_safely(path=ONTOLOGY):
    """F1 (review 20261014-014833): any failure while reading the table is a refusal, never a hook error."""
    try:
        return load_table(path)
    except Exception as e:
        return None, f"ontology {path} refused: {type(e).__name__}: {e}"


def classify(table, tool, tool_input):
    """First entry whose tool matches and whose match (regex per input field) matches; else unclassified."""
    for c in table["classes"]:
        if c["tool"] != tool:
            continue
        m = c["match"] or {}
        if all(re.search(rx, str(tool_input.get(k, ""))) for k, rx in m.items()):
            return c
    return {"class": "unclassified", "tool": tool, "match": None, "carries_model": tool == "Agent", "default_tier": "none", "ask": tool == "Agent"}


# ---- ledger ----

def ledger_dir():
    root = os.environ.get("GSTACK_PEER_REVIEW_DIR")
    if root:
        return Path(root) / "model-routing", "env GSTACK_PEER_REVIEW_DIR"
    return Path.home() / ".gstack" / "model-routing", "fallback ~/.gstack/model-routing"


def ledger_path(session_id):
    d, _ = ledger_dir()
    return d / f"{datetime.now(timezone.utc).strftime('%Y%m%d')}-{session_id}.jsonl"


def session_file(session_id):
    """Today's file for this session, or the newest earlier one (a session that crossed midnight)."""
    d, _ = ledger_dir()
    p = ledger_path(session_id)
    if p.exists():
        return p
    older = sorted(d.glob(f"*-{session_id}.jsonl")) if d.exists() else []
    return older[-1] if older else p


def routing_off(path):
    """F2 (review 20261014-014833): a session whose table was refused stays off, whatever the table does later."""
    # round 2: any refusal in the session's ledger holds, whatever a later SessionStart (compact, resume) finds
    return any(l.get("event") == "session_start" and l.get("routing") == "off" for l in read_lines(path))


def append(path, line):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(line, sort_keys=True) + "\n")


def read_lines(path):
    out = []
    try:
        for raw in Path(path).read_text(encoding="utf-8").splitlines():
            if raw.strip():
                try:
                    out.append(json.loads(raw))
                except ValueError:
                    out.append({"event": "unreadable"})
    except OSError:
        pass
    return out


# ---- Jev ----

def credential():
    key = os.environ.get("AI_GATEWAY_API_KEY")
    if key:
        return key, "env AI_GATEWAY_API_KEY"
    f = os.environ.get("GSTACK_AIGATEWAY_ENV")
    if f:
        try:
            for raw in Path(f).read_text(encoding="utf-8").splitlines():
                raw = raw.strip()
                if raw.startswith("AI_GATEWAY_API_KEY="):
                    return raw.split("=", 1)[1].strip().strip('"').strip("'"), "GSTACK_AIGATEWAY_ENV"
        except OSError:
            return None, f"GSTACK_AIGATEWAY_ENV names {f}, which could not be read"
        return None, f"{f} sets no AI_GATEWAY_API_KEY"
    return None, "no AI_GATEWAY_API_KEY on any path"


def ask_jev(state):
    """{answers} or {error}. Same wire shape the ai SDK's evaluation model uses (XE-014, MR-001)."""
    key, source = credential()
    if not key:
        return {"error": source}
    base = os.environ.get("JEV_ENDPOINT") or GATEWAY
    body = json.dumps({"state": state, "questions": QUESTIONS}).encode()
    req = urllib.request.Request(f"{base.rstrip('/')}/evaluation-model", data=body, method="POST", headers={
        "Content-Type": "application/json", "Authorization": f"Bearer {key}", "ai-gateway-auth-method": "api-key",
        "ai-evaluation-model-specification-version": "4", "ai-model-id": MODEL_ID})
    try:
        with urllib.request.urlopen(req, timeout=JEV_TIMEOUT) as r:
            d = json.loads(r.read().decode())
    except Exception as e:  # network, HTTP status, bad JSON: Jev is unavailable, the call still runs
        return {"error": f"{type(e).__name__}: {e}"[:200]}
    ans = d.get("answers") if isinstance(d, dict) else None
    if not isinstance(ans, dict):
        return {"error": "response carries no answers"}
    return {"answers": {k: float(v.get("probability", 0) or 0) for k, v in ans.items() if isinstance(v, dict)},
            "input_tokens": (d.get("usage") or {}).get("inputTokens", 0)}


def decide(answers):
    a = {k: answers.get(k, 0.0) >= BARS[k] for k in QUESTIONS}
    rule, tier, _ = next(r for r in RULES if r[2](a))
    return {"tier": tier, "rule": rule, "booleans": a, "thresholds": THRESHOLDS}


def cos_run_command(command):
    """('start', id), ('end', None) or None. The whole Bash command must be the invocation and nothing else:
    an optional python3, the script path (quoted or not, no spaces), then `cos-run start <id>` or `cos-run end`.
    No chaining, no prefix, no suffix. Three rounds of review 20261014-085739 showed that recognizing the
    invocation inside a larger command means reimplementing shell quoting; /cos runs it as its own command,
    so the hook accepts only that shape and a mention anywhere else is text."""
    m = COS_RUN_FULL.match(str(command))
    if not m:
        return None
    return ("start", m.group(1)) if m.group(1) else ("end", None)


def cos_run_id(path):
    """The live run id for this session: COS_RUN_ID if set, else the last cos-run start in the session
    ledger that no cos-run end has closed. Never invented."""
    if os.environ.get("COS_RUN_ID"):
        return os.environ["COS_RUN_ID"]
    run = None
    for l in read_lines(path):
        if l.get("event") == "cos_run_start":
            run = l.get("cos_run") or None
        elif l.get("event") == "cos_run_end":
            run = None
    return run


def cmd_cos_run(argv):
    """route.py cos-run start <id> | end. The command is the signal: the PreToolUse hook records it in the
    session ledger as it runs. Outside a hooked session it only prints."""
    if argv[:1] == ["start"] and len(argv) > 1 and argv[1].strip():
        print(f"cos-run {argv[1].strip()} started (recorded by the model-router hook in this session's ledger)"); return 0
    if argv[:1] == ["end"]:
        print("cos-run ended"); return 0
    print("usage: route.py cos-run start <id> | end", file=sys.stderr); return 2


# ---- hooks ----

def hook_input():
    try:
        return json.loads(sys.stdin.read() or "{}")
    except ValueError:
        return {}


def cmd_session_start(h):
    table, why = load_table_safely()
    sid = h.get("session_id") or "unknown"
    d, source = ledger_dir()
    path = session_file(sid)                 # the session's existing ledger, across a date rollover
    if table is not None and routing_off(path):
        table, why = None, "refused earlier in this session"
    if table is None:
        print(f"model-router: routing is off for this session: {why}", file=sys.stderr)
        append(path, {"ts": now(), "event": "session_start", "routing": "off", "why": why, "ledger_source": source, "source": h.get("source")})
        return 0
    append(path, {"ts": now(), "event": "session_start", "routing": "on", "ontology_version": table["version"],
                  "ledger_source": source, "source": h.get("source")})
    return 0


def cmd_pre_tool_use(h):
    sid = h.get("session_id") or "unknown"
    tool = h.get("tool_name") or ""
    tin = h.get("tool_input") if isinstance(h.get("tool_input"), dict) else {}
    path = session_file(sid)
    if os.environ.get("MODEL_ROUTER_FORCE_ERROR"):   # MR-003.8's forced internal failure, for the test only
        raise RuntimeError("forced by MODEL_ROUTER_FORCE_ERROR")
    if routing_off(path):
        append(path, {"ts": now(), "event": "refused", "tool": tool, "why": "routing is off for this session"})
        return 0
    table, why = load_table_safely()
    if table is None:
        if not path.exists():
            append(path, {"ts": now(), "event": "session_start", "routing": "off", "why": why, "ledger_source": ledger_dir()[1], "source": "lazy"})
        append(path, {"ts": now(), "event": "refused", "tool": tool, "why": why})
        return 0
    if not path.exists():   # a cloud session whose SessionStart fired before the plugin's hooks registered
        append(path, {"ts": now(), "event": "session_start", "routing": "on", "ontology_version": table["version"],
                      "ledger_source": ledger_dir()[1], "source": "lazy"})
    if tool == "Bash":                          # CS-007: the run id's start and end are commands the hook watches go by
        m = cos_run_command(tin.get("command", ""))
        if m:
            append(path, {"ts": now(), "event": "cos_run_start", "cos_run": m[1]} if m[0] == "start" else {"ts": now(), "event": "cos_run_end"})
    c = classify(table, tool, tin)
    line = {"ts": now(), "class": c["class"], "tool": tool, "routed": False, "tool_use_id": h.get("tool_use_id")}
    run = cos_run_id(path)                      # this session's live run, or COS_RUN_ID; never invented
    if run:
        line["cos_run"] = run
    if tool == "Agent":
        line["subagent_type"] = tin.get("subagent_type")
        if c["class"] == "department-subagent":
            line["department"] = str(tin.get("subagent_type", "")).split(":", 1)[0]
    if not c["carries_model"]:
        append(path, line); return 0
    tier = c["default_tier"] if c["default_tier"] != "none" else None
    decided_by = "table"
    if c["ask"]:
        state = {"class": c["class"], "tool": tool, "subagent_type": tin.get("subagent_type"),
                 "description": tin.get("description"), "prompt": str(tin.get("prompt", ""))[:PROMPT_HEAD]}
        r = ask_jev(state)
        if "answers" in r:
            d = decide(r["answers"])
            line.update(answers=r["answers"], rule=d["rule"], thresholds=d["thresholds"], jev_tokens=r.get("input_tokens", 0))
            tier, decided_by = d["tier"], "jev"
        else:
            line["jev"] = "unavailable"; line["jev_error"] = r["error"]
    floor_rule = (decided_by == "jev" and line.get("rule") in FLOOR_RULES) or (decided_by == "table" and tier == "floor")
    if (c["class"] in FLOOR_LOCKED or line.get("department") in FLOOR_LOCKED_DEPARTMENTS) and tier != "floor":
        line["floor_locked_from"] = tier; tier = "floor"; floor_rule = True
    if tier is None:                      # unclassified Agent with Jev unavailable: unchanged
        append(path, line); return 0
    line.update(tier=tier, decided_by=decided_by, model=table["tiers"][tier])
    if tool != "Agent":                   # a script chooses its own model; the tier is recorded, not applied
        line["note"] = "script selects its own model"
        append(path, line); return 0
    if tin.get("model"):                  # MR-001.7: a caller's explicit choice stands and is recorded
        # F2/F5 (review 20261014-082908): the model the launch actually used, and whether a floor rule put it there,
        # are written here, not inferred by a reader later
        line.update(caller_model=tin["model"], decided_by=f"caller ({decided_by} advised {table['tiers'][tier]})",
                    applied_model=tin["model"], floor_rule=False)
        append(path, line); return 0
    line.update(routed=True, applied_model=table["tiers"][tier], floor_rule=floor_rule)
    append(path, line)
    print(json.dumps({"hookSpecificOutput": {"hookEventName": "PreToolUse", "updatedInput": {**tin, "model": table["tiers"][tier]}}}))
    return 0


def summarize(lines):
    calls = [l for l in lines if "class" in l]
    by_class = Counter(l["class"] for l in calls)
    tiers = Counter(l.get("tier") for l in calls if l.get("tier"))
    return {"calls": len(calls), "by_class": dict(sorted(by_class.items())), "routed": sum(1 for l in calls if l.get("routed")),
            "jev_consults": sum(1 for l in calls if "answers" in l or l.get("jev") == "unavailable"),
            "jev_unavailable": sum(1 for l in calls if l.get("jev") == "unavailable"),
            "tiers": dict(sorted(tiers.items())), "unclassified": by_class.get("unclassified", 0),
            "refused": sum(1 for l in lines if l.get("event") == "refused")}


def cmd_session_end(h):
    sid = h.get("session_id") or "unknown"
    path = session_file(sid)
    lines = read_lines(path)
    table, _ = load_table_safely()
    s = summarize(lines)
    s.update(ts=now(), event="session_end", ontology_version=table["version"] if table else None, reason=h.get("reason"))
    append(path, s)
    print(f"model-router: {s['calls']} calls, {s['routed']} routed, {s['jev_consults']} Jev consults, "
          f"{s['unclassified']} unclassified, tiers {s['tiers'] or 0}; ledger {path}")
    return 0


# ---- score ----

def score_dir(d):
    files = sorted(Path(d).glob("*.jsonl")) if Path(d).exists() else []
    lines = [l for f in files for l in read_lines(f)]
    calls = [l for l in lines if "class" in l]
    def bump(p, l):
        p["calls"] += 1; p["routed"] += bool(l.get("routed")); p["jev"] += ("answers" in l or l.get("jev") == "unavailable")
        p["jev_unavailable"] += l.get("jev") == "unavailable"; p["unclassified"] += l["class"] == "unclassified"
    fresh = lambda: {"calls": 0, "routed": 0, "jev": 0, "jev_unavailable": 0, "unclassified": 0}
    per_class = {}
    per_tier = {t: fresh() for t in TIERS}   # F3: the same four counts in both breakdowns
    for l in calls:
        bump(per_class.setdefault(l["class"], fresh()), l)
        if l.get("tier") in per_tier:
            bump(per_tier[l["tier"]], l)
    return {"files": len(files), "lines": len(lines), "calls": len(calls), "per_class": dict(sorted(per_class.items())),
            "per_tier": per_tier, "unclassified": per_class.get("unclassified", {}).get("calls", 0),
            "sessions": len({f.name for f in files if any(l.get("event") == "session_start" for l in read_lines(f))})}   # F1 follow-up: distinct sessions, not SessionStart events


def print_score(s, d):
    print(f"ledger {d}: {s['files']} files, {s['lines']} lines, {s['sessions']} sessions, {s['calls']} calls, {s['unclassified']} unclassified")
    row = lambda p: f"{p['calls']} calls, {p['routed']} routed, {p['jev']} Jev consults ({p['jev_unavailable']} unavailable), {p['unclassified']} unclassified"
    for c, p in s["per_class"].items():
        print(f"  {c:<22} {row(p)}")
    for t in TIERS:
        print(f"  tier {t:<9} {row(s['per_tier'][t])}")


# ---- CS-007: the after-action report ----

def rate(n, d, per=None):
    """'n/d (p)' with the too-few mark; a rate is never printed without its denominator. With `per`,
    a count over a denominator that is not a share ('4 over 1 reviews')."""
    if not d:
        return f"{n}/0 (no observations)"
    s = f"{n} over {d} {per}" if per else f"{n}/{d} ({n / d:.0%})"
    return s + (f", too few to read (n={d} < {TOO_FEW}), a lead" if d < TOO_FEW else "")


def aar(d, date):
    """Read one day's routing records (by timestamp, across session files that may span days), claim-check
    lines and model-selection lines. Counts over usage, never causes. Every model attribution comes from a
    tag written at the time (applied_model, declared_tier); nothing is inferred after the fact."""
    d = Path(d)
    session_files = sorted(f for f in d.glob("*.jsonl") if f.name != CLAIM_CHECKS) if d.exists() else []
    lines = [l for f in session_files for l in read_lines(f) if str(l.get("ts", "")).startswith(date)]   # F3: by ts, not file name
    calls = [l for l in lines if "class" in l]
    checks_file = d / CLAIM_CHECKS
    checks = [l for l in read_lines(checks_file) if str(l.get("ts", "")).startswith(date)] if checks_file.exists() else []
    # the MR-001 ledger beside this directory: one line per released item, written by model_selection_line() in
    # plugins/gstack-execution/scripts/peer_review.py at record-release, with recorded_at, recommendation {tier, rule,
    # mode}, declared_tier (the tier the build said it ran on, from the packet), override and outcome
    # {blocking_findings, rounds_used, unknowns_raised, release_outcome}. This reader attributes a line by its
    # declared_tier only; a line without one is counted as untagged.
    sel_dir = d.parent / "model-selection"
    sel_files = sorted(sel_dir.glob("*.jsonl")) if sel_dir.exists() else []
    sel = [l for f in sel_files for l in read_lines(f) if str(l.get("recorded_at", "")).startswith(date)]
    read = {"files": len(session_files) + (1 if checks_file.exists() else 0) + len(sel_files), "lines": len(lines) + len(checks) + len(sel)}
    table = load_table_safely()[0]
    tiers = (table or {}).get("tiers", {"floor": "opus", "standard": "sonnet", "light": "haiku"})
    tier_of = {m: t for t, m in tiers.items()}

    launches = [l for l in calls if l.get("tool") == "Agent" and l.get("applied_model")]   # F2: what actually ran, written at launch
    dispatches = [l for l in launches if l.get("department")]
    out = [f"# After-action report for {date}", "",
           f"Read {read['files']} files and {read['lines']} lines dated {date}: {len(calls)} calls across {len(session_files)} session ledgers, "
           f"{len(dispatches)} department dispatches, {len(checks)} claim checks, {len(sel)} model-selection lines."]
    if read["lines"] == 0:
        out.append("Zero lines read. That is not a clean day; it is a day with no record.")
    out += ["", "Note: harder tasks go to stronger models by design. MR-001 and MR-002 send trust-boundary, cross-file and risky "
            "work to the floor, so a stronger model's higher failure rate is expected before it is evidence. Every rate below is "
            "printed over its usage count; counts under 10 are leads, not findings; nothing here names a cause.", ""]

    out += ["## By class", "", "| class | calls | routed | Jev consults | unclassified |", "|---|---|---|---|---|"]
    per_class = {}
    for l in calls:
        p = per_class.setdefault(l["class"], {"calls": 0, "routed": 0, "jev": 0, "unclassified": 0})
        p["calls"] += 1; p["routed"] += bool(l.get("routed")); p["jev"] += ("answers" in l or l.get("jev") == "unavailable")
        p["unclassified"] += l["class"] == "unclassified"
    for c, p in sorted(per_class.items()):
        out.append(f"| {c} | {p['calls']} | {p['routed']} | {p['jev']} | {p['unclassified']} |")
    if not per_class:
        out.append("| (none) | 0 | 0 | 0 | 0 |")

    # by model: usage is launches that actually ran on it; mistakes are checks and findings tagged with it at write time
    out += ["", "## By model", "", "| model | launches | department dispatches | sent there by a floor rule | claim-check failures / dispatches | checks passed / checks | blocking findings / reviews |", "|---|---|---|---|---|---|---|"]
    untagged_checks = sum(1 for c in checks if not c.get("model") or not c.get("department"))
    untagged_sel = sum(1 for l in sel if l.get("declared_tier") not in tiers)                 # F4: no fallback to the recommendation
    for tier in TIERS:
        model = tiers[tier]
        ml = [l for l in launches if l["applied_model"] == model]
        md = [l for l in dispatches if l["applied_model"] == model]
        floor_rule = sum(1 for l in ml if l.get("floor_rule"))                                   # F5: the tag written at launch
        mchecks = [c for c in checks if c.get("model") == model]
        fails = sum(1 for c in mchecks if not c.get("passed"))
        msel = [l for l in sel if l.get("declared_tier") == tier]
        blocking = sum(int((l.get("outcome") or {}).get("blocking_findings", 0) or 0) for l in msel)
        out.append(f"| {model} ({tier}) | {len(ml)} | {len(md)} | {rate(floor_rule, len(ml))} | {rate(fails, len(md), 'dispatches')} | "
                   f"{rate(len(mchecks) - fails, len(mchecks))} | {rate(blocking, len(msel), 'reviews')} |")
    out.append(f"\nUntagged, counted apart: {untagged_checks} claim-check lines without a model or department; "
               f"{untagged_sel} model-selection lines without a declared tier.")

    # by department: dispatches are the usage; send-backs are failed checks over dispatches
    out += ["", "## By department", "", "| department | dispatches | models used | checks passed / checks | send-backs / dispatches | escalations / runs |", "|---|---|---|---|---|---|"]
    runs, dep_rows = {}, {}
    for l in dispatches:
        r = runs.setdefault(l.get("cos_run") or "(no cos_run)", {"departments": set(), "models": set(), "failed": {}})
        r["departments"].add(l["department"]); r["models"].add(l["applied_model"])
        dp = dep_rows.setdefault(l["department"], {"dispatches": 0, "models": set(), "checks": 0, "passed": 0, "send_backs": 0, "escalations": 0})
        dp["dispatches"] += 1; dp["models"].add(l["applied_model"])
    for c in checks:
        dep = c.get("department") or "(untagged)"
        r = runs.setdefault(c.get("cos_run") or "(no cos_run)", {"departments": set(), "models": set(), "failed": {}})
        r["departments"].add(dep)
        dp = dep_rows.setdefault(dep, {"dispatches": 0, "models": set(), "checks": 0, "passed": 0, "send_backs": 0, "escalations": 0})
        dp["checks"] += 1; dp["passed"] += bool(c.get("passed"))
        if not c.get("passed"):
            dp["send_backs"] += 1
            r["failed"][dep] = r["failed"].get(dep, 0) + 1
    for r in runs.values():                         # an escalation is a second failed check for one department in one run
        for dep, n in r["failed"].items():
            if n >= 2:
                dep_rows[dep]["escalations"] += 1
    for dep, p in sorted(dep_rows.items()):
        dep_runs = sum(1 for rr in runs.values() if dep in rr["departments"])
        out.append(f"| {dep} | {p['dispatches']} | {', '.join(sorted(p['models'])) or '(none)'} | {rate(p['passed'], p['checks'])} | "
                   f"{rate(p['send_backs'], p['dispatches'], 'dispatches')} | {rate(p['escalations'], dep_runs, 'runs')} |")
    if not dep_rows:
        out.append("| (none) | 0 | (none) | 0/0 (no observations) | 0/0 (no observations) | 0/0 (no observations) |")

    out += ["", "## Runs", ""]
    for rid, r in sorted(runs.items()):
        esc = [dp for dp, n in r["failed"].items() if n >= 2]
        outcome = "escalated (" + ", ".join(sorted(esc)) + ")" if esc else ("sent back once" if r["failed"] else "done")
        out.append(f"- {rid}: {', '.join(sorted(r['departments']))}; models {', '.join(sorted(r['models'])) or '(none)'}; {outcome}")
    if not runs:
        out.append("- (no runs)")

    # one decision: the worst rate over at least TOO_FEW observations of its own usage
    out += ["", "## Decision", ""]
    candidates = []
    for dep, p in dep_rows.items():
        if p["dispatches"] >= TOO_FEW and p["send_backs"]:
            candidates.append((p["send_backs"] / p["dispatches"], 2, f"the {dep} department's return contract or claim-check form: {p['send_backs']} send-backs over {p['dispatches']} dispatches"))
    for tier in TIERS:
        model = tiers[tier]
        md = [l for l in dispatches if l["applied_model"] == model]
        fails = sum(1 for c in checks if c.get("model") == model and not c.get("passed"))
        if len(md) >= TOO_FEW and fails:
            candidates.append((fails / len(md), 1, f"the routing default that sends department dispatches to {model}: {fails} claim-check failures over {len(md)} dispatches"))
    n = per_class.get("unclassified", {}).get("calls", 0)
    if len(calls) >= TOO_FEW and n:            # the bar is over the calls observed, the mistakes are the unclassified ones
        candidates.append((n / max(len(calls), 1), 0, f"the ontology: {n} of {len(calls)} calls were unclassified; add the missing class"))
    if candidates:   # the worst rate wins; on a tie the narrower gate (a department before a model before the ontology)
        candidates.sort(reverse=True)
        out.append(f"Decision: change {candidates[0][2]}.")
    else:
        out.append("Decision: none this day; the counts are below the bar.")
    return "\n".join(out) + "\n"


# ---- entry ----

def main(argv):
    if not argv or argv[0] in ("-h", "--help"):
        print(__doc__); return 0
    cmd = argv[0]
    if cmd == "--selftest":
        return selftest()
    if cmd == "cos-run":
        return cmd_cos_run(argv[1:])
    if cmd == "aar":
        d = argv[argv.index("--dir") + 1] if "--dir" in argv else str(ledger_dir()[0])
        date = argv[argv.index("--date") + 1] if "--date" in argv else datetime.now(timezone.utc).strftime("%Y-%m-%d")
        print(aar(d, date), end=""); return 0
    if cmd == "score":
        d = argv[argv.index("--dir") + 1] if "--dir" in argv else str(ledger_dir()[0])
        print_score(score_dir(d), d); return 0
    h = hook_input()
    try:
        if cmd == "session-start":
            return cmd_session_start(h)
        if cmd == "pre-tool-use":
            return cmd_pre_tool_use(h)
        if cmd == "session-end":
            return cmd_session_end(h)
    except Exception as e:  # MR-003.8: a hook never raises; the failure is a line and the call proceeds
        try:
            append(session_file(h.get("session_id") or "unknown"), {"ts": now(), "event": "hook_error", "cmd": cmd,
                                                                      "error": f"{type(e).__name__}: {e}"[:300], "tool": h.get("tool_name")})
        except Exception:
            pass
        return 0
    print(f"model-router: unknown command {cmd}", file=sys.stderr)
    return 0


def selftest():
    table, why = load_table()
    assert table and not why, why
    assert classify(table, "Read", {})["class"] == "read-file"
    assert classify(table, "Bash", {"command": "git status"})["class"] == "git"
    assert classify(table, "Bash", {"command": "ls"})["class"] == "shell"
    assert classify(table, "Agent", {"subagent_type": "gstack-execution:explore"})["class"] == "explore-subagent"
    assert classify(table, "Agent", {"subagent_type": "finance:finance"})["class"] == "department-subagent"
    assert classify(table, "Teleport", {})["class"] == "unclassified"
    assert decide({"risky": 0.70, "docs_only": 0.95})["tier"] == "floor"
    assert decide({"risky": 0.69, "docs_only": 0.95})["tier"] == "light"
    assert decide({"trust_boundary": 0.30})["rule"] == "trust_boundary"
    assert decide({"docs_only": 0.60, "has_tests": 0.50})["tier"] == "standard"
    assert cos_run_command('python3 "$P/scripts/route.py" cos-run start 2026-10-14-x') == ("start", "2026-10-14-x")
    assert cos_run_command('python3 "${CLAUDE_PLUGIN_ROOT}/../model-router/scripts/route.py" cos-run end') == ("end", None)
    assert cos_run_command("python3 plugins/model-router/scripts/route.py cos-run end\n") == ("end", None)
    assert cos_run_command("scripts/route.py cos-run start r9") == ("start", "r9")
    for text in ("cd /p && python3 route.py cos-run end", "rg -n 'route.py cos-run end' plugins", "echo python3 route.py cos-run end",
                 "echo ';' python3 route.py cos-run end ';'", "echo prefix'; python3 route.py cos-run end; suffix'",
                 "python3 route.py cos-run end; ls", "# python3 route.py cos-run end", "cat <<'EOF'\npython3 route.py cos-run end\nEOF\n",
                 "python3 -c \"print(1)\" route.py cos-run end", "python3 route.py cos-run start 'two words'", "ls\npython3 route.py cos-run end",
                 "#route.py cos-run end", "'#route.py' cos-run end", "`x`route.py cos-run end", "$(x)route.py cos-run end",
                 "python3 route.py\ncos-run end", "python3 route.py cos-run\nend", "python3 route.py cos-run start\nr1", "python3\nroute.py cos-run end"):
        assert cos_run_command(text) is None, text
    print(f"route.py selftest: examined {len(table['classes'])} ontology classes, 4 rule boundaries and 23 cos-run command shapes, all passed")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
