#!/usr/bin/env python3
"""The daily approval batch: one JSON ledger per day that holds every outward item.

Every outward LinkedIn action the plugin takes starts life as an item in this ledger. An item is
drafted, then Dorian (the Release Owner) approves, edits or strikes it, and only then can
`gtm_mcp.py execute` send it. The ledger binds the approval to the exact arguments with a hash, so
an item edited after approval can't go out on the old signature.

Statuses: drafted -> approved | edited | struck -> executed | failed | uncertain | skipped.
`edited` means approved with Dorian's changes; it executes like `approved`.

Stdlib only. Usage (run with --help on any subcommand for its flags):

  batch_ledger.py new      --ledger-dir DIR --date YYYY-MM-DD --config CFG
  batch_ledger.py add      --ledger FILE --kind comment --lane C --args '{...}' --reason "..." [--config CFG]
  batch_ledger.py render   --ledger FILE              # the approval message, markdown
  batch_ledger.py present  --ledger FILE              # stamps presented_at (the clock for response time)
  batch_ledger.py decide   --ledger FILE --items 3,4 --decision approve --approver "Dorian Cougias" --initials DC
  batch_ledger.py queue    --ledger FILE [--block engagement|publish|network|inbox]
  batch_ledger.py stats    --ledger-dir DIR [--days 30]
  batch_ledger.py gate-log --ledger FILE [--gate-log-dir DIR]
  batch_ledger.py crm-export --ledger FILE
"""
import argparse
import datetime as dt
import hashlib
import json
import os
import re
import statistics
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
SCHEMA = "linkedin-gtm/batch-ledger@1"
POLICY_PATH = HERE / "tool_policy.json"

DRAFTED, APPROVED, EDITED, STRUCK = "drafted", "approved", "edited", "struck"
EXECUTED, FAILED, UNCERTAIN, SKIPPED = "executed", "failed", "uncertain", "skipped"
DROPPED = "dropped"  # cut before presentation (over budget); never shown, never decided
EXECUTABLE = (APPROVED, EDITED)
DECISIONS = {"approve": APPROVED, "edit": EDITED, "strike": STRUCK}
GATE_DECISION = {APPROVED: "signed", EDITED: "edited", STRUCK: "stopped"}

# The order the day runs in (plan section 3). Reactions and comments warm up first, then inbound,
# then the publish window, then network outreach.
BLOCKS = {
    "engagement": ["reaction", "comment", "repost", "accept", "ignore", "reply", "visit", "endorse"],
    "publish": ["post"],
    "network": ["connect", "dm", "withdraw"],
    "inbox": ["mark_unread"],
}
KIND_ORDER = [k for block in ("engagement", "publish", "network", "inbox") for k in BLOCKS[block]]

# Outreach kinds Lane A may not use while the partner campaign is held (plan section 2).
OUTREACH_KINDS = {"connect", "dm"}
VAGUE_APPROVERS = {"", "me", "i", "user", "the user", "owner", "the owner", "team", "the team",
                   "approved", "ok", "yes", "admin", "someone", "amos", "claude", "agent"}

EM_DASH = "\u2014"
# react_linkedin_post's enum. "interested" exists but only lands on event posts, so it isn't offered.
REACTIONS = {"like", "celebrate", "support", "love", "insightful", "funny"}
LIMITS = {  # hard caps; a draft over these can't be approved
    "connect": 200,    # plan: notes under 200 chars (LinkedIn allows 300 on Premium)
    "comment": 1200,   # linkedin-thought-leadership hard limit (LinkedIn truncates past it)
    "dm": 8000,        # send_linkedin_message body cap
    "reply": 8000,
    "post": 2900,      # 4d-blog-engine house cap under LinkedIn's 3,000
    "repost": 2900,
}
SOFT = {  # craft ranges from references/voice-and-craft.md; outside them is a warning
    "comment": (200, 900),
    "dm": (0, 600),
    "post": (1300, 2500),  # 4d-blog-engine blog-social sweet spot
}
URL_RE = re.compile(r"https?://|www\.|lnkd\.in/", re.I)
CAL_RE = re.compile(r"calendly\.com|cal\.com/|savvycal|hubspot\.com/meetings|/book(ing)?/", re.I)


