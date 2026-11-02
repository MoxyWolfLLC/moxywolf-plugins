#!/usr/bin/env python3
"""spec_review.py: pairwise requirement consistency review of the items under build (SR-001).

One Messages API call: a Sonnet executor with adaptive thinking and a Fable advisor
(advisor_20260301). The executor reads the scope, consults the advisor before committing to a
reading, and reports every contradiction as the requirements involved, the scenario that triggers
it, and the smallest change that resolves it. Ambiguities are reported separately.

Scope (SR-001.1): with --items, the doc's `## Goal` and `## Constraints and settled decisions`
sections plus each named item's `###` section; without it, the whole file (a goal's PLAN.md).
Every `**Status:**` line is dropped, so moving an item's status leaves its record current.

The advisor tool exists only on the Claude API, not on OpenRouter, so this script is the one place
in the plugin that talks to Anthropic directly. The credential has one home, the vault file
GSTACK_ANTHROPIC_ENV names (ANTHROPIC_API_KEY=...), same convention as GSTACK_OPENROUTER_ENV.

Commands
  run   <doc> [--items A,B]   review the scope; writes reviews/spec-review/<scope>.json and .md
                              beside the doc. exit 0 clean, 2 open contradictions, 1 refused.
  check <doc> [--items A,B]   gate: the record exists, its scope_sha256 matches the scope as it is
                              now, and it lists no contradiction. exit 0 pass, 2 fail.
  --selftest                  stubbed transport; no network.

The record is the evidence, not the exit code: `check` recomputes the scope, never reads a verdict.
A contradiction clears only by revising the doc and re-running; the record has no `resolved` flag.
"""
import argparse
import hashlib
import json
import os
import re
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

API_URL = os.environ.get("GSTACK_ANTHROPIC_URL", "https://api.anthropic.com/v1/messages")
EXECUTOR = os.environ.get("GSTACK_SPEC_EXECUTOR", "claude-sonnet-5-5")
ADVISOR = os.environ.get("GSTACK_SPEC_ADVISOR", "claude-fable-5-1")
BETA = "advisor-tool-2026-03-01"
MAX_RESUMES = 6   # pause_turn resumptions; one per pending advisor call
CONTEXT = ("## Goal", "## Constraints and settled decisions")

SYSTEM = """You have access to an `advisor` tool backed by a stronger reviewer model. It takes NO parameters. When you call advisor(), your entire conversation history is automatically forwarded.

Call advisor BEFORE substantive work: before committing to a reading of the plan, before building on an assumption. Reading the plan is orientation, not substantive work. Declaring a finding is.

Call advisor for design, architecture, and risk questions where you won't touch a file. If your response would be analysis with no other tool calls, call advisor first. That judgment call is exactly where a second opinion is highest-value. Call it again once you have drafted your findings, before declaring done.

Give the advice serious weight. If the plan's own text contradicts a specific claim, adapt. If your reading points one way and the advisor points another, don't silently switch: surface the conflict in one more advisor call and ask which constraint breaks the tie.

You review MoxyWolf build plans before anything gets built. Cross-check every requirement against every other one and against the constraints. Most conflicts hide in pairs that each read fine alone. A contradiction is two or more requirements that cannot both be satisfied in some reachable scenario. An ambiguity is a requirement whose satisfaction cannot be decided from the plan's text.

Quote requirements by the identifier the plan gives them (item id plus criterion number, or the constraint's heading). Never invent a requirement the plan does not state.

End your reply with exactly one fenced ```json block, nothing after it, of the shape:
{"contradictions": [{"id": "C1", "requirements": ["<id>", "<id>"], "scenario": "<what triggers it>", "smallest_change": "<the fix>"}],
 "ambiguities": [{"id": "A1", "requirements": ["<id>"], "question": "<what must be decided>"}]}
Empty lists are fine. The prose above the block is for the human; the block is what the gate reads."""

ADVISOR_STEER = ("(Advisor: list only the requirement pairs you believe conflict or are ambiguous, "
                 "one line each, no explanation. The executor will write up the scenarios and fixes.)")


class Refused(Exception):
    pass


