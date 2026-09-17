#!/usr/bin/env python3
"""XE-003: the cheapest surface that answers the question.

The audited session made 1,039 browser calls against 51 API calls, with connectors configured for
several of the services it drove through the browser. The bias is not that sessions prefer browsers
on principle -- it is that with several hundred tools available, "is there a connector for this?" is
answered by eyeballing, and eyeballing favours the tool already in hand.

So this answers it by looking. Rungs, cheapest first:

    connector -> cli -> rest -> browser

ponytail: substring match on tool names, no registry. A connector's tools are named
mcp__<Service>__<verb>, which is enough to find them; the cost of a miss is one wasted lookup, not a
wrong action. REST is deliberately NOT detected -- an HTTP API leaves no trace in a tool list, so
reporting "no rest" would be a claim this cannot support. It reports what it can see and says so.
"""
import json
import shutil
import sys

RUNGS = ["connector", "cli", "rest", "browser"]
BROWSER_PREFIXES = ("mcp__claude-in-chrome__", "mcp__remote-devices__Claude_Browser__",
                    "mcp__remote-devices__playwright__", "mcp__remote-devices__Control_Chrome__")


def classify(tool_name):
    """Which rung a single available tool sits on."""
    if tool_name.startswith(BROWSER_PREFIXES):
        return "browser"
    return "connector" if tool_name.startswith("mcp__") else "cli"


def survey(service, tool_names, clis=()):
    """What is available for `service`, cheapest rung first.

    Returns {"cheapest": rung|None, "by_rung": {...}, "undetectable": ["rest"]}. `cheapest` is the
    rung a session is expected to take; taking a lower one is the thing that must be said out loud.
    """
    s = service.lower().replace(" ", "").replace("-", "").replace("_", "")
    by_rung = {r: [] for r in RUNGS}
    for t in tool_names:
        rung = classify(t)
        if rung == "browser":
            by_rung["browser"].append(t)          # a browser serves any service, so never name-matched
        elif s in t.lower().replace("-", "").replace("_", ""):
            by_rung[rung].append(t)
    for c in clis:
        if shutil.which(c):
            by_rung["cli"].append(c)
    cheapest = next((r for r in RUNGS if by_rung[r]), None)
    return {"service": service, "cheapest": cheapest, "by_rung": by_rung,
            "undetectable": ["rest"],
            "note": "rest is not detectable from a tool list; check the service's API before "
                    "settling for browser"}


def report(service, rung_taken, tool_names, clis=()):
    """XE-003.2: a session that took a lower rung than the cheapest available says so.

    Returns a one-line string to put in the session's own output, or None when the cheapest rung
    was taken and there is nothing to disclose.
    """
    s = survey(service, tool_names, clis)
    cheap = s["cheapest"]
    if cheap is None or rung_taken == cheap:
        return None
    if RUNGS.index(rung_taken) <= RUNGS.index(cheap):
        return None
    names = ", ".join(sorted(s["by_rung"][cheap])[:3])
    return (f"rung: took {rung_taken} for {service} while {cheap} was available ({names}). "
            f"State why, or take the {cheap} rung.")


def main(argv):
    if len(argv) < 2:
        print(__doc__.strip().splitlines()[0]); print("usage: tool_rung.py <service> [rung_taken] < tool_names"); return 2
    names = [l.strip() for l in sys.stdin.read().splitlines() if l.strip()]
    if len(argv) >= 3:
        line = report(argv[1], argv[2], names)
        print(line or f"rung: took {argv[2]} for {argv[1]}; nothing cheaper was available")
        return 1 if line else 0
    print(json.dumps(survey(argv[1], names), indent=2)); return 0


def _selftest():
    tools = ["mcp__Github__create_pull_request", "mcp__Github__get_commit",
             "mcp__Slack__slack_send_message", "mcp__claude-in-chrome__navigate",
             "mcp__remote-devices__Claude_Browser__read_page"]

    s = survey("Github", tools)
    assert s["cheapest"] == "connector", s
    assert len(s["by_rung"]["connector"]) == 2 and s["by_rung"]["browser"], s

    # a browser is not matched by name -- it serves every service, which is exactly why it gets reached for
    assert survey("Notion", tools)["cheapest"] == "browser", survey("Notion", tools)

    # the disclosure XE-003.2 requires
    line = report("Github", "browser", tools)
    assert line and "took browser" in line and "connector was available" in line, line
    assert report("Github", "connector", tools) is None
    assert report("Notion", "browser", tools) is None      # nothing cheaper existed; nothing to disclose

    # a cli counts, and only when it is really on PATH
    assert "git" in survey("git", [], clis=["git"])["by_rung"]["cli"]
    assert survey("x", [], clis=["definitely-not-a-real-binary-xyz"])["cheapest"] is None

    # rest is never claimed either way
    assert survey("Github", tools)["undetectable"] == ["rest"]
    print("tool_rung selftest ok")


if __name__ == "__main__":
    sys.exit(_selftest() if "--selftest" in sys.argv else main(sys.argv))