class LedgerError(Exception):
    """A request the ledger refuses. The message says why, in words a person can act on."""


def now_utc():
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0)


def iso(t):
    return t.astimezone(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def parse_iso(s):
    if not s:
        return None
    return dt.datetime.fromisoformat(s.replace("Z", "+00:00"))


def load_policy():
    return json.loads(POLICY_PATH.read_text(encoding="utf-8"))


def args_hash(args):
    canon = json.dumps({k: v for k, v in args.items() if k not in ("commit_token", "_meta")},
                       sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(canon.encode("utf-8")).hexdigest()


def load(path):
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if data.get("schema") != SCHEMA:
        raise LedgerError(f"{path} is not a linkedin-gtm batch ledger (schema {data.get('schema')!r})")
    return data


def save(ledger, path):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), prefix=".ledger-", suffix=".json")
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        json.dump(ledger, f, indent=2, ensure_ascii=False)
        f.write("\n")
    os.replace(tmp, path)


def new_ledger(date, account_sid, release_owner, now=None):
    if not re.match(r"^\d{4}-\d{2}-\d{2}$", date or ""):
        raise LedgerError("date must be YYYY-MM-DD")
    if not account_sid or not account_sid.startswith("ln_ac_"):
        raise LedgerError("account_sid must be a GTM API LinkedIn account sid (ln_ac_...)")
    check_approver_name(release_owner)
    return {
        "schema": SCHEMA,
        "date": date,
        "account_sid": account_sid,
        "release_owner": release_owner,
        "created_at": iso(now or now_utc()),
        "presented_at": None,
        "stops": {"all": None, "buckets": {}},
        "items": [],
    }


def check_approver_name(name):
    if (name or "").strip().lower() in VAGUE_APPROVERS or len((name or "").split()) < 2:
        raise LedgerError(f"approver {name!r} is not a named human; give a first and last name")


def lint_text(kind, text):
    """(errors, warnings). Errors block approval; warnings ride along in the batch for Dorian."""
    errors, warnings = [], []
    if text is None:
        return errors, warnings
    if EM_DASH in text:
        errors.append("contains an em dash; Dorian's voice uses none")
    cap = LIMITS.get(kind)
    if cap and len(text) > cap:
        errors.append(f"{len(text)} chars, over the {cap}-char cap for {kind}")
    lo_hi = SOFT.get(kind)
    if lo_hi and not (lo_hi[0] <= len(text) <= lo_hi[1]):
        warnings.append(f"{len(text)} chars, outside the {lo_hi[0]}-{lo_hi[1]} craft range for {kind}")
    if kind in ("comment", "connect") and "#" in text:
        warnings.append("hashtag in a comment or note")
    if kind in ("post",) and URL_RE.search(text):
        warnings.append("link in the post body; links go in the first comment")
    if kind in ("connect",) and URL_RE.search(text):
        errors.append("link in a connection note")
    if kind == "dm" and CAL_RE.search(text):
        warnings.append("calendar link in a DM; first DMs carry no booking link")
    if "{{" in text or "}}" in text:
        errors.append("unfilled {{placeholder}} left in the text")
    return errors, warnings


def _load_suppression(config):
    path = (config or {}).get("suppression_file")
    if not path:
        return set()
    p = Path(os.path.expanduser(path))
    if not p.exists():
        return set()
    body = p.read_text(encoding="utf-8")
    if body.lstrip().startswith(("[", "{")):  # JSON export from the CRM
        raw = json.loads(body)
        entries = raw.get("suppressed", raw) if isinstance(raw, dict) else raw
    else:  # one public identifier or profile URL per line, # comments allowed
        entries = [ln.split("#", 1)[0].strip() for ln in body.splitlines()]
    out = set()
    for e in entries:
        ident = e.get("identifier") if isinstance(e, dict) else e
        if ident:
            out.add(normalize_identifier(ident))
    return out


def normalize_identifier(ident):
    s = str(ident).strip().lower().rstrip("/")
    m = re.search(r"linkedin\.com/in/([^/?#]+)", s)
    return m.group(1) if m else s


