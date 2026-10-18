#!/usr/bin/env python3
"""DC-001: the decider council. Typed questions go to three decision models from three vendors on
one wire, the AI Gateway's OpenAI-compatible /v1/decisions endpoint; the majority answers; every
call lands on one ledger with its caller, and the caller writes the outcome later.

  decider_council.py ask --caller <name> --ref <id> --input <file|-> --questions <file|json>
                         [--voices a,b,c] [--timeout-ms 8000]
  decider_council.py outcome --line <id> --result <json>
  decider_council.py score [--caller <name>] [--since YYYY-MM]
  decider_council.py gate --caller <name>

Majority (Dorian, 2026-10-18: "Majority wins"): for a choice, the value more than half the available
voices picked; for a predicate or a score, the median. No majority is a tie, returned as a tie.
Code decides what an answer means: this script carries no bar, no tier and no policy. The caller's
rule table does, and it registers the rule that scores an outcome in OUTCOME_RULES below.

Availability is a property of answers, not of HTTP: a voice that returns 200 and refuses, or answers
out of shape, is unavailable for that question (review 20261018-100213 F1). The request bytes are
serialized once and sent to each slug with only the leading `model` member different (F9). The
whole call, connection and body read, is bounded by one deadline per voice (F5). The ledger is
append-and-rewrite under one file lock (F3).

Stdlib only. The env JEV_ENDPOINT replaces the gateway base URL so tests run against a stub. The key
resolves from AI_GATEWAY_API_KEY, then the file GSTACK_AIGATEWAY_ENV names, then the vault paths
`plugins/council/scripts/jev_route.py` already knows.
ponytail: one request body, built once; three daemon threads; a JSONL file under flock.
"""
import argparse
import fcntl
import json
import os
import statistics
import sys
import tempfile
import threading
import time
import urllib.error
import urllib.request
import uuid
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

GATEWAY = "https://ai-gateway.vercel.sh"
DECIDERS = ["typesafe-ai/jev", "perplexity/pplx-decider-v1.2", "openai/gpt-6-luna-decisions"]
DECIDER_TIMEOUT_MS = 8000
AGREE_BAND = 0.15          # numbers within this of the median count as agreement
GATE_MIN_LINES = 20        # DC-001.6
QUESTION_TYPES = ("predicate", "choice", "score")


# ---------- credentials and paths ----------

def gateway_key():
    """AI_GATEWAY_API_KEY from the environment, else the file GSTACK_AIGATEWAY_ENV names, else the
    vault paths jev_route.py already knows. Returns (key, source) or (None, why)."""
    if os.environ.get("AI_GATEWAY_API_KEY"):
        return os.environ["AI_GATEWAY_API_KEY"], "env AI_GATEWAY_API_KEY"
    f = os.environ.get("GSTACK_AIGATEWAY_ENV")
    if f:
        try:
            for raw in Path(f).read_text(encoding="utf-8").splitlines():
                k, _, v = raw.strip().partition("=")
                if k.replace("export ", "").strip() == "AI_GATEWAY_API_KEY" and v.strip():
                    return v.strip().strip("\"'"), f
            return None, f"{f} sets no AI_GATEWAY_API_KEY"
        except OSError as e:
            return None, f"{f} could not be read ({e.strerror})"
    try:
        from jev_route import load_gateway_key  # noqa: WPS433
        key, src = load_gateway_key(return_source=True)
        return key, src
    except Exception as e:  # JevUnavailable or import trouble: both mean no key
        return None, str(e).splitlines()[0] if str(e) else "no key"


def ledger_dir():
    root = os.environ.get("GSTACK_PEER_REVIEW_DIR")
    d = Path(root) / "decisions" if root else Path.home() / ".gstack" / "decisions"
    d.mkdir(parents=True, exist_ok=True)
    return d


class ledger_lock:
    """One flock for every append and every read-modify-replace of the ledger (F3)."""

    def __enter__(self):
        self.fh = open(ledger_dir() / ".lock", "a")
        fcntl.flock(self.fh, fcntl.LOCK_EX)
        return self

    def __exit__(self, *exc):
        fcntl.flock(self.fh, fcntl.LOCK_UN)
        self.fh.close()


