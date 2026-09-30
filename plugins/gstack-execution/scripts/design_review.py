#!/usr/bin/env python3
"""XE-031: a design doc is argued by two reviewers in turn before a human reads it.

The state machine behind `/gstack-plan-review critics=2 target=design`. The command writes the
prompts and the revisions; this file owns everything a model must not decide for itself: who may
review, which findings are open, when one closes, and whether the loop converged, stalled, hit
its cap or ended incomplete. Stdlib only.

  design_review.py init    <state> --writer claude --draft <file> --log <md> [--cap 20]
  design_review.py review  <state> --slot r1|r2 --draft <file> --prompt <file> [--root <dir>]
  design_review.py writer  <state> --dispositions <json> --draft <file>
  design_review.py status  <state>
  design_review.py dissent <state>
  design_review.py finish  <state> [--measure-dir <dir>]
"""
import argparse, hashlib, json, os, sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import peer_review as pr  # noqa: E402
from enclosure import enclose  # noqa: E402

DEFAULT_CAP = 20
SEVERITIES = {"material", "minor"}
KINDS = {"finding", "policy_proposal"}
STANCES = {"agree", "disagree", "extend"}
WRITER = {"accepted", "rejected", "deferred"}   # plus "duplicate of <ID>"

# OpenAI-strict (every object closed, every property required) so codex --output-schema takes it.
_OPEN = {"type": "object", "additionalProperties": False, "required": ["id", "status", "reason"],
         "properties": {"id": {"type": "string"}, "status": {"type": "string", "enum": ["resolved", "still_open"]},
                        "reason": {"type": "string"}}}
_STANCE = {"type": "object", "additionalProperties": False, "required": ["id", "stance", "reason"],
           "properties": {"id": {"type": "string"}, "stance": {"type": "string", "enum": sorted(STANCES)},
                          "reason": {"type": "string"}}}
_NEW = {"type": "object", "additionalProperties": False, "required": ["severity", "kind", "text"],
        "properties": {"severity": {"type": "string", "enum": sorted(SEVERITIES)},
                       "kind": {"type": "string", "enum": sorted(KINDS)}, "text": {"type": "string"}}}
SCHEMA = {"type": "object", "additionalProperties": False,
          "required": ["verdict", "open_findings", "stances", "new_findings"],
          "properties": {"verdict": {"type": "string", "enum": ["APPROVED", "REVISE"]},
                         "open_findings": {"type": "array", "items": _OPEN},
                         "stances": {"type": "array", "items": _STANCE},
                         "new_findings": {"type": "array", "items": _NEW}}}


class Malformed(Exception):
    pass


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load(p):
    return json.loads(Path(p).read_text())


def save(p, s):
    Path(p).write_text(json.dumps(s, indent=1))


def log(s, text):
    with open(s["log"], "a", encoding="utf-8") as f:
        f.write(text.rstrip("\n") + "\n\n")


PING = {"type": "object", "additionalProperties": False, "required": ["ok"], "properties": {"ok": {"type": "boolean"}}}


def ready(tool, calls=None):
    """(ok, why). One tiny real call through the same path a review uses, so a candidate is ready only
    if its CLI or key, its auth, its configured model and the model floor all answer (criterion 4).
    A failure's own words become the reason."""
    import tempfile
    model, result = None, None
    pr.LAST_REVIEWER_USAGE = "not_reported"
    try:
        text, model = pr.run_reviewer(tool, 'Readiness check. Reply with {"ok": true} and nothing else.',
                                      Path(tempfile.mkdtemp()), 300, PING)
        result = (True, f"answered as {model}") if json.loads(text).get("ok") is True \
            else (False, f"answered, but not with ok: true ({text[:80]!r})")
    except pr.ReviewError as e:
        result = (False, f"{e.outcome}: {e.detail}")
    except (ValueError, AttributeError) as e:
        result = (False, f"unreadable readiness reply: {e}")
    finally:   # review F8: a readiness call is a model call, so it is counted like any other
        if calls is not None:
            calls.append({"round": 0, "slot": "ready", "tool": tool, "model": model,
                          "usage": getattr(pr, "LAST_REVIEWER_USAGE", "not_reported"),
                          "error": None if result and result[0] else (result[1] if result else "no result")})
    return result