def check_page_choice(args, target, config, ledger):
    """A post AS a company page needs a page from config long_form.pages that the Release Owner
    named for this piece (target.page and target.page_chosen_by). Nothing defaults to a page."""
    pages = (config or {}).get("long_form", {}).get("pages", {})
    org = str(args.get("author_organization_id"))
    by_id = {str(v.get("organization_id")): name for name, v in pages.items()}
    if org not in by_id:
        raise LedgerError(f"author_organization_id {org} is not one of the long-form pages in config "
                          f"({', '.join(sorted(pages)) or 'none set'})")
    page = (target or {}).get("page")
    if page != by_id[org]:
        raise LedgerError(f"target.page must name the page this post goes to ({by_id[org]}), "
                          "as Dorian chose it for this piece")
    chooser = ((target or {}).get("page_chosen_by") or "").strip().lower()
    if chooser != ledger["release_owner"].strip().lower():
        raise LedgerError(f"the page is chosen by the Release Owner ({ledger['release_owner']}) for each "
                          "piece; record it in target.page_chosen_by")


def add_item(ledger, kind, args, lane, reason, target=None, sources=None, sequence=None,
             config=None, policy=None, now=None):
    policy = policy or load_policy()
    spec = policy["gated_kinds"].get(kind)
    if not spec:
        raise LedgerError(f"unknown kind {kind!r}; one of {sorted(policy['gated_kinds'])}")
    if lane not in ("A", "B", "C", "D", "OWN"):
        raise LedgerError("lane must be A, B, C, D or OWN (Dorian's own posts and replies)")
    if not (reason or "").strip():
        raise LedgerError("every item carries a one-line reason")
    config = config or {}
    lane_a_mode = config.get("lanes", {}).get("A", {}).get("mode", "engagement-only")
    if lane == "A" and kind in OUTREACH_KINDS and lane_a_mode != "full-outreach":
        raise LedgerError("Lane A is on hold (engagement-only): no connection requests or DMs to "
                          "partners until Dorian releases the campaign in config lanes.A.mode")
    args = dict(args or {})
    unknown = sorted(set(args) - set(spec["params"]))
    if unknown:
        raise LedgerError(f"{spec['tool']} takes no {unknown}; its params are {spec['params']}")
    if spec["account_arg"] and not args.get(spec["account_arg"]):
        args[spec["account_arg"]] = ledger["account_sid"]
    if spec["account_arg"] and args[spec["account_arg"]] != ledger["account_sid"]:
        raise LedgerError("an item may only act as the ledger's own account")
    target = dict(target or {})
    ident = target.get("identifier") or (args.get(spec["target_arg"]) if spec["target_arg"] else None)
    if ident and normalize_identifier(ident) in _load_suppression(config):
        raise LedgerError(f"{ident} is on the suppression list; nothing goes to them")
    if kind == "reaction" and args.get("reaction_type") not in REACTIONS:
        raise LedgerError(f"reaction_type must be one of {sorted(REACTIONS)}")
    if kind == "post" and args.get("author_organization_id"):
        check_page_choice(args, target, config, ledger)
    text = args.get(spec["text_arg"]) if spec["text_arg"] else None
    if kind in ("comment", "dm", "reply", "post") and not (text or "").strip():
        raise LedgerError(f"a {kind} needs its text in args.{spec['text_arg']}")
    errors, warnings = lint_text(kind, text)
    if errors:
        raise LedgerError(f"draft refused: {'; '.join(errors)}")
    n = len(ledger["items"]) + 1
    item_id = f"{ledger['date'].replace('-', '')}-{n:03d}"
    if spec["client_reference"] and not args.get("client_reference"):
        # Sending-once key: a repeat under this key is answered, never sent twice.
        args["client_reference"] = f"lgtm-{item_id}"
    item = {
        "id": item_id,
        "kind": kind,
        "lane": lane,
        "tool": spec["tool"],
        "bucket": spec["bucket"],
        "target": target,
        "args": args,
        "reason": reason.strip(),
        "sources": list(sources or []),
        "sequence": sequence,
        "warnings": warnings,
        "status": DRAFTED,
        "created_at": iso(now or now_utc()),
        "decision": None,
        "approved_args_hash": None,
        "execution": None,
        "gate_log": None,
    }
    ledger["items"].append(item)
    return item


