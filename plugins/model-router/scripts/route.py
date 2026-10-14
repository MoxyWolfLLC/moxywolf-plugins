#!/usr/bin/env python3
"""MR-003: every call is classified against an ontology, and only the calls that carry a model
choice ask Jev.

Three hooks and two commands, stdlib only:

  route.py session-start   (hook JSON on stdin)  opens the session ledger
  route.py pre-tool-use    (hook JSON on stdin)  classifies the call; may return updatedInput
  route.py session-end     (hook JSON on stdin)  appends the session summary line
  route.py score --dir D                         counts a ledger directory
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
    c = classify(table, tool, tin)
    line = {"ts": now(), "class": c["class"], "tool": tool, "routed": False, "tool_use_id": h.get("tool_use_id")}
    if tool == "Agent":
        line["subagent_type"] = tin.get("subagent_type")
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
    if c["class"] in FLOOR_LOCKED and tier != "floor":
        line["floor_locked_from"] = tier; tier = "floor"
    if tier is None:                      # unclassified Agent with Jev unavailable: unchanged
        append(path, line); return 0
    line.update(tier=tier, decided_by=decided_by, model=table["tiers"][tier])
    if tool != "Agent":                   # a script chooses its own model; the tier is recorded, not applied
        line["note"] = "script selects its own model"
        append(path, line); return 0
    if tin.get("model"):                  # MR-001.7: a caller's explicit choice stands and is recorded
        line.update(caller_model=tin["model"], decided_by=f"caller ({decided_by} advised {table['tiers'][tier]})")
        append(path, line); return 0
    line["routed"] = True
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
            "sessions": sum(1 for l in lines if l.get("event") == "session_start")}


def print_score(s, d):
    print(f"ledger {d}: {s['files']} files, {s['lines']} lines, {s['sessions']} sessions, {s['calls']} calls, {s['unclassified']} unclassified")
    row = lambda p: f"{p['calls']} calls, {p['routed']} routed, {p['jev']} Jev consults ({p['jev_unavailable']} unavailable), {p['unclassified']} unclassified"
    for c, p in s["per_class"].items():
        print(f"  {c:<22} {row(p)}")
    for t in TIERS:
        print(f"  tier {t:<9} {row(s['per_tier'][t])}")


# ---- entry ----

def main(argv):
    if not argv or argv[0] in ("-h", "--help"):
        print(__doc__); return 0
    cmd = argv[0]
    if cmd == "--selftest":
        return selftest()
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
    assert classify(table, "Agent", {"subagent_type": "finance:finance"})["class"] == "unclassified"
    assert classify(table, "Teleport", {})["class"] == "unclassified"
    assert decide({"risky": 0.70, "docs_only": 0.95})["tier"] == "floor"
    assert decide({"risky": 0.69, "docs_only": 0.95})["tier"] == "light"
    assert decide({"trust_boundary": 0.30})["rule"] == "trust_boundary"
    assert decide({"docs_only": 0.60, "has_tests": 0.50})["tier"] == "standard"
    print(f"route.py selftest: examined {len(table['classes'])} ontology classes and 4 rule boundaries, all passed")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