def voices():
    raw = os.environ.get("GSTACK_DECIDERS")
    return [v.strip() for v in raw.split(",") if v.strip()] if raw else list(DECIDERS)


# ---------- the wire ----------

def request_bytes(model, payload):
    """The body for one voice: the shared payload bytes with `model` as the leading member and
    nothing else different (F9). `payload` is `json.dumps(body)` done once; it starts with '{'."""
    return b'{"model": ' + json.dumps(model).encode() + b", " + payload.encode()[1:]


def post(model, payload, key, deadline):
    """One /v1/decisions call bounded by `deadline` (a time.monotonic() instant) covering the
    connection and the whole body read (F5). Returns {status, latency_ms, response|error}."""
    req = urllib.request.Request(
        os.environ.get("JEV_ENDPOINT", GATEWAY).rstrip("/") + "/v1/decisions", data=request_bytes(model, payload),
        headers={"Authorization": "Bearer " + key, "Content-Type": "application/json"}, method="POST")
    t = time.monotonic()
    out = {}
    try:
        left = deadline - time.monotonic()
        if left <= 0:
            raise TimeoutError("deadline passed before the call")
        with urllib.request.urlopen(req, timeout=left) as r:
            chunks = []
            while True:
                if time.monotonic() > deadline:
                    raise TimeoutError("deadline passed while reading the body")
                c = r.read(65536)
                if not c:
                    break
                chunks.append(c)
            out = {"status": r.status, "response": json.loads(b"".join(chunks).decode())}
    except urllib.error.HTTPError as e:
        out = {"status": e.code, "error": e.read(2000).decode(errors="replace")[:500]}
    except TimeoutError as e:
        out = {"status": "timeout", "error": str(e)}
    except Exception as e:  # socket timeout, refused, bad JSON
        name = type(e).__name__
        out = {"status": "timeout" if "timed out" in str(e) else "error", "error": f"{name}: {e}"[:500]}
    out["latency_ms"] = int((time.monotonic() - t) * 1000)
    return out


def ask_all(payload, key, timeout_ms, slugs):
    """Every voice at once, each on a daemon thread, all abandoned at the deadline (F5)."""
    deadline = time.monotonic() + timeout_ms / 1000
    results = {}

    def one(m):
        results[m] = post(m, payload, key, deadline)
    ts = {m: threading.Thread(target=one, args=(m,), daemon=True) for m in slugs}
    for t in ts.values():
        t.start()
    for m, t in ts.items():
        t.join(max(0.0, deadline - time.monotonic()))
        if t.is_alive() or m not in results:
            results[m] = {"status": "timeout", "error": f"no answer within {timeout_ms} ms", "latency_ms": timeout_ms}
    return results


# ---------- reading answers ----------

def unit(p):
    return isinstance(p, (int, float)) and not isinstance(p, bool) and 0.0 <= p <= 1.0


def envelope(resp):
    """The response's answers by name, or (None, why) when the envelope is not the documented
    shape: an object whose `answers` is a list of objects (F4)."""
    if not isinstance(resp, dict):
        return None, "malformed response: not an object"
    ans = resp.get("answers")
    if not isinstance(ans, list) or not all(isinstance(a, dict) for a in ans):
        return None, "malformed response: answers is not a list of objects"
    return {a.get("name"): a for a in ans}, None