def find(ledger, item_id):
    for it in ledger["items"]:
        if it["id"] == item_id:
            return it
    raise LedgerError(f"no item {item_id} in the {ledger['date']} batch")


def drop(ledger, item_ids, why):
    """Take drafted items out before the batch is shown (budget cuts). Ids stay stable."""
    if ledger.get("presented_at"):
        raise LedgerError("the batch was already presented; Dorian strikes items now, nobody drops them")
    out = []
    for item_id in item_ids:
        item = find(ledger, item_id)
        if item["status"] != DRAFTED:
            raise LedgerError(f"{item_id} is {item['status']}; only drafted items can be dropped")
        item["status"] = DROPPED
        item["dropped_because"] = why
        out.append(item)
    return out


def present(ledger, now=None):
    ledger["presented_at"] = iso(now or now_utc())
    return ledger["presented_at"]


def decide(ledger, item_ids, decision, approver, initials, now=None, new_text=None, note=None,
           policy=None):
    """Record the Release Owner's decision on each item. Refuses a vague or substitute approver."""
    if decision not in DECISIONS:
        raise LedgerError(f"decision must be one of {sorted(DECISIONS)}")
    check_approver_name(approver)
    if approver.strip().lower() != ledger["release_owner"].strip().lower():
        raise LedgerError(f"only the Release Owner ({ledger['release_owner']}) signs this batch, "
                          f"not {approver!r}")
    if not re.match(r"^[A-Za-z]{2,4}$", initials or ""):
        raise LedgerError("initials are 2-4 letters")
    if not ledger.get("presented_at"):
        raise LedgerError("present the batch before recording decisions (batch_ledger.py present)")
    if decision == "edit" and new_text is None:
        raise LedgerError("an edit carries the new text (--text)")
    policy = policy or load_policy()
    now = now or now_utc()
    presented = parse_iso(ledger["presented_at"])
    out = []
    for item_id in item_ids:
        item = find(ledger, item_id)
        if item["status"] not in (DRAFTED, APPROVED, EDITED, STRUCK):
            raise LedgerError(f"{item_id} is already {item['status']}; a decision can't change it")
        rec = {
            "decision": decision,
            "approver": approver.strip(),
            "initials": initials.upper(),
            "requested_at": ledger["presented_at"],
            "decided_at": iso(now),
            "response_seconds": max(0, int((now - presented).total_seconds())),
            "note": note,
        }
        if decision == "edit":
            spec = policy["gated_kinds"][item["kind"]]
            if not spec["text_arg"]:
                raise LedgerError(f"a {item['kind']} has no text to edit; strike it or approve it")
            errors, warnings = lint_text(item["kind"], new_text)
            if errors:
                raise LedgerError(f"edited text refused: {'; '.join(errors)}")
            rec["original_text"] = item["args"].get(spec["text_arg"])
            item["args"][spec["text_arg"]] = new_text
            item["warnings"] = warnings
        item["decision"] = rec
        item["status"] = DECISIONS[decision]
        item["approved_args_hash"] = args_hash(item["args"]) if item["status"] in EXECUTABLE else None
        item["gate_log"] = {"status": "pending"}
        out.append(item)
    return out


def stop(ledger, reason, bucket=None):
    if bucket:
        ledger["stops"]["buckets"][bucket] = reason
    else:
        ledger["stops"]["all"] = reason


def stopped_reason(ledger, bucket):
    return ledger["stops"].get("all") or ledger["stops"]["buckets"].get(bucket)


def queue(ledger, block=None):
    kinds = BLOCKS[block] if block else KIND_ORDER
    items = [it for it in ledger["items"] if it["status"] in EXECUTABLE and it["kind"] in kinds]
    return sorted(items, key=lambda it: (KIND_ORDER.index(it["kind"]), it["id"]))