def choose(writer, probe=ready, calls=None):
    """(r1, r2): two ready reviewers from two families, neither the writer's (criterion 4)."""
    wf, tried, picked = pr.family(writer), [], []
    for t in pr.REVIEWER_ORDER:
        fam = pr.REVIEWERS[t]["family"]
        if fam == wf or fam in {pr.family(p) for p in picked}:
            continue
        ok, why = probe(t, calls)
        if not ok:
            tried.append(f"{t} ({fam}): {why}")
            continue
        picked.append(t)
        if len(picked) == 2:
            return tuple(picked)
    raise SystemExit("design review needs two reviewers from two families other than the writer's "
                     f"({wf}); found {picked or 'none'}. Tried: " + "; ".join(tried or ["nothing else in REVIEWER_ORDER"])
                     + ". No same-family stand-in is used.")


def init(state, writer, draft, logpath, cap=DEFAULT_CAP, probe=ready):
    calls = []
    r1, r2 = choose(writer, probe, calls)
    s = {"writer": writer, "reviewers": {"r1": r1, "r2": r2}, "cap": cap, "round": 0, "log": str(logpath),
         "hash": sha(draft), "findings": {}, "policy_proposals": [], "rounds": [], "stalls": 0,
         "outcome": None, "failure": None, "calls": calls}
    save(state, s)
    log(s, f"# Design review log\n\nWriter `{writer}`; reviewer 1 `{r1}` ({pr.family(r1)}); "
           f"reviewer 2 `{r2}` ({pr.family(r2)}); cap {cap} rounds.")
    return s


def open_ids(s):
    return sorted(i for i, f in s["findings"].items() if f["open"])


def validate(s, slot, reply, new_r1):
    """Raises Malformed unless the reply accounts for every open finding (criterion 3)."""
    if not isinstance(reply, dict) or reply.get("verdict") not in ("APPROVED", "REVISE"):
        raise Malformed("verdict must be APPROVED or REVISE")
    for k in ("open_findings", "stances", "new_findings"):
        if not isinstance(reply.get(k), list) or not all(isinstance(x, dict) for x in reply[k]):
            raise Malformed(f"{k} must be a list of objects")
        if k != "new_findings" and not all(isinstance(x.get("id"), str) and isinstance(x.get("reason"), str)
                                           and x["reason"].strip() for x in reply[k]):
            raise Malformed(f"every {k} entry needs a string id and a reason")
    must = set(open_ids(s))   # reviewer 2 included: reviewer 1's new findings are open too
    seen = {o["id"] for o in reply["open_findings"]}
    if must - seen:
        raise Malformed(f"reply omits open finding(s) {sorted(must - seen)}")
    if any(o.get("status") not in ("resolved", "still_open") for o in reply["open_findings"]):
        raise Malformed("open_findings status must be resolved or still_open")
    if slot == "r2":
        st = {x.get("id") for x in reply["stances"]}
        if set(new_r1) - st:
            raise Malformed(f"reviewer 2 gives no stance on reviewer 1's {sorted(set(new_r1) - st)}")
        if any(x.get("stance") not in STANCES for x in reply["stances"]):
            raise Malformed("stance must be agree, disagree or extend")
    for n in reply["new_findings"]:
        if n.get("severity") not in SEVERITIES or n.get("kind") not in KINDS or not isinstance(n.get("text"), str) or not n["text"].strip():
            raise Malformed("each new finding needs severity, kind and text")