def answer_for(q, by_name):
    """The voice's answer to question q, or (None, why). Well-formedness checks are the ones
    jev_route.well_formed applies, re-expressed for the /v1/decisions shape."""
    a = by_name.get(q["name"])
    if a is None:
        return None, "missing"
    if a.get("type") == "refusal":
        return None, "refusal"
    if q["type"] == "predicate":
        return (a, None) if unit(a.get("probability")) else (None, "malformed probability")
    probs = a.get("probabilities")
    if probs is not None:
        try:
            ps = [x["probability"] for x in probs]
        except (KeyError, TypeError):
            return None, "malformed probabilities"
        if not all(unit(p) for p in ps) or abs(sum(ps) - 1) > 0.01:
            return None, "probabilities do not sum to 1"
    if q["type"] == "choice":
        offered = {c["value"] for c in q["choices"]}
        return (a, None) if a.get("choice") in offered else (None, "choice not offered")
    n = len(q["levels"])
    s = a.get("score")
    ok = isinstance(s, (int, float)) and not isinstance(s, bool) and 0 <= s <= n - 1
    return (a, None) if ok else (None, "score outside levels")


def majority(q, answers):
    """answers: {slug: answer dict} for the available voices. Returns the quorum fields."""
    n = len(answers)
    if q["type"] == "choice":
        votes = {}
        for a in answers.values():
            votes[a["choice"]] = votes.get(a["choice"], 0) + 1
        top = max(votes.items(), key=lambda kv: kv[1]) if votes else (None, 0)
        win = top[0] if n >= 2 and top[1] * 2 > n else None
        return {"majority": win, "tie": win is None, "agreed": n >= 2 and len(votes) == 1}
    key = "probability" if q["type"] == "predicate" else "score"
    xs = [a[key] for a in answers.values()]
    if n < 2:
        return {"majority": None, "tie": True, "agreed": False}
    med = statistics.median(xs)
    return {"majority": med, "tie": False, "agreed": all(abs(x - med) <= AGREE_BAND for x in xs)}


def agrees(q, answer, maj):
    """Does one voice's answer agree with the majority? (per-voice agreement, F2)"""
    if maj is None:
        return None
    if q["type"] == "choice":
        return answer["choice"] == maj
    v = answer["probability" if q["type"] == "predicate" else "score"]
    return abs(v - maj) <= AGREE_BAND


def validate_questions(qs):
    if not isinstance(qs, list) or not qs:
        raise ValueError("questions must be a non-empty list")
    names = set()
    for q in qs:
        if q.get("type") not in QUESTION_TYPES or not q.get("instructions") or not q.get("name"):
            raise ValueError(f"each question needs type in {QUESTION_TYPES}, name and instructions: {q}")
        if q["name"] in names:
            raise ValueError(f"duplicate question name {q['name']}")
        names.add(q["name"])
        if q["type"] == "choice" and not (1 <= len(q.get("choices") or []) <= 255):
            raise ValueError(f"{q['name']}: choice needs 1 to 255 choices")
        if q["type"] == "score" and not (2 <= len(q.get("levels") or []) <= 10):
            raise ValueError(f"{q['name']}: score needs 2 to 10 levels")


def quorum_of(answers):
    """full when every question has at least two available voices, degraded when every question
    has one, unavailable when any question has none (F1)."""
    low = min(a["available"] for a in answers.values())
    return "full" if low >= 2 else ("degraded" if low == 1 else "unavailable")


# ---------- commands ----------