def verify_for_execution(ledger, item_id, tool=None, args=None):
    """The gate gtm_mcp.py checks before any outward call. Returns the item or raises."""
    item = find(ledger, item_id)
    if item["status"] not in EXECUTABLE:
        raise LedgerError(f"{item_id} is {item['status']}, not approved; nothing goes out")
    dec = item.get("decision") or {}
    if not dec.get("approver") or not dec.get("decided_at"):
        raise LedgerError(f"{item_id} has no recorded Release Owner decision")
    if dec["approver"].lower() != ledger["release_owner"].lower():
        raise LedgerError(f"{item_id} was signed by {dec['approver']}, not the Release Owner")
    if tool is not None and tool != item["tool"]:
        raise LedgerError(f"{item_id} approves {item['tool']}, not {tool}")
    current = args if args is not None else item["args"]
    if args_hash(current) != item["approved_args_hash"]:
        raise LedgerError(f"{item_id}'s arguments changed after approval; it needs a new decision")
    if ledger["date"] != today_for(ledger):
        raise LedgerError(f"{item_id} belongs to the {ledger['date']} batch; approvals don't carry "
                          "over to another day")
    reason = stopped_reason(ledger, item["bucket"])
    if reason:
        raise LedgerError(f"{item['bucket']} is stopped for today: {reason}")
    return item


def today_for(ledger, tz_name=None):
    """Today's date in the plan's timezone. Overridable for tests via LINKEDIN_GTM_TODAY."""
    forced = os.environ.get("LINKEDIN_GTM_TODAY")
    if forced:
        return forced
    tz_name = tz_name or ledger.get("timezone") or "America/Los_Angeles"
    try:
        from zoneinfo import ZoneInfo
        return dt.datetime.now(ZoneInfo(tz_name)).date().isoformat()
    except Exception:  # no tz database on this machine: Pacific standard offset is close enough
        return (dt.datetime.now(dt.timezone.utc) - dt.timedelta(hours=8)).date().isoformat()


STOP_OUTCOMES = {"rate_limited", "quota_hit", "blocked"}


def record_execution(ledger, item_id, outcome, now=None, **details):
    """outcome: executed | rate_limited | quota_hit | blocked | checkpoint | uncertain | failed | skipped."""
    item = find(ledger, item_id)
    status = {"executed": EXECUTED, "uncertain": UNCERTAIN, "skipped": SKIPPED}.get(outcome, FAILED)
    item["status"] = status
    item["execution"] = dict(details, outcome=outcome, at=iso(now or now_utc()))
    if outcome in STOP_OUTCOMES:
        stop(ledger, f"{outcome} on {item_id}" + (f", retry_after {details.get('retry_after')}"
                                                   if details.get("retry_after") else ""),
             bucket=item["bucket"])
    if outcome == "checkpoint":
        stop(ledger, f"checkpoint or login issue on {item_id}; all outward work stops")
    return item


def stats(ledgers):
    """Override rate and response time across ledgers: the anti-rubber-stamp signal (Test 4)."""
    decided = [it for lg in ledgers for it in lg["items"] if it.get("decision")]
    n = len(decided)
    edits = sum(1 for it in decided if it["decision"]["decision"] == "edit")
    strikes = sum(1 for it in decided if it["decision"]["decision"] == "strike")
    # Response time per batch, not per item: one presented batch is one decision session.
    per_batch = {}
    for lg in ledgers:
        times = [it["decision"]["response_seconds"] for it in lg["items"] if it.get("decision")]
        if times:
            per_batch[lg["date"]] = max(times)
    batch_times = list(per_batch.values())
    override_rate = (edits + strikes) / n if n else None
    median_batch = statistics.median(batch_times) if batch_times else None
    items_per_batch = (n / len(per_batch)) if per_batch else None
    flags = []
    if n >= 5 and override_rate is not None and override_rate < 0.10:
        flags.append("RUBBER-STAMP?")
    # Under 20 s per item to read a batch is too fast to have read it.
    if median_batch is not None and items_per_batch and median_batch < 20 * items_per_batch:
        flags.append("TOO-FAST?")
    executed = [it for lg in ledgers for it in lg["items"] if it["status"] == EXECUTED]
    by_kind = {}
    for it in executed:
        by_kind[it["kind"]] = by_kind.get(it["kind"], 0) + 1
    return {
        "batches": len(per_batch),
        "decisions": n,
        "approved": n - edits - strikes,
        "edited": edits,
        "struck": strikes,
        "override_rate": round(override_rate, 3) if override_rate is not None else None,
        "median_batch_response_seconds": median_batch,
        "executed_by_kind": by_kind,
        "failed": sum(1 for lg in ledgers for it in lg["items"] if it["status"] in (FAILED, UNCERTAIN)),
        "flags": flags,
    }