def review(state, slot, draft, prompt, runner=None, root="."):
    """Run one reviewer turn: one retry of the same reviewer and model, then `incomplete` (criterion 8)."""
    s = load(state)
    if s["outcome"]:
        raise SystemExit(f"loop already ended: {s['outcome']}")
    h = sha(draft)
    if h != s["hash"]:
        raise SystemExit(f"draft hash {h[:12]} is not the revision under review ({s['hash'][:12]})")
    if slot == "r1":
        s["round"] += 1
        s["rounds"].append({"n": s["round"], "hash": h})
    rnd = s["rounds"][-1]
    if slot == "r2" and "r1" not in rnd:
        raise SystemExit("reviewer 2 runs after reviewer 1 in the same round")
    tool = s["reviewers"][slot]
    runner = runner or (lambda t, p: pr.run_reviewer(t, p, Path(root), 1800, SCHEMA))
    new_r1 = rnd.get("r1", {}).get("new", []) if slot == "r2" else []
    reply, why = None, None
    for attempt in (1, 2):   # criterion 8: one retry, and only for a malformed reply
        model, err = None, None
        pr.LAST_REVIEWER_USAGE = "not_reported"
        try:
            text, model = runner(tool, Path(prompt).read_text())
            reply = json.loads(text)
            validate(s, slot, reply, new_r1)
        except pr.ReviewError as e:          # timeout, quota, transport: the loop ends, no retry
            err, reply = f"{e.outcome}: {e.detail}", None
            why = f"attempt {attempt}: {err}"
        except (Malformed, ValueError, TypeError, AttributeError) as e:
            err, reply = f"malformed: {e}", None
            why = f"attempt {attempt}: {err}"
        finally:
            s["calls"].append({"round": s["round"], "slot": slot, "tool": tool, "model": model,
                               "usage": getattr(pr, "LAST_REVIEWER_USAGE", "not_reported"), "error": err})
        if reply is not None or not err.startswith("malformed"):
            break
    if reply is None:
        s["outcome"], s["failure"] = "incomplete", {"round": s["round"], "slot": slot, "tool": tool, "why": why}
        save(state, s)
        log(s, f"## Round {s['round']}: {slot} ({tool}) failed\n\n{why}\n\nOutcome `incomplete`. No other reviewer was substituted.")
        return s
    me = slot
    for o in reply["open_findings"]:
        f = s["findings"].get(o["id"])
        if f and f["open"] and o["status"] == "resolved" and f["raised_by"] == me:
            f["open"] = False
            f["closed_by"] = f"{me} resolved in round {s['round']}"
    new = []
    for k, n in enumerate(reply["new_findings"], 1):
        fid = f"R{s['round']}-{slot}-{k}"
        if n["kind"] == "policy_proposal":
            s["policy_proposals"].append({"id": fid, "raised_by": slot, "round": s["round"], "text": n["text"]})
            continue
        s["findings"][fid] = {"raised_by": slot, "round": s["round"], "severity": n["severity"], "text": n["text"],
                              "open": True, "disposition": None}
        new.append(fid)
    rnd[slot] = {"verdict": reply["verdict"], "new": new,
                 "stances": {x["id"]: x for x in reply["stances"]} if slot == "r2" else {}}
    log(s, f"## Round {s['round']}: {slot} ({tool}), revision `{h[:12]}`\n\n" + enclose(f"reviewer {tool}", json.dumps(reply, indent=1)))
    if slot == "r2":
        settle_after_reviews(s)
    save(state, s)
    return s


def settle_after_reviews(s):
    rnd = s["rounds"][-1]
    material_open = [i for i in open_ids(s) if s["findings"][i]["severity"] == "material"]
    if rnd["r1"]["verdict"] == rnd["r2"]["verdict"] == "APPROVED" and not material_open:
        s["outcome"] = "converged"            # criterion 5: both approve this revision hash
    # criterion 6: the cap is decided in writer(), after this round's findings are disposed of


def writer(state, dispositions, draft):
    """The writer disposes of this round's new findings and hands over the next revision."""
    s = load(state)
    if s["outcome"]:
        raise SystemExit(f"loop already ended: {s['outcome']}")
    rnd = s["rounds"][-1]
    if "r2" not in rnd:
        raise SystemExit("the writer revises after both reviewers")
    new = rnd["r1"]["new"] + rnd["r2"]["new"]
    missing = [i for i in new if i not in dispositions]
    if missing:
        raise SystemExit(f"no disposition for {missing}")
    for fid, d in dispositions.items():
        f = s["findings"].get(fid)
        if not f:
            raise SystemExit(f"unknown finding {fid}")
        value, reason = d.get("disposition", ""), d.get("reason", "")
        if value.startswith("duplicate of "):
            orig = value[len("duplicate of "):].strip()
            if orig not in s["findings"] or orig == fid:
                raise SystemExit(f"{fid}: {value} names no other finding")
            f.update(open=False, disposition=value, closed_by=f"merged into {orig}")
            s["findings"][orig]["open"] = True          # the original stays open; a reissue closes nothing
            continue
        if value not in WRITER:
            raise SystemExit(f"{fid}: disposition must be accepted, rejected, deferred or 'duplicate of <ID>'")
        if value in ("rejected", "deferred") and not reason.strip():
            raise SystemExit(f"{fid}: {value} needs a reason")
        f["disposition"], f["reason"] = value, reason
        if f["severity"] == "minor":
            f["open"] = False                            # a minor finding closes on the writer's disposition
            f["closed_by"] = f"writer {value}"
    s["hash"] = sha(draft)
    # criterion 7. The key is the revision handed to the next round plus every finding and whether it
    # is open. A finding merged as a duplicate is left out, so a reissue can't reset the count.
    state_now = sorted([i, f["open"]] for i, f in s["findings"].items() if not str(f.get("disposition") or "").startswith("duplicate of "))
    key = [s["hash"], state_now]
    prev = s["rounds"][-2].get("key") if len(s["rounds"]) > 1 else None
    rnd["key"] = key
    s["stalls"] = s["stalls"] + 1 if key == prev else 0
    if s["stalls"] >= 2:
        s["outcome"] = "stalled"
    elif s["round"] >= s["cap"]:
        s["outcome"] = "cap_reached"
    log(s, f"## Round {s['round']}: writer\n\n" + "\n".join(
        f"- `{fid}`: {d.get('disposition')}" + (f" ({d['reason']})" if d.get("reason") else "") for fid, d in dispositions.items())
        + f"\n\nOpen after round {s['round']}: {', '.join(open_ids(s)) or 'none'}. Next revision `{s['hash'][:12]}`.")
    save(state, s)
    return s