def cmd_ask(a):
    text = sys.stdin.read() if a.input == "-" else Path(a.input).read_text(encoding="utf-8")
    qs = json.loads(Path(a.questions).read_text(encoding="utf-8")) if os.path.exists(a.questions) else json.loads(a.questions)
    validate_questions(qs)
    key, source = gateway_key()
    slugs = [v.strip() for v in a.voices.split(",")] if a.voices else voices()
    payload = json.dumps({"input": text, "questions": qs})
    line_id = uuid.uuid4().hex[:12]
    voice_rows, by_q = [], {q["name"]: {} for q in qs}
    raw = ask_all(payload, key, a.timeout_ms, slugs) if key else {m: {"status": "no_key", "error": source, "latency_ms": 0} for m in slugs}
    for m in slugs:
        r = raw[m]
        row = {"model": m, "status": r.get("status"), "latency_ms": r["latency_ms"], "cost": None, "input_tokens": None,
               "answered": 0, "questions": len(qs)}
        try:
            resp = r.get("response") if r.get("status") == 200 else None
            transport = f"HTTP {r['status']}" if isinstance(r.get("status"), int) else (r.get("error") or str(r.get("status")))
            by_name, why = envelope(resp) if resp is not None else (None, transport)
            if by_name is not None:
                gw = resp.get("provider_metadata") if isinstance(resp.get("provider_metadata"), dict) else {}
                gw = gw.get("gateway") if isinstance(gw.get("gateway"), dict) else {}
                row["cost"] = gw.get("cost")
                usage = resp.get("usage") if isinstance(resp.get("usage"), dict) else {}
                row["input_tokens"] = usage.get("input_tokens")
            reasons = []
            for q in qs:
                ans, qwhy = answer_for(q, by_name) if by_name is not None else (None, why)
                if ans is None:
                    reasons.append(qwhy)
                    by_q[q["name"]][m] = {"unavailable": qwhy}
                else:
                    row["answered"] += 1
                    by_q[q["name"]][m] = ans
        except Exception as e:  # a voice that breaks the reader is unavailable, never a crash (F4)
            reasons = [f"internal: {type(e).__name__}: {e}"[:200]]
            for q in qs:
                by_q[q["name"]][m] = {"unavailable": reasons[0]}
            row["answered"] = 0
        if row["answered"] == 0:
            row["unavailable"] = reasons[0] if reasons else "no answer"
        if r.get("error") and isinstance(r.get("status"), int) and r["status"] != 200:
            row["error"] = r["error"]
            row["unavailable"] = f"HTTP {r['status']}"
        voice_rows.append(row)
    answers = {}
    for q in qs:
        avail = {m: v for m, v in by_q[q["name"]].items() if "unavailable" not in v}
        maj = majority(q, avail)
        answers[q["name"]] = {"type": q["type"], **maj, "by_voice": by_q[q["name"]], "available": len(avail),
                              "agrees": {m: agrees(q, v, maj["majority"]) for m, v in avail.items()}}
    quorum = quorum_of(answers)
    line = {"id": line_id, "ts": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "caller": a.caller, "ref": a.ref, "questions": [{"name": q["name"], "type": q["type"]} for q in qs],
            "voices": voice_rows, "answers": answers, "quorum": quorum, "credential": source if key else None,
            "outcome": None}
    f = ledger_dir() / (datetime.now(timezone.utc).strftime("%Y%m") + ".jsonl")
    with ledger_lock(), open(f, "a", encoding="utf-8") as fh:          # DC-001.4: written before the output prints
        fh.write(json.dumps(line, sort_keys=True) + "\n")
    out = dict(line, ledger=str(f))
    del out["outcome"]
    print(json.dumps(out, indent=None if a.compact else 1))
    return 0 if quorum != "unavailable" else 1


def _lines(since=None):
    for f in sorted(ledger_dir().glob("*.jsonl")):
        if since and f.stem < since.replace("-", ""):
            continue
        for raw in f.read_text(encoding="utf-8").splitlines():
            if raw.strip():
                yield f, json.loads(raw)


def cmd_outcome(a):
    result = json.loads(a.result)
    with ledger_lock():                                               # F3: no append lands between read and replace
        for f in sorted(ledger_dir().glob("*.jsonl")):
            rows = [json.loads(r) for r in f.read_text(encoding="utf-8").splitlines() if r.strip()]
            hit = [r for r in rows if r.get("id") == a.line]
            if not hit:
                continue
            hit[0]["outcome"] = result                    # answers untouched; only the outcome is filled
            fd, tmp = tempfile.mkstemp(prefix=f.stem + ".", suffix=".tmp", dir=str(f.parent))
            with os.fdopen(fd, "w", encoding="utf-8") as fh:
                fh.write("".join(json.dumps(r, sort_keys=True) + "\n" for r in rows))
            os.replace(tmp, f)
            print(json.dumps({"id": a.line, "ledger": str(f), "outcome": result}))
            return 0
    print(f"no ledger line {a.line} under {ledger_dir()}", file=sys.stderr)
    return 2