def _short(text, n=90):
    text = (text or "").replace("\n", " ")
    return text if len(text) <= n else text[: n - 3] + "..."


def render(ledger, budget=None, policy=None):
    """The one approval message (references/approval-batch-format.md)."""
    policy = policy or load_policy()
    lines = [f"# LinkedIn batch {ledger['date']} for {ledger['release_owner']}", ""]
    drafted = [it for it in ledger["items"] if it["status"] == DRAFTED]
    lines.append(f"{len(drafted)} items waiting. Reply `approve all`, or per item `approve 3`, "
                 "`edit 4: <new text>`, `strike 5`. Nothing goes out without your decision.")
    if ledger["stops"].get("all") or ledger["stops"]["buckets"]:
        lines += ["", "**Stopped today:** " + "; ".join(
            filter(None, [ledger["stops"].get("all")] +
                   [f"{b}: {r}" for b, r in ledger["stops"]["buckets"].items()]))]
    if budget:
        lines += ["", "| Bucket | Plan left | Ceiling left |", "|---|---|---|"]
        for b, row in sorted(budget.items()):
            lines.append(f"| {b} | {row.get('plan_left')} | {row.get('ceiling_left')} |")
    titles = {"engagement": "Engagement (10:30)", "publish": "Publish (12:00)",
              "network": "Network and outreach (13:00)", "inbox": "Inbox hand-backs (15:00)"}
    for block, kinds in BLOCKS.items():
        items = [it for it in ledger["items"] if it["kind"] in kinds and it["status"] == DRAFTED]
        if not items:
            continue
        lines += ["", f"## {titles[block]}", ""]
        for it in sorted(items, key=lambda x: (KIND_ORDER.index(x["kind"]), x["id"])):
            spec = policy["gated_kinds"][it["kind"]]
            text = it["args"].get(spec["text_arg"]) if spec["text_arg"] else None
            who = it["target"].get("name") or it["target"].get("identifier") or \
                (it["args"].get(spec["target_arg"]) if spec["target_arg"] else "") or ""
            link = it["target"].get("url")
            head = f"**{it['id'].split('-')[-1]}. {it['kind']}** (Lane {it['lane']}) {who}"
            if link:
                head += f" <{link}>"
            lines.append(head)
            lines.append(f"Why: {it['reason']}")
            if text is not None:
                lines.append(f"Text ({len(text)} chars):")
                lines += ["> " + ln if ln else ">" for ln in text.splitlines()]
            if it["args"].get("reaction_type"):
                lines.append(f"Reaction: {it['args']['reaction_type']}")
            if it["args"].get("author_organization_id"):
                lines.append(f"Posts as page: {it['target'].get('page')} (chosen by {it['target'].get('page_chosen_by')})")
            if it["args"].get("scheduled_at"):
                lines.append(f"Scheduled: {it['args']['scheduled_at']}")
            if it["sources"]:
                lines.append("Sources: " + ", ".join(it["sources"]))
            if it["warnings"]:
                lines.append("Check: " + "; ".join(it["warnings"]))
            lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def gate_log_commands(ledger, gate_log_dir="GitHub/Projects/_gate-log"):
    """One record_decision.py call per decided item whose row isn't written yet."""
    script = str(Path(gate_log_dir) / "record_decision.py")
    out = []
    for it in ledger["items"]:
        dec = it.get("decision")
        if not dec or (it.get("gate_log") or {}).get("status") == "recorded":
            continue
        status = DECISIONS[dec["decision"]]
        tier = "high-stakes"
        target = it["target"].get("identifier") or it["target"].get("url") or it["id"]
        out.append((it["id"], [
            "python3", script, "--skill", "linkedin-gtm:li-approval-batch", "--tier", tier,
            "--action", f"{it['kind']} {it['id']} (Lane {it['lane']}): {_short(it['reason'], 80)}",
            "--target", str(target), "--decision", GATE_DECISION[status],
            "--approver", dec["approver"], "--requested-at", dec["requested_at"],
        ]))
    return out


