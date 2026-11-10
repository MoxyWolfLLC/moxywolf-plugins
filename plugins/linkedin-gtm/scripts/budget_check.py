#!/usr/bin/env python3
"""Today's budget: the GTM API smart limits read against the plan's own, lower targets.

The platform ceiling (daily_limit) is the most the warmup allows. The plan target is what we
choose to spend, and it is never above the ceiling. For each bucket this reports what's spent,
what's left under each, and whether the bucket is red (held, LinkedIn quota hit, not active, or
risk_level above none). Red on any outward bucket means that action type stops today.

Input is either a saved search_linkedin_account_smart_limits result (--limits FILE, raw MCP
output or the structured result) or a live read (--live, through gtm_mcp.py, read-only).

  budget_check.py --limits smart_limits.json --config linkedin-gtm.json [--ledger L.json] [--json]
  budget_check.py --live --config linkedin-gtm.json [--proxy-auth] [--json]

Exit codes: 0 all green, 3 a red outward bucket or an over-budget batch, 2 bad input.
"""
import argparse
import datetime as dt
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

# Buckets an outward action spends. A red one here stops that action type for the day.
OUTWARD = {"send_connection_requests", "send_messages", "send_inmails", "comment_posts",
           "react_posts", "endorse_skills", "visit_profiles", "posting", "networking_general",
           "messaging_general", "edit_profile"}

# Plan section 5, weeks 1-2 and week 3+. The high end of each range is the daily cap we plan to.
DEFAULT_TARGETS = {
    "send_connection_requests": {"weeks_1_2": 5, "week_3_plus": 20},
    "send_messages": {"weeks_1_2": 10, "week_3_plus": 20},
    "comment_posts": {"weeks_1_2": 5, "week_3_plus": 5},
    "react_posts": {"weeks_1_2": 5, "week_3_plus": 15},
    "visit_profiles": {"weeks_1_2": 8, "week_3_plus": 20},
    "endorse_skills": {"weeks_1_2": 2, "week_3_plus": 3},
    "posting": {"weeks_1_2": 1, "week_3_plus": 1},  # 2-3 posts a week, never 2 in a day
    "enrichment": {"weeks_1_2": 12, "week_3_plus": None},  # None = follow the platform ramp
    "scraping": {"weeks_1_2": 15, "week_3_plus": None},
}


class BadInput(Exception):
    pass


def extract_rows(doc):
    """Accept the raw JSON-RPC response, the structured result, or a bare list of rows."""
    if isinstance(doc, dict) and "result" in doc and isinstance(doc["result"], dict):
        res = doc["result"]
        doc = res.get("structuredContent") or json.loads(res["content"][0]["text"])
    if isinstance(doc, dict):
        doc = doc.get("items", doc.get("rows", []))
    if not isinstance(doc, list):
        raise BadInput("no smart-limit rows found")
    rows = [r.get("item", r) if isinstance(r, dict) else r for r in doc]
    if not rows or "limit_type" not in rows[0]:
        raise BadInput("rows carry no limit_type; is this a search_linkedin_account_smart_limits result?")
    return rows


def _later(ts, now):
    if not ts:
        return False
    t = dt.datetime.fromisoformat(str(ts).replace("Z", "+00:00"))
    return t > now


def phase_for(config, today):
    start = config.get("ramp_start_date")
    if not start:
        return "weeks_1_2"
    days = (today - dt.date.fromisoformat(start)).days
    return "weeks_1_2" if days < 14 else "week_3_plus"