def api_key():
    envfile = os.environ.get("GSTACK_ANTHROPIC_ENV")
    if not envfile:
        raise Refused("GSTACK_ANTHROPIC_ENV is not set; point it at the vault's anthropic.env")
    path = Path(envfile).expanduser()
    if not path.exists():
        raise Refused(f"GSTACK_ANTHROPIC_ENV names {path}, which does not exist. No other credential is tried.")
    for line in path.read_text().splitlines():
        k, _, v = line.partition("=")
        if k.strip().removeprefix("export ").strip() == "ANTHROPIC_API_KEY" and v.strip():
            return v.strip().strip('"').strip("'")
    raise Refused(f"{path} sets no ANTHROPIC_API_KEY")


def post(body, timeout=600):
    req = urllib.request.Request(API_URL, data=json.dumps(body).encode(), headers={
        "x-api-key": api_key(), "anthropic-version": "2023-06-01",
        "anthropic-beta": BETA, "content-type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode())


def _section(lines, start):
    """Lines from `start` to the next heading at its own level or above."""
    level = len(lines[start]) - len(lines[start].lstrip("#"))
    end = next((i for i in range(start + 1, len(lines))
                if re.match(r"#{1,%d} " % level, lines[i])), len(lines))
    return lines[start:end]


def scope(text, items=None):
    """(scope_name, text_sent). Raises Refused for an item the doc doesn't contain."""
    lines = text.splitlines()
    if items:
        out = []
        for head in CONTEXT:
            i = next((n for n, l in enumerate(lines) if l.strip() == head), None)
            if i is not None:
                out += _section(lines, i)
        for item in items:
            i = next((n for n, l in enumerate(lines)
                      if re.match(r"### %s\b" % re.escape(item), l)), None)
            if i is None:
                raise Refused(f"the doc has no item {item}")
            out += _section(lines, i)
        name = "+".join(items)
    else:
        out, name = lines, "all"
    # ponytail: a status line is any line starting **Status:**; other per-item bookkeeping still counts
    return name, "\n".join(l for l in out if not l.lstrip().startswith("**Status:**")) + "\n"


def record_path(doc, name):
    return Path(doc).parent / "reviews" / "spec-review" / f"{name}.json"


def review(scope_text, post=post):
    """Returns (final_text, usage_iterations, advisor_calls). Resumes pause_turn until the turn ends."""
    tools = [{"type": "advisor_20260301", "name": "advisor", "model": ADVISOR,
              "max_uses": 3, "max_tokens": 4096}]
    messages = [{"role": "user", "content": f"{ADVISOR_STEER}\n\n<plan>\n{scope_text}</plan>"}]
    iterations, advisor_calls, text = [], 0, []
    for _ in range(MAX_RESUMES + 1):
        resp = post({"model": EXECUTOR, "max_tokens": 20000, "system": SYSTEM,
                     "thinking": {"type": "adaptive"}, "tools": tools, "messages": messages})
        content = resp.get("content") or []
        iterations += (resp.get("usage") or {}).get("iterations") or []
        advisor_calls += sum(1 for b in content if b.get("type") == "server_tool_use" and b.get("name") == "advisor")
        text += [b["text"] for b in content if b.get("type") == "text"]
        if resp.get("stop_reason") == "pause_turn":
            messages.append({"role": "assistant", "content": content})   # unchanged; the server resumes
            continue
        if resp.get("stop_reason") == "max_tokens":
            raise Refused("executor hit max_tokens before closing its findings block")
        return "\n".join(text), iterations, advisor_calls
    raise Refused(f"turn did not finish within {MAX_RESUMES} resumptions")


def findings(text):
    blocks = re.findall(r"```json\s*(\{.*?\})\s*```", text, re.S)
    if not blocks:
        raise Refused("executor returned no ```json findings block")
    f = json.loads(blocks[-1])
    return {k: f.get(k) or [] for k in ("contradictions", "ambiguities")}


def cmd_run(doc, items=None, post=post):
    doc = Path(doc)
    name, sent = scope(doc.read_text(), items)   # refuses an unknown item before any request
    text, iterations, calls = review(sent, post)
    f = findings(text)
    rec = {"schema": "spec-review/2", "doc": doc.name, "items": items or [],
           "scope_sha256": hashlib.sha256(sent.encode()).hexdigest(),
           "reviewed_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
           "executor": EXECUTOR, "advisor": ADVISOR, "advisor_calls": calls, "usage": iterations,
           "contradictions": f["contradictions"], "ambiguities": f["ambiguities"]}
    rp = record_path(doc, name)
    rp.parent.mkdir(parents=True, exist_ok=True)
    rp.write_text(json.dumps(rec, indent=2) + "\n")
    rp.with_suffix(".md").write_text(f"# Spec review: {doc.name} {name}\n\n_{rec['reviewed_at']} · "
                                     f"{EXECUTOR} with {ADVISOR} advisor ({calls} calls)_\n\n{text}\n")
    n = len(f["contradictions"])
    print(f"spec_review: {n} contradiction(s), {len(f['ambiguities'])} ambiguit(ies); "
          f"advisor called {calls}x; wrote {rp}")
    return 2 if n else 0


def check(doc, items=None):
    """(ok, reason). Read by cmd_check and by peer_review.py open."""
    doc = Path(doc)
    hint = f"run `spec_review.py run {doc}{' --items ' + ','.join(items) if items else ''}`"
    if not doc.exists():
        return False, f"spec_review_missing: {doc} does not exist"
    try:
        name, sent = scope(doc.read_text(), items)
    except Refused as e:
        return False, f"spec_review_missing: {e}"
    rp = record_path(doc, name)
    if not rp.exists():
        return False, f"spec_review_missing: no {rp.relative_to(doc.parent)} beside {doc.name}; {hint}"
    rec = json.loads(rp.read_text())
    if rec.get("scope_sha256") != hashlib.sha256(sent.encode()).hexdigest():
        return False, f"spec_review_stale: {rp.name} reviewed a different {name} in {doc.name}; {hint}"
    open_ = rec.get("contradictions") or []
    if open_:
        ids = ", ".join(c.get("id", "?") for c in open_)
        return False, f"spec_review_open: {len(open_)} open contradiction(s) ({ids}); amend {doc.name}, then re-run"
    return True, f"spec_review_ok: {rp.name} matches {name} in {doc.name}, no open contradictions"


def stub_post(body_json):
    """A transport that pauses once on an advisor call, then ends with `body_json` as findings.
    Shared with test_spec_review_gate.py so the tests and the selftest exercise one stub."""
    seen = []

    def stub(req):
        seen.append(req)
        if len(seen) == 1:
            return {"stop_reason": "pause_turn", "usage": {"iterations": [{"type": "message"}]},
                    "content": [{"type": "server_tool_use", "id": "s1", "name": "advisor", "input": {}}]}
        assert req["messages"][-1]["role"] == "assistant", "resume must resend the paused assistant turn"
        return {"stop_reason": "end_turn", "usage": {"iterations": [{"type": "advisor_message"}]},
                "content": [{"type": "text", "text": f"Looked.\n```json\n{json.dumps(body_json)}\n```"}]}
    stub.seen = seen
    return stub


def seed_clean(doc, items=None):
    """Test fixtures only: a clean record for `doc` as it is now, through the real writer and the stub
    transport, so a fixture opening an item review meets the gate rather than bypassing it."""
    import contextlib
    import io
    with contextlib.redirect_stdout(io.StringIO()):
        cmd_run(doc, items, post=stub_post({"contradictions": [], "ambiguities": []}))
    return record_path(doc, scope(Path(doc).read_text(), items)[0])


DEMO = """# Design

## Goal

Ship it.

## Constraints and settled decisions

- Offline first.

## Items and acceptance criteria

### R-001 — Rates

**Status:** planned.

1. Works offline.
2. Fetches live rates.

### R-002 — Other

1. Unrelated.

## Amendments log
"""


def selftest():
    import tempfile
    conflict = {"contradictions": [{"id": "C1", "requirements": ["R-001.1", "R-001.2"],
                                    "scenario": "offline", "smallest_change": "drop 2"}], "ambiguities": []}
    with tempfile.TemporaryDirectory() as d:
        doc = Path(d) / "DESIGN.md"
        doc.write_text(DEMO)
        # scope: context sections plus the item, no other item, no status line
        name, sent = scope(DEMO, ["R-001"])
        assert name == "R-001" and "Offline first" in sent and "Fetches live rates" in sent
        assert "R-002" not in sent and "Unrelated" not in sent and "**Status:**" not in sent and "Amendments" not in sent
        assert scope(DEMO)[0] == "all" and "R-002" in scope(DEMO)[1]
        # an unknown item refuses before any request
        s = stub_post(conflict)
        try:
            cmd_run(doc, ["R-009"], post=s)
            raise AssertionError("unknown item ran")
        except Refused as e:
            assert "no item R-009" in str(e) and not s.seen
        # missing, then a paused turn resumed, then open
        assert check(doc, ["R-001"])[1].startswith("spec_review_missing")
        s = stub_post(conflict)
        assert cmd_run(doc, ["R-001"], post=s) == 2 and len(s.seen) == 2
        rec = json.loads(record_path(doc, "R-001").read_text())
        assert rec["advisor_calls"] == 1 and rec["contradictions"][0]["id"] == "C1"
        ok, why = check(doc, ["R-001"])
        assert not ok and why.startswith("spec_review_open")
        # a hand-set resolved flag clears nothing
        rec["contradictions"][0]["resolved"] = True
        record_path(doc, "R-001").write_text(json.dumps(rec))
        assert check(doc, ["R-001"])[1].startswith("spec_review_open")
        # revise the doc, re-run clean; a status move leaves the record current
        doc.write_text(DEMO.replace("2. Fetches live rates.\n", ""))
        assert check(doc, ["R-001"])[1].startswith("spec_review_stale")
        assert cmd_run(doc, ["R-001"], post=stub_post({"contradictions": [], "ambiguities": []})) == 0
        assert check(doc, ["R-001"])[0]
        doc.write_text(doc.read_text().replace("**Status:** planned.", "**Status:** building."))
        assert check(doc, ["R-001"])[0], "a status line made the record stale"
        doc.write_text(doc.read_text().replace("- Offline first.", "- Online first."))
        assert check(doc, ["R-001"])[1].startswith("spec_review_stale"), "a constraint edit left it current"
        # the credential has one home
        saved = os.environ.pop("GSTACK_ANTHROPIC_ENV", None)
        try:
            for env, msg in ((None, "is not set"), (str(Path(d) / "nope.env"), "does not exist"),
                             (str(Path(d) / "empty.env"), "sets no ANTHROPIC_API_KEY")):
                (Path(d) / "empty.env").write_text("OTHER=1\n")
                if env:
                    os.environ["GSTACK_ANTHROPIC_ENV"] = env
                try:
                    api_key()
                    raise AssertionError(f"credential accepted: {env}")
                except Refused as e:
                    assert msg in str(e), (msg, e)
            (Path(d) / "ok.env").write_text('export ANTHROPIC_API_KEY="k1"\n')
            os.environ["GSTACK_ANTHROPIC_ENV"] = str(Path(d) / "ok.env")
            assert api_key() == "k1"
        finally:
            os.environ.pop("GSTACK_ANTHROPIC_ENV", None)
            if saved is not None:
                os.environ["GSTACK_ANTHROPIC_ENV"] = saved
    print("spec_review selftest: ok")


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--selftest", action="store_true")
    sub = p.add_subparsers(dest="cmd")
    for c in ("run", "check"):
        sp = sub.add_parser(c)
        sp.add_argument("doc")
        sp.add_argument("--items", type=lambda s: [x.strip() for x in s.split(",") if x.strip()])
    a = p.parse_args(argv)
    if a.selftest:
        return selftest()
    try:
        if a.cmd == "run":
            return cmd_run(a.doc, a.items)
        if a.cmd == "check":
            ok, reason = check(a.doc, a.items)
            print(reason)
            return 0 if ok else 2
    except Refused as e:
        print(f"refused: {e}", file=sys.stderr)
        return 1
    p.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main() or 0)