def run_gate_log(ledger, gate_log_dir, runner=subprocess.run):
    """Write the rows if record_decision.py is reachable; otherwise leave them pending (local only)."""
    script = Path(gate_log_dir) / "record_decision.py"
    results = []
    for item_id, cmd in gate_log_commands(ledger, gate_log_dir):
        item = find(ledger, item_id)
        if not script.exists():
            item["gate_log"] = {"status": "pending", "why": f"{script} not found on this machine"}
            results.append((item_id, "pending"))
            continue
        r = runner(cmd, capture_output=True, text=True)
        ok = r.returncode == 0
        item["gate_log"] = {"status": "recorded" if ok else "failed",
                            "detail": (r.stdout or r.stderr or "").strip()[-300:]}
        results.append((item_id, item["gate_log"]["status"]))
    return results


def crm_export(ledger):
    """Touch records per references/crm-sync-contract.md. A file to hand to the CRM integration;
    this script writes nothing to the CRM itself."""
    rows = []
    for it in ledger["items"]:
        if it["status"] not in (EXECUTED, UNCERTAIN):
            continue
        ex = it.get("execution") or {}
        rows.append({
            "source": "linkedin-gtm",
            "touch_id": f"li-{it['id']}",
            "occurred_at": ex.get("at"),
            "channel": "linkedin",
            "touch_type": it["kind"],
            "lane": it["lane"],
            "person": {k: it["target"].get(k) for k in ("name", "identifier", "url", "company")},
            "sequence": it.get("sequence"),
            "text": it["args"].get("text") or it["args"].get("note"),
            "linkedin_ref": ex.get("result_ref"),
            "approved_by": (it.get("decision") or {}).get("approver"),
            "send_status": "sent" if it["status"] == EXECUTED else "uncertain",
        })
    return rows


def _load_config(path):
    if not path:
        return {}
    return json.loads(Path(os.path.expanduser(path)).read_text(encoding="utf-8"))


def _json_arg(value):
    if value is None:
        return None
    if value.startswith("@"):
        return json.loads(Path(value[1:]).read_text(encoding="utf-8"))
    return json.loads(value)