# ---------- outcome rules: one small function per caller, registered here (DC-001.5) ----------

def _tier(probs):
    """MR-002's rule table over predicate probabilities, copied under its own names so the scorer
    needs nothing from gstack. Returns the tier a voice (or the majority) would have selected."""
    RISKY_BAR, UPGRADE_BAR, DOWNGRADE_BAR, HAS_TESTS_BAR = 0.70, 0.30, 0.60, 0.50
    g = lambda k: probs.get(k) if isinstance(probs.get(k), (int, float)) else 0.0
    if g("risky") >= RISKY_BAR or g("trust_boundary") >= UPGRADE_BAR or g("cross_file") >= UPGRADE_BAR:
        return "floor"
    if g("docs_only") >= DOWNGRADE_BAR and g("has_tests") < HAS_TESTS_BAR:
        return "light"
    return "standard"


def rule_model_select(line):
    """Per voice and for the majority: the tier the MR-002 table gives, and whether it was right.
    As MR-001.5 counts it, a cheap tier is right when the item cleared in at most two rounds with no
    blocking finding; a floor tier is not scored (it cannot be wrong-cheap). Returns
    {who: True|False|None} with None for not scored."""
    o = line.get("outcome") or {}
    cleared = o.get("rounds_used", 99) <= 2 and o.get("blocking_findings", 99) == 0
    out = {}
    who = set()
    for q in line["answers"].values():
        who |= set(q["by_voice"])
    for m in sorted(who) + ["majority"]:
        probs = {}
        for name, q in line["answers"].items():
            v = q["majority"] if m == "majority" else q["by_voice"].get(m, {}).get("probability")
            probs[name] = v
        if any(v is None for v in probs.values()):
            out[m] = None
            continue
        out[m] = None if _tier(probs) == "floor" else cleared
    return out


OUTCOME_RULES = {"model_select": rule_model_select}


def _voice_row():
    return {"calls": 0, "answers": 0, "unavailable": 0, "agree_n": 0, "agree_d": 0, "tie_n": 0, "cost": [], "latency": [], "scored": 0, "right": 0}


def score_rows(lines, caller=None):
    """Per caller and voice: calls, answers, unavailable answers, agreement with the majority, ties,
    cost, latency; over lines with an outcome, matches by the caller's rule (F2). Zeros are zeros."""
    by = {}
    for _, l in lines:
        if caller and l["caller"] != caller:
            continue
        c = by.setdefault(l["caller"], {"calls": 0, "with_outcome": 0, "agreed_q": 0, "tie_q": 0, "questions": 0,
                                        "voices": {}, "majority": {"scored": 0, "right": 0},
                                        "rule": "no outcome rule" if l["caller"] not in OUTCOME_RULES else "registered"})
        c["calls"] += 1
        for q in l["answers"].values():
            c["questions"] += 1
            c["agreed_q"] += bool(q.get("agreed"))
            c["tie_q"] += bool(q.get("tie"))
            for m, v in q["by_voice"].items():
                r = c["voices"].setdefault(m, _voice_row())
                if "unavailable" in v:
                    r["unavailable"] += 1
                    continue
                r["answers"] += 1
                if q.get("tie"):
                    r["tie_n"] += 1
                ag = (q.get("agrees") or {}).get(m)
                if ag is not None:
                    r["agree_d"] += 1
                    r["agree_n"] += bool(ag)
        for v in l["voices"]:
            r = c["voices"].setdefault(v["model"], _voice_row())
            r["calls"] += 1
            if v.get("cost") is not None:
                r["cost"].append(float(v["cost"]))
            if "unavailable" not in v:
                r["latency"].append(v["latency_ms"])
        if l.get("outcome") is not None:
            c["with_outcome"] += 1
            rule = OUTCOME_RULES.get(l["caller"])
            if rule:
                for who, ok in rule(l).items():
                    if ok is None:
                        continue
                    tgt = c["majority"] if who == "majority" else c["voices"].setdefault(who, _voice_row())
                    tgt["scored"] += 1
                    tgt["right"] += bool(ok)
    return by


