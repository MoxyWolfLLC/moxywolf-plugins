#!/usr/bin/env python3
"""GO-004.2: the runner counts what a goal run spends and stops near the cap.

  goal_spend.py status <ledger> <GOAL.md>   exit 0 only when the run may take its next step; any
                                            other exit stops it (80% of a budget, the cap or Max
                                            calls, a ledger or brief it can't read, or a crash,
                                            which Python reports as 1), and prints the totals

During a goal run the runner names a ledger file in GSTACK_GOAL_LEDGER and the dispatchers append
one JSON line per model call: the provider, the cost the provider reported for that call (null
when it reported none) and the transport. A subscription CLI, and a metered call that reports no
cost, count against Max calls. Outside a goal run GSTACK_GOAL_LEDGER is unset and record() does
nothing. The team key's own credit limit at the provider stays the backstop outside the agent.
"""
import json
import os
import sys
from decimal import Decimal, InvalidOperation
from pathlib import Path

LEDGER_ENV = "GSTACK_GOAL_LEDGER"
STOP_AT = Decimal("0.8")


class LedgerError(BaseException):
    """Not an Exception, so a caller's `except Exception` can't swallow it: a goal run that can't
    count what it spent must not keep spending."""


def record(provider, cost, transport):
    """Append one call to the run's ledger; a write that fails raises LedgerError."""
    path = os.environ.get(LEDGER_ENV)
    if not path:
        return
    line = {"provider": str(provider).lower(), "cost": None if cost is None else str(cost), "transport": transport}
    try:
        with open(path, "a") as f:
            f.write(json.dumps(line) + "\n")
    except OSError as e:
        raise LedgerError(f"cannot record a model call in {path}: {e}")


def limits(brief_text):
    """({provider: budget}, cap, max_calls) from a goal brief that goal_brief.py check accepted."""
    # imported here, not at the top: peer_review imports this module for record(), and goal_brief
    # needs the repository's .github, which an installed plugin doesn't have
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from goal_brief import INT, MONEY, bullet_lines, sections
    b, errors = sections(brief_text), []
    budgets = {}
    for line in bullet_lines("Provider budgets", b.get("Provider budgets", ""), errors):
        name, _, amount = line.partition(":")
        budgets[name.strip().lower()] = Decimal(MONEY.match(amount.strip()).group(1))
    cap = Decimal(MONEY.match(b["Spend cap"].strip()).group(1))
    max_calls = int(INT.match(b["Max calls"].strip()).group(0))
    return budgets, cap, max_calls


def status(ledger, brief_text):
    """(stop, reasons, totals). Fails closed: a missing or malformed ledger is a stop."""
    try:
        budgets, cap, max_calls = limits(brief_text)
    except (KeyError, AttributeError, InvalidOperation) as e:
        return True, [f"the brief's Spend cap, Provider budgets or Max calls can't be read ({e!r})"], {}
    try:
        entries = [json.loads(line) for line in Path(ledger).read_text().splitlines() if line.strip()]
        spent, calls = {}, 0
        for e in entries:
            if e["cost"] is None or e["transport"] == "subscription":
                calls += 1
            if e["cost"] is not None:
                c = Decimal(e["cost"])
                if not c.is_finite() or c < 0:
                    raise ValueError(f"cost {e['cost']}")
                spent[e["provider"]] = spent.get(e["provider"], Decimal(0)) + c
    except (OSError, ValueError, KeyError, TypeError, InvalidOperation) as e:
        return True, [f"the spend ledger {ledger} can't be read ({e}); a run that can't count stops"], {}
    reasons = []
    for p, amount in sorted(spent.items()):
        if p not in budgets:
            reasons.append(f"{p} was charged ${amount} and has no Provider budget")
        elif amount >= STOP_AT * budgets[p]:
            reasons.append(f"{p} spent ${amount} of its ${budgets[p]} budget (stop at 80%)")
    total = sum(spent.values(), Decimal(0))
    if total >= STOP_AT * cap:
        reasons.append(f"spent ${total} of the ${cap} Spend cap (stop at 80%)")
    if calls >= STOP_AT * max_calls:
        reasons.append(f"{calls} of {max_calls} Max calls used (stop at 80%)")
    return bool(reasons), reasons, {"entries": len(entries), "spent": {k: str(v) for k, v in spent.items()},
                                    "total": str(total), "calls": calls}


def main(argv):
    if argv[:1] == ["status"] and len(argv) == 3:
        try:
            brief = Path(argv[2]).read_text()
        except OSError as e:
            print(f"STOP: the brief can't be read ({e})")
            return 1
        stop, reasons, totals = status(argv[1], brief)
        print(f"examined {totals.get('entries', 0)} ledger entries: {json.dumps(totals)}")
        for r in reasons:
            print("STOP:", r)
        return 1 if stop else 0
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