def main(argv=None):
    ap = argparse.ArgumentParser(description="linkedin-gtm daily approval batch ledger")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("new"); p.add_argument("--ledger-dir", required=True)
    p.add_argument("--date"); p.add_argument("--config", required=True)

    p = sub.add_parser("add"); p.add_argument("--ledger", required=True)
    p.add_argument("--kind", required=True); p.add_argument("--lane", required=True)
    p.add_argument("--args", required=True, help="JSON object or @file")
    p.add_argument("--reason", required=True); p.add_argument("--target", help="JSON or @file")
    p.add_argument("--sources", nargs="*", default=[]); p.add_argument("--sequence", help="JSON")
    p.add_argument("--config")

    for name in ("render", "present", "list", "crm-export"):
        p = sub.add_parser(name); p.add_argument("--ledger", required=True)
        if name == "render":
            p.add_argument("--budget", help="budget_check.py --json output file")

    p = sub.add_parser("decide"); p.add_argument("--ledger", required=True)
    p.add_argument("--items", required=True, help="comma list of item numbers or ids, or 'all'")
    p.add_argument("--decision", required=True, choices=sorted(DECISIONS))
    p.add_argument("--approver", required=True); p.add_argument("--initials", required=True)
    p.add_argument("--text"); p.add_argument("--note")

    p = sub.add_parser("drop"); p.add_argument("--ledger", required=True)
    p.add_argument("--items", required=True, help="comma list of item numbers or ids")
    p.add_argument("--why", required=True)

    p = sub.add_parser("queue"); p.add_argument("--ledger", required=True)
    p.add_argument("--block", choices=sorted(BLOCKS))

    p = sub.add_parser("stats"); p.add_argument("--ledger-dir", required=True)
    p.add_argument("--days", type=int, default=30)

    p = sub.add_parser("gate-log"); p.add_argument("--ledger", required=True)
    p.add_argument("--gate-log-dir", default="GitHub/Projects/_gate-log")
    p.add_argument("--print-only", action="store_true")

    a = ap.parse_args(argv)
    try:
        if a.cmd == "new":
            cfg = _load_config(a.config)
            date = a.date or today_for({"timezone": cfg.get("timezone")})
            path = Path(a.ledger_dir) / f"{date}.json"
            if path.exists():
                raise LedgerError(f"{path} already exists; one batch per day")
            lg = new_ledger(date, cfg.get("account_sid"), cfg.get("release_owner"))
            lg["timezone"] = cfg.get("timezone", "America/Los_Angeles")
            save(lg, path)
            print(path)
        elif a.cmd == "add":
            lg = load(a.ledger)
            it = add_item(lg, a.kind, _json_arg(a.args), a.lane, a.reason,
                          target=_json_arg(a.target), sources=a.sources,
                          sequence=_json_arg(a.sequence), config=_load_config(a.config))
            save(lg, a.ledger)
            print(json.dumps({"id": it["id"], "warnings": it["warnings"]}))
        elif a.cmd == "render":
            budget = _json_arg("@" + a.budget).get("buckets") if a.budget else None
            print(render(load(a.ledger), budget=budget), end="")
        elif a.cmd == "present":
            lg = load(a.ledger); print(present(lg)); save(lg, a.ledger)
        elif a.cmd == "list":
            for it in load(a.ledger)["items"]:
                print(f"{it['id']}  {it['status']:<9} {it['kind']:<11} lane {it['lane']}  {_short(it['reason'], 60)}")
        elif a.cmd == "decide":
            lg = load(a.ledger)
            if a.items.strip().lower() == "all":
                ids = [it["id"] for it in lg["items"] if it["status"] == DRAFTED]
            else:
                ids = []
                for tok in a.items.split(","):
                    tok = tok.strip()
                    ids.append(tok if "-" in tok else f"{lg['date'].replace('-', '')}-{int(tok):03d}")
            done = decide(lg, ids, a.decision, a.approver, a.initials, new_text=a.text, note=a.note)
            save(lg, a.ledger)
            print(json.dumps([{"id": it["id"], "status": it["status"]} for it in done]))
        elif a.cmd == "drop":
            lg = load(a.ledger)
            ids = [t.strip() if "-" in t else f"{lg['date'].replace('-', '')}-{int(t):03d}"
                   for t in a.items.split(",")]
            done = drop(lg, ids, a.why)
            save(lg, a.ledger)
            print(json.dumps([it["id"] for it in done]))
        elif a.cmd == "queue":
            lg = load(a.ledger)
            for it in queue(lg, a.block):
                why = stopped_reason(lg, it["bucket"])
                print(f"{it['id']}  {it['kind']:<11} {it['bucket']:<26} {'STOPPED: ' + why if why else 'ready'}")
        elif a.cmd == "stats":
            files = sorted(Path(a.ledger_dir).glob("????-??-??.json"))[-a.days:]
            print(json.dumps(stats([load(f) for f in files]), indent=2))
        elif a.cmd == "gate-log":
            lg = load(a.ledger)
            if a.print_only:
                for item_id, cmd in gate_log_commands(lg, a.gate_log_dir):
                    print(" ".join(json.dumps(c) if " " in c else c for c in cmd))
            else:
                for item_id, status in run_gate_log(lg, a.gate_log_dir):
                    print(f"{item_id}: {status}")
                save(lg, a.ledger)
        elif a.cmd == "crm-export":
            for row in crm_export(load(a.ledger)):
                print(json.dumps(row, ensure_ascii=False))
    except LedgerError as e:
        print(f"refused: {e}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