def dissent(s):
    rows = [i for i in open_ids(s)]
    if not rows:
        return ""
    out = ["## Dissent", "", "| Finding | Held by | Raised in round | Writer's position |", "|---|---|---|---|"]
    for i in rows:
        f = s["findings"][i]
        pos = f"{f['disposition']}: {f.get('reason', '')}" if f["disposition"] else "not yet disposed"
        out.append(f"| `{i}` ({f['severity']}): {f['text']} | {s['reviewers'][f['raised_by']]} | {f['round']} | {pos} |")
    return "\n".join(out) + "\n"


def summary(s):
    return {"outcome": s["outcome"] or "in_progress", "round": s["round"], "open": open_ids(s),
            "policy_proposals": s["policy_proposals"], "log": s["log"], "failure": s["failure"],
            "reviewers": s["reviewers"]}


def finish(state, measure_dir=None):
    """Writes the XE-012 run note: every reviewer call, with its usage as reported."""
    s = load(state)
    if not measure_dir:
        return None
    import measure
    per = [c["usage"] for c in s["calls"]]
    totals = [u.get("total") for u in per if isinstance(u, dict) and u.get("total") is not None]
    rec = {"type": "gstack-design-review", "run_id": Path(state).stem, "recorded_at": datetime.now(timezone.utc).isoformat(),
           "outcome": s["outcome"], "rounds": s["round"], "reviewers": list(s["reviewers"].values()),
           "reviewer_calls": len(s["calls"]), "reviewer_tokens_per_call": per,
           "reviewer_tokens": sum(totals) if totals and len(totals) == len(per) else None,
           "origin": "gate_output"}
    if rec["reviewer_tokens"] is None:
        rec["reviewer_tokens_reason"] = "not reported for every call" if per else "no calls ran"
    Path(measure_dir).mkdir(parents=True, exist_ok=True)
    p = Path(measure_dir) / f"{rec['recorded_at'][:10]}-{rec['run_id']}.md"
    p.write_text(measure.note_text(rec, f"# design review {rec['run_id']}\n"))
    return p


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    i = sub.add_parser("init"); i.add_argument("state"); i.add_argument("--writer", required=True)
    i.add_argument("--draft", required=True); i.add_argument("--log", required=True); i.add_argument("--cap", type=int, default=DEFAULT_CAP)
    r = sub.add_parser("review"); r.add_argument("state"); r.add_argument("--slot", choices=["r1", "r2"], required=True)
    r.add_argument("--draft", required=True); r.add_argument("--prompt", required=True); r.add_argument("--root", default=".")
    w = sub.add_parser("writer"); w.add_argument("state"); w.add_argument("--dispositions", required=True); w.add_argument("--draft", required=True)
    for n in ("status", "dissent"):
        sub.add_parser(n).add_argument("state")
    f = sub.add_parser("finish"); f.add_argument("state"); f.add_argument("--measure-dir")
    a = ap.parse_args(argv)
    if a.cmd == "init":
        s = init(a.state, a.writer, a.draft, a.log, a.cap)
    elif a.cmd == "review":
        s = review(a.state, a.slot, a.draft, a.prompt, root=a.root)
    elif a.cmd == "writer":
        s = writer(a.state, load(a.dispositions), a.draft)
    elif a.cmd == "dissent":
        print(dissent(load(a.state)), end="")
        return 0
    elif a.cmd == "finish":
        print(finish(a.state, a.measure_dir) or "no measure dir given; nothing recorded")
        return 0
    else:
        s = load(a.state)
    print(json.dumps(summary(s), indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