def rate(d, n="right", dd="scored"):
    return (d[n] / d[dd]) if d[dd] else 0.0


def cmd_score(a):
    by = score_rows(list(_lines(a.since)), a.caller)
    if not by:
        print(f"decisions ledger {ledger_dir()}: 0 lines" + (f" for caller {a.caller}" if a.caller else ""))
        if a.caller:
            print(f"  {a.caller}: 0 calls, 0 with outcome, 0 of 0 questions agreed, 0 ties; majority 0 right of 0 scored; no voices seen")
        return 0
    for name, c in sorted(by.items()):
        print(f"{name}: {c['calls']} calls, {c['with_outcome']} with outcome, {c['agreed_q']} of {c['questions']} questions agreed, "
              f"{c['tie_q']} ties; outcome rule {c['rule']}")
        for m, v in sorted(c["voices"].items()):
            mc = statistics.mean(v["cost"]) if v["cost"] else 0.0
            ml = statistics.median(v["latency"]) if v["latency"] else 0
            print(f"  {m}: {v['calls']} calls, {v['answers']} answers, {v['unavailable']} unavailable answers, "
                  f"agreed with the majority {v['agree_n']} of {v['agree_d']} (rate {rate(v, 'agree_n', 'agree_d'):.3f}), "
                  f"in a tie {v['tie_n']} of {v['answers']} (rate {rate(v, 'tie_n', 'answers'):.3f}), "
                  f"{v['right']} right of {v['scored']} scored (rate {rate(v):.3f}), mean cost {mc:.7f}, median latency {ml} ms")
        print(f"  majority: {c['majority']['right']} right of {c['majority']['scored']} scored (rate {rate(c['majority']):.3f})")
    return 0


def gate_status(caller, lines=None):
    """DC-001.6: pass when the caller has at least GATE_MIN_LINES lines with outcomes in which every
    question had at least two available voices, and the majority's rate is at least Jev's. A
    majority scored over nothing has examined nothing and does not pass (EV-001)."""
    rows = [l for _, l in (lines if lines is not None else _lines())
            if l["caller"] == caller and l.get("outcome") is not None
            and l["answers"] and min(q.get("available", 0) for q in l["answers"].values()) >= 2]
    c = score_rows([(None, l) for l in rows], caller).get(caller)
    maj = c["majority"] if c else {"scored": 0, "right": 0}
    jev = (c or {}).get("voices", {}).get(DECIDERS[0], {"scored": 0, "right": 0})
    ok = len(rows) >= GATE_MIN_LINES and maj["scored"] > 0 and rate(maj) >= rate(jev)
    return {"ok": ok, "lines": len(rows), "needs_lines": GATE_MIN_LINES, "majority_rate": round(rate(maj), 3),
            "majority_scored": maj["scored"], "jev_rate": round(rate(jev), 3), "jev_scored": jev["scored"],
            **({} if ok else {"reason": "insufficient_history"})}


def cmd_gate(a):
    g = gate_status(a.caller)
    print(json.dumps(g))
    return 0 if g["ok"] else 1


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("ask"); s.add_argument("--caller", required=True); s.add_argument("--ref", required=True)
    s.add_argument("--input", required=True); s.add_argument("--questions", required=True)
    s.add_argument("--voices"); s.add_argument("--timeout-ms", type=int, default=DECIDER_TIMEOUT_MS)
    s.add_argument("--compact", action="store_true")
    s = sub.add_parser("outcome"); s.add_argument("--line", required=True); s.add_argument("--result", required=True)
    s = sub.add_parser("score"); s.add_argument("--caller"); s.add_argument("--since")
    s = sub.add_parser("gate"); s.add_argument("--caller", required=True)
    a = p.parse_args(argv)
    return {"ask": cmd_ask, "outcome": cmd_outcome, "score": cmd_score, "gate": cmd_gate}[a.cmd](a)


if __name__ == "__main__":
    sys.exit(main())