def compute(rows, config=None, now=None, today=None):
    config = config or {}
    now = now or dt.datetime.now(dt.timezone.utc)
    today = today or now.date()
    phase = phase_for(config, today)
    targets = dict(DEFAULT_TARGETS)
    targets.update(config.get("plan_targets") or {})
    out = {}
    for r in rows:
        b = r["limit_type"]
        ceiling = int(r.get("daily_limit") or 0)
        done = int(r.get("done_today_count") or 0)
        tgt = (targets.get(b) or {}).get(phase)
        plan_cap = ceiling if tgt is None else min(int(tgt), ceiling)
        flags = []
        if r.get("status") not in (None, "active"):
            flags.append(f"status {r.get('status')}")
        if _later(r.get("hold_till"), now):
            flags.append(f"held until {r['hold_till']}")
        if _later(r.get("linkedin_quota_hit_till"), now):
            flags.append(f"LinkedIn quota hit until {r['linkedin_quota_hit_till']}")
        if r.get("risk_level") not in (None, "none"):
            flags.append(f"risk_level {r['risk_level']}")
        out[b] = {
            "ceiling": ceiling,
            "done": done,
            "ceiling_left": max(0, ceiling - done),
            "plan_cap": plan_cap,
            "plan_left": 0 if flags else max(0, plan_cap - done),
            "delay_seconds": r.get("delay_in_seconds"),
            "red": bool(flags),
            "flags": flags,
            "outward": b in OUTWARD,
        }
    red = sorted(b for b, v in out.items() if v["red"] and v["outward"])
    return {"phase": phase, "buckets": out, "red_outward": red, "status": "red" if red else "green"}


def check_batch(budget, ledger):
    """Items still to go out per bucket against plan_left. Returns the over-budget buckets."""
    pending = {}
    for it in ledger["items"]:
        if it["status"] in ("drafted", "approved", "edited"):
            pending[it["bucket"]] = pending.get(it["bucket"], 0) + 1
    over = {}
    for b, n in pending.items():
        left = budget["buckets"].get(b, {}).get("plan_left", 0)
        if n > left:
            over[b] = {"queued": n, "plan_left": left, "cut": n - left}
    return pending, over


def render_text(budget, pending=None, over=None):
    lines = [f"Budget ({budget['phase'].replace('_', ' ')}): {budget['status'].upper()}",
             "| Bucket | Spent | Plan cap | Plan left | Ceiling | Flags |", "|---|---|---|---|---|---|"]
    for b, v in sorted(budget["buckets"].items()):
        lines.append(f"| {b} | {v['done']} | {v['plan_cap']} | {v['plan_left']} | {v['ceiling']} | "
                     f"{'; '.join(v['flags']) or ''} |")
    if pending is not None:
        lines.append("")
        lines.append("Queued in today's batch: " + (", ".join(f"{b} {n}" for b, n in sorted(pending.items())) or "nothing"))
    if over:
        lines.append("OVER BUDGET, cut before approval: " +
                     ", ".join(f"{b} by {v['cut']}" for b, v in sorted(over.items())))
    if budget["red_outward"]:
        lines.append("STOP these action types today: " + ", ".join(budget["red_outward"]))
    return "\n".join(lines)


def main(argv=None, transport=None):
    ap = argparse.ArgumentParser(description="linkedin-gtm budget check")
    src = ap.add_mutually_exclusive_group(required=True)
    src.add_argument("--limits"); src.add_argument("--live", action="store_true")
    ap.add_argument("--config"); ap.add_argument("--ledger"); ap.add_argument("--json", action="store_true")
    ap.add_argument("--proxy-auth", action="store_true")
    a = ap.parse_args(argv)
    config = json.loads(Path(a.config).read_text(encoding="utf-8")) if a.config else {}
    try:
        if a.live:
            import gtm_mcp
            sid = config.get("account_sid")
            if not sid:
                raise BadInput("--live needs account_sid in the config")
            client = gtm_mcp.GtmClient(proxy_auth=a.proxy_auth or None, transport=transport)
            r = client.read("search_linkedin_account_smart_limits",
                            {"filter": {"linkedin_account_sid": {"eq": sid}}, "page_size": 50})
            if not r.ok:
                raise BadInput(f"smart-limit read failed: {r.error}")
            rows = extract_rows(r.data)
        else:
            rows = extract_rows(json.loads(Path(a.limits).read_text(encoding="utf-8")))
    except (BadInput, ValueError, KeyError) as e:
        print(f"bad input: {e}", file=sys.stderr)
        return 2
    budget = compute(rows, config)
    pending = over = None
    if a.ledger:
        import batch_ledger
        pending, over = check_batch(budget, batch_ledger.load(a.ledger))
    if a.json:
        print(json.dumps(dict(budget, queued=pending, over=over), indent=2))
    else:
        print(render_text(budget, pending, over))
    return 3 if budget["red_outward"] or over else 0


if __name__ == "__main__":
    sys.exit(main())
