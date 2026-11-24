#!/usr/bin/env python3
"""XE-049.16: a fresh model reads one builder's brief and asks two questions of it.

  brief_check.py <brief file>        print the entries as JSON (exit 0; 1 when the model's reply won't parse)

The brief is the item's text, its acceptance criteria and every command, script and tool it names. The model gets
nothing else, and answers: is any instruction ambiguous, and do you know how to use each command and tool named?
Each entry quotes the words it is about. Settling an entry is the coordinator's work (goal_run.py settle), never
this script's.

The call goes to Claude through spec_review.py's plumbing (GSTACK_ANTHROPIC_ENV). It is recorded in the goal's
spend ledger (GSTACK_GOAL_LEDGER) with no dollar cost, so it counts against the brief's Max calls. Tests and dry
runs set GSTACK_BRIEF_CHECK_REPLY to a file holding the model's reply text, and no network call is made.
"""
import json
import os
import sys
from pathlib import Path

import goal_spend

MODEL = os.environ.get("GSTACK_BRIEF_CHECK_MODEL", "claude-sonnet-5-5")
KINDS = ("ambiguous", "unknown_tool")
PROMPT = """You are about to be handed the brief below as your only instructions for a build. Before you start,
answer two questions about it, and nothing else:
1. Is any instruction ambiguous: could two careful builders read it and do different things?
2. Do you know how to use each command, script and tool it names, from the brief alone?

Reply with only a JSON array. One object per problem: {"kind": "ambiguous" or "unknown_tool", "quote": "<the exact
words from the brief, copied verbatim>", "question": "<what you would need answered>"}. An empty array means the
brief is clear. Don't invent problems to fill the list.

<brief>
%s
</brief>"""


class Refused(Exception):
    pass


def _claude(prompt):
    stub = os.environ.get("GSTACK_BRIEF_CHECK_REPLY")
    if stub:
        return Path(stub).read_text()
    import spec_review
    try:
        resp = spec_review.post({"model": MODEL, "max_tokens": 4000, "messages": [{"role": "user", "content": prompt}]})
    except spec_review.Refused as e:
        raise Refused(str(e))
    return "".join(b.get("text", "") for b in resp.get("content", []) if b.get("type") == "text")


def parse(reply, brief):
    """The entries, numbered B1, B2, ... A reply that isn't a JSON array of well-formed entries is refused, not
    read as 'no problems': a check that saw nothing must not pass a builder."""
    text = reply.strip()
    if text.startswith("```"):
        text = text.strip("`").split("\n", 1)[-1]
    start, stop = text.find("["), text.rfind("]")
    try:
        raw = json.loads(text[start:stop + 1]) if start >= 0 and stop > start else None
    except json.JSONDecodeError:
        raw = None
    if not isinstance(raw, list):
        raise Refused(f"the model's reply isn't a JSON array: {reply[:200]!r}")
    out = []
    for e in raw:
        if not (isinstance(e, dict) and e.get("kind") in KINDS and isinstance(e.get("quote"), str) and e["quote"].strip()
                and isinstance(e.get("question"), str) and e["question"].strip()):
            raise Refused(f"malformed entry: {e!r}")
        out.append({"id": f"B{len(out) + 1}", "kind": e["kind"], "quote": e["quote"], "question": e["question"],
                    # a quote the brief doesn't hold is kept, flagged, so the coordinator can see the model misread
                    "quote_found": e["quote"] in brief, "settlement": "open", "how": None})
    return out


def check(brief, call=None):
    reply = (call or _claude)(PROMPT % brief)
    goal_spend.record("anthropic", None, "anthropic")      # counts against Max calls; no measured dollar cost
    return parse(reply, brief)


def main(argv):
    if len(argv) != 1:
        print(__doc__, file=sys.stderr)
        return 2
    try:
        print(json.dumps(check(Path(argv[0]).read_text()), indent=1))
        return 0
    except Refused as e:
        print(f"REFUSED: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
