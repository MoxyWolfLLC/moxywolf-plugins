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
  run|check <doc> --constraints   SR-002: the Goal and Constraints sections alone, record
                              constraints.json. While that record is clean, an item's contradiction
                              scoped `constraints` (no requirement names the item) is listed by
                              check and doesn't fail the item.
  --selftest                  stubbed transport; no network.

The record is the evidence, not the exit code: `check` recomputes the scope, never reads a verdict.
A contradiction clears only by revising the doc and re-running, or by a disposition (SR-003): the record
has no `resolved` flag.

  budget init --stop-usd N [--ledger P] | budget show [--ledger P]
                              SR-003.1: the spend ledger every real run reserves against
                              (GSTACK_SPEND_LEDGER, default ~/.gstack/spend-ledger.json).
  dispose <doc> [--items A | --constraints] --id C1 --by <name> --evidence "<text>"
                              SR-003.6: record that a contradiction is disproved, bound to the record
                              file as it is now. Recorded only on Dorian's words, quoted into --evidence.
"""
import argparse
import fcntl
import hashlib
import math
import json
import os
import re
import sys
import urllib.error
import urllib.request
import uuid
from datetime import datetime, timezone
from pathlib import Path

API_URL = os.environ.get("GSTACK_ANTHROPIC_URL", "https://api.anthropic.com/v1/messages")
EXECUTOR = os.environ.get("GSTACK_SPEC_EXECUTOR", "claude-sonnet-5-5")
ADVISOR = os.environ.get("GSTACK_SPEC_ADVISOR", "claude-fable-5-2")
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
{"contradictions": [{"id": "C1", "requirements": ["<id>", "<id>"], "scope": "item", "scenario": "<what triggers it>", "smallest_change": "<the fix>"}],
 "ambiguities": [{"id": "A1", "requirements": ["<id>"], "question": "<what must be decided>"}]}
"scope" is "constraints" when every requirement in the contradiction is a constraint and none belongs to an item under review; otherwise it is "item". When unsure, say "item".
Empty lists are fine. The prose above the block is for the human; the block is what the gate reads."""

# The advisor docs: Sonnet 5.5 executors reject a forced tool_choice, so the lever is one reminder.
REMINDER = ("You have not consulted the advisor yet. Call advisor now, then give your findings again, "
            "ending with the ```json block.")

ADVISOR_STEER = ("(Advisor: list only the requirement pairs you believe conflict or are ambiguous, "
                 "one line each, no explanation. The executor will write up the scenarios and fixes.)")


class Refused(Exception):
    pass


def _env_values():
    envfile = os.environ.get("GSTACK_ANTHROPIC_ENV")
    if not envfile:
        raise Refused("GSTACK_ANTHROPIC_ENV is not set; point it at the vault's anthropic.env")
    path = Path(envfile).expanduser()
    if not path.exists():
        raise Refused(f"GSTACK_ANTHROPIC_ENV names {path}, which does not exist. No other credential is tried.")
    vals = {}
    for line in path.read_text().splitlines():
        k, _, v = line.partition("=")
        if v.strip():
            vals[k.strip().removeprefix("export ").strip()] = v.strip().strip('"').strip("'")
    if not vals.get("ANTHROPIC_API_KEY"):
        raise Refused(f"{path} sets no ANTHROPIC_API_KEY")
    return vals


def api_key():
    return _env_values()["ANTHROPIC_API_KEY"]


def headers():
    """A key not scoped to a workspace needs ANTHROPIC_WORKSPACE_ID, from the same file."""
    vals = _env_values()
    h = {"x-api-key": vals["ANTHROPIC_API_KEY"], "anthropic-version": "2023-06-01",
         "anthropic-beta": BETA, "content-type": "application/json"}
    if vals.get("ANTHROPIC_WORKSPACE_ID"):
        h["anthropic-workspace-id"] = vals["ANTHROPIC_WORKSPACE_ID"]
    return h


def post(body, timeout=600):
    req = urllib.request.Request(API_URL, data=json.dumps(body).encode(), headers=headers())
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read().decode())
    except urllib.error.HTTPError as e:   # the API's own reason, never a traceback
        try:
            why = json.loads(e.read().decode())["error"]["message"]
        except Exception:
            why = e.reason
        raise Refused(f"Claude API {e.code}: {why}")
    except urllib.error.URLError as e:
        raise Refused(f"Claude API unreachable at {API_URL}: {e.reason}")


def _section(lines, start):
    """Lines from `start` to the next heading at its own level or above."""
    level = len(lines[start]) - len(lines[start].lstrip("#"))
    end = next((i for i in range(start + 1, len(lines))
                if re.match(r"#{1,%d} " % level, lines[i])), len(lines))
    return lines[start:end]


def _cells(row):
    """A markdown table row's cells; an escaped \\| stays inside its cell."""
    return [c.strip() for c in re.split(r"(?<!\\)\|", row.strip().strip("|"))]


def _blanked(lines):
    """Every table's Status and Review ID cells emptied, so bookkeeping never changes the scope."""
    out, blank = [], set()
    for n, line in enumerate(lines):
        if not line.lstrip().startswith("|"):
            blank = set()
        elif n + 1 < len(lines) and re.match(r"^\s*\|[\s:|-]+\|?\s*$", lines[n + 1]) and "-" in lines[n + 1]:
            blank = {i for i, h in enumerate(_cells(line))
                     if h.lower() == "status" or h.lower().startswith("review id")}
        elif blank and set(line.strip()) <= set("|-: "):
            pass   # the separator row
        elif blank:
            line = "| " + " | ".join("" if i in blank else c for i, c in enumerate(_cells(line))) + " |"
        out.append(line)
    return out


def _heading_id(line):
    """The id a `### <id> — title` heading declares, compared whole: `R` is not `R-001` (review F1)."""
    m = re.match(r"### ([^\s—–:]+)", line)
    return m.group(1).rstrip(".,;:") if m else None


def _table_item(lines, item):
    """The header, separator and row whose first cell is `item`, with its Status and Review ID cells
    blanked, or None. The design-doc template writes items this way (one row per item)."""
    for n, line in enumerate(lines):
        if line.lstrip().startswith("|") and _cells(line)[0].strip("*` ") == item:
            break
    else:
        return None
    top = n
    while top > 0 and lines[top - 1].lstrip().startswith("|"):
        top -= 1
    return [line] if top == n else [lines[top], lines[top + 1], line]


def scope(text, item=None):
    """(name, text_sent) for one item, or for the whole file when item is None. Raises Refused for an
    item the doc doesn't contain."""
    lines = text.splitlines()
    if item is None:
        out, name = lines, "all"
    else:
        out = []
        for head in CONTEXT:
            i = next((n for n, l in enumerate(lines) if l.strip() == head), None)
            if i is not None:
                out += _section(lines, i)
        i = next((n for n, l in enumerate(lines) if _heading_id(l) == item), None)
        row = None if i is not None else _table_item(lines, item)
        if i is None and row is None:
            raise Refused(f"the doc has no item {item}")
        out += _section(lines, i) if i is not None else ["## Item", ""] + row
        name = item
    # ponytail: a status line is any line starting **Status:**; other per-item bookkeeping still counts
    return name, "\n".join(l for l in _blanked(out) if not l.lstrip().startswith("**Status:**")) + "\n"


def scope_constraints(text):
    """SR-002.1: ("constraints", text_sent): the context sections alone, nothing from the items onward."""
    lines, out = text.splitlines(), []
    for head in CONTEXT:
        i = next((n for n, l in enumerate(lines) if l.strip() == head), None)
        if i is not None:
            out += _section(lines, i)
    if not out:
        raise Refused(f"the doc has neither of {', '.join(CONTEXT)}")
    return "constraints", "\n".join(l for l in _blanked(out) if not l.lstrip().startswith("**Status:**")) + "\n"


def effective_scope(entry, item):
    """SR-002.4: "constraints" only when the entry says so, an item is under review, and none of its
    requirements names that item's id, matched whole (ME-00 is not ME-004). Anything else is "item"."""
    if entry.get("scope") != "constraints" or not item:
        return "item"
    # review F1: `-` continues an id (ME-004-extra is its own item, as _heading_id reads it); `.` starts a criterion
    named = re.compile(r"(?<![A-Za-z0-9-])" + re.escape(item) + r"(?![A-Za-z0-9-])")
    return "item" if any(named.search(str(r)) for r in entry.get("requirements") or ()) else "constraints"


# ---------- SR-003: spend ledger, prices and the worst-case bound ----------

PRICES = Path(__file__).resolve().with_name("spec_review_prices.json")
RATE_KEYS = ("input", "output", "cache_read", "cache_write")
# SR-003.3, frozen on Dorian's choice of 2026-11-21 ("Tight formula + allowance"); see worst_case_usd.
N_ITER, O_TOK, A_CALLS, M_TOK, K_TOK, M_REMIND, F_E, F_A = 10, 20000, 3, 4096, 4160, 200, 10000, 10000
R_REQ = 1 + MAX_RESUMES + 1   # the first request, six resumptions, one reminder


def _finite(x):
    return isinstance(x, (int, float)) and not isinstance(x, bool) and math.isfinite(x) and x >= 0


def load_prices(path=None):
    """{model: {input, output, cache_read, cache_write}} in USD per token (SR-003.5)."""
    path = Path(path or PRICES)
    try:
        data = json.loads(path.read_text())
    except (OSError, json.JSONDecodeError) as e:
        raise Refused(f"budget_refused: prices file {path} unreadable: {e}")
    models = data.get("models") if isinstance(data, dict) else None
    if data.get("schema") != "spec-review-prices/1" or not isinstance(models, dict):
        raise Refused(f"budget_refused: {path} is not a spec-review-prices/1 file")
    for m, r in models.items():
        if not isinstance(r, dict) or not all(_finite(r.get(k)) for k in RATE_KEYS):
            raise Refused(f"budget_refused: {path} has a missing or invalid rate for {m}")
    return models


def _rates(prices, model):
    if model not in prices:
        raise Refused(f"budget_refused: {model} is not in the prices file; no request sent")
    return prices[model]


def worst_case_usd(body_bytes, executor, advisor, prices):
    """SR-003.3: the most one scope can be charged, b = the first request body's UTF-8 bytes.

    Sources: https://platform.claude.com/docs/en/agents-and-tools/tool-use/advisor-tool (a request's
    server loop runs at most 10 iterations, each re-sending the growing conversation; executor input is
    billed per iteration; the advisor reads the full transcript) and
    https://platform.claude.com/docs/en/about-claude/pricing (rates). Every input token is priced at the
    higher of its model's input and cache-write rate. F_E and F_A are an ASSUMED allowance for the
    executor's and the advisor's framing, which the docs don't size; an actual above the reservation is
    recorded in full (SR-003.4)."""
    e, a, b = _rates(prices, executor), _rates(prices, advisor), body_bytes
    e_in = (N_ITER * R_REQ * (b + F_E + M_REMIND) + N_ITER * O_TOK * R_REQ * (R_REQ + 1) // 2
            + N_ITER * R_REQ * A_CALLS * K_TOK)
    a_in = A_CALLS * (F_A + b + F_E + M_REMIND + R_REQ * O_TOK + A_CALLS * K_TOK)
    return (max(e["input"], e["cache_write"]) * e_in + e["output"] * R_REQ * O_TOK
            + max(a["input"], a["cache_write"]) * a_in + a["output"] * A_CALLS * M_TOK)


def ledger_path(ledger=None):
    return Path(ledger or os.environ.get("GSTACK_SPEND_LEDGER") or Path.home() / ".gstack" / "spend-ledger.json")


ROW_KEYS = {"id", "scope", "doc", "reserved_usd", "actual_usd", "state", "reserved_at", "settled_at"}


def _valid_ledger(db, path):
    """A well-formed spend-ledger/1 or Refused; every number finite and non-negative (SR-003.1)."""
    rows = db.get("reservations") if isinstance(db, dict) else None
    if (not isinstance(db, dict) or db.get("schema") != "spend-ledger/1" or not isinstance(rows, list)
            or not _finite(db.get("stop_usd")) or not _finite(db.get("spent_usd"))):
        raise Refused(f"budget_refused: {path} is not a well-formed spend ledger (stop_usd, spent_usd, reservations)")
    for r in rows:
        ok = (isinstance(r, dict) and set(r) >= ROW_KEYS and r["state"] in ("held", "settled") and _finite(r["reserved_usd"])
              and all(isinstance(r.get(k), str) and r[k] for k in ("id", "scope", "doc", "reserved_at")))
        if ok and r["state"] == "held":
            ok = r.get("actual_usd") is None and r.get("settled_at") is None
        elif ok:
            ok = _finite(r.get("actual_usd")) and isinstance(r.get("settled_at"), str) and bool(r["settled_at"])
        if not ok:
            raise Refused(f"budget_refused: {path} has a malformed reservation row {r!r:.120}")
    return db


def _held(db):
    return sum(r["reserved_usd"] for r in db["reservations"] if r["state"] == "held")


def _locked():
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from review_run import locked   # the one flock + atomic-replace helper (SR-003.1)
    return locked


def read_ledger(ledger=None):
    """Read under the ledger's lock, never writing (budget show)."""
    path = ledger_path(ledger)
    if not path.exists():
        raise Refused(f"budget_refused: no spend ledger at {path}; a person creates one with `budget init`")
    class Read(Exception):   # leaves locked() before its write: a read never rewrites the ledger
        pass
    try:
        with _locked()(path) as db:
            raise Read(_valid_ledger(db, path))
    except Read as r:
        return r.args[0]
    except json.JSONDecodeError as e:
        raise Refused(f"budget_refused: {path} is not JSON: {e}")


def budget_init(stop_usd, ledger=None):
    path = ledger_path(ledger)
    try:
        stop = float(stop_usd)
    except (TypeError, ValueError):
        raise Refused(f"--stop-usd {stop_usd!r} is not a number")
    if not _finite(stop):
        raise Refused(f"--stop-usd must be finite and non-negative, not {stop_usd}")
    if path.exists():
        raise Refused(f"{path} already exists; budget init never replaces a ledger")
    path.parent.mkdir(parents=True, exist_ok=True)
    with _locked()(path) as db:
        if db.get("schema"):   # created by another process between the check and the lock
            raise Refused(f"{path} already exists; budget init never replaces a ledger")
        db.clear()
        db.update({"schema": "spend-ledger/1", "stop_usd": stop if stop != int(stop) else int(stop),
                   "spent_usd": 0, "reservations": []})
    print(f"spend ledger {path}: stop_usd {stop}")


def budget_show(ledger=None):
    db = read_ledger(ledger)
    held = _held(db)
    print(f"stop_usd {db['stop_usd']:.6f}\nspent_usd {db['spent_usd']:.6f}\nheld_usd {held:.6f}\n"
          f"remaining_usd {max(0.0, db['stop_usd'] - db['spent_usd'] - held):.6f}")
    try:   # SR-003.5: a stale date is shown, not refused; Dorian decides when to re-verify
        verified = json.loads(Path(PRICES).read_text()).get("verified")
    except (OSError, json.JSONDecodeError, AttributeError) as e:
        verified = f"unknown ({e})"
    print(f"prices_verified {verified} ({PRICES})")
    for r in db["reservations"]:
        if r["state"] == "held":
            print(f"held {r.get('id')} {r.get('scope')} {r.get('doc')} {r['reserved_usd']:.6f} since {r.get('reserved_at')}")


def _now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def reserve(ledger, scope_name, doc_name, amount):
    """Hold `amount` or raise budget_refused, writing nothing (SR-003.2)."""
    path = ledger_path(ledger)
    if not path.exists():
        raise Refused(f"budget_refused: no spend ledger at {path}; a person creates one with `budget init`")
    rid = uuid.uuid4().hex
    with _locked()(path) as db:
        _valid_ledger(db, path)
        held = _held(db)
        if db["spent_usd"] + held + amount > db["stop_usd"]:
            raise Refused(f"budget_refused: stop_usd {db['stop_usd']:.6f}, spent_usd {db['spent_usd']:.6f}, "
                          f"held_usd {held:.6f}, reservation {amount:.6f}; no request sent")
        db["reservations"].append({"id": rid, "scope": scope_name, "doc": doc_name, "reserved_usd": amount,
                                   "actual_usd": None, "state": "held", "reserved_at": _now(), "settled_at": None})
    return rid


def charged(responses, prices):
    """(known USD, certain) from every response's usage.iterations, each entry at its own model's rates.
    An entry without a model is the executor's; an advisor entry without one is the advisor's."""
    total, certain = 0.0, True
    for resp in responses:
        use = resp.get("usage") if isinstance(resp, dict) else None
        its = use.get("iterations") if isinstance(use, dict) else None
        if not isinstance(its, list) or not its:
            certain = False
            continue
        for e in its:
            if not isinstance(e, dict):   # malformed: uncertain, and the known charges still count
                certain = False
                continue
            model = e.get("model")   # review F5: only an omitted model takes the default
            if model is None:
                model = ADVISOR if e.get("type") == "advisor_message" else EXECUTOR
            if not isinstance(model, str) or not model:
                certain = False
                continue
            toks = [e.get(k) for k in ("input_tokens", "output_tokens", "cache_read_input_tokens",
                                       "cache_creation_input_tokens")]
            if model not in prices:
                certain = False
                continue
            r = prices[model]
            for x, k in zip(toks, RATE_KEYS):   # a missing class is uncertain; the known ones still count
                if isinstance(x, int) and not isinstance(x, bool) and x >= 0:
                    total += x * r[k]
                else:
                    certain = False
    return total, certain


class Metered:
    """The real transport behind a reservation: reserves the scope's worst case before the first request,
    remembers every response, and marks the scope uncertain if any request fails mid-flight."""

    def __init__(self, transport, ledger, scope_name, doc_name, prices):
        self.transport, self.ledger, self.scope, self.doc, self.prices = transport, ledger, scope_name, doc_name, prices
        self.rid, self.responses, self.certain = None, [], True

    def __call__(self, body):
        if self.rid is None:
            self.rid = reserve(self.ledger, self.scope, self.doc,
                               worst_case_usd(len(json.dumps(body).encode()), EXECUTOR, ADVISOR, self.prices))
        try:
            resp = self.transport(body)
        except BaseException:
            self.certain = False
            raise
        self.responses.append(resp)
        return resp

    def settle(self):
        """Settle once; True when the actual exceeded the reservation (SR-003.4)."""
        if self.rid is None:
            return False
        known, certain = charged(self.responses, self.prices)
        actual = known if (certain and self.certain) else None
        path = ledger_path(self.ledger)
        with _locked()(path) as db:
            row = next(r for r in db["reservations"] if r["id"] == self.rid)
            reserved = row["reserved_usd"]
            value = actual if actual is not None else max(reserved, known)
            if row["state"] == "held":
                row.update(actual_usd=value, state="settled", settled_at=_now())
                db["spent_usd"] = db["spent_usd"] + value
        self.rid_settled = value
        return value > reserved



def record_path(doc, name):
    return Path(doc).parent / "reviews" / "spec-review" / f"{name}.json"


def review(scope_text, post=post):
    """Returns (final_text, usage_iterations, advisor_calls, cache). Resumes pause_turn until the turn ends.
    cache is {read, write} summed from every response's usage, or a str naming why it's unknown (ME-002.4)."""
    tools = [{"type": "advisor_20260301", "name": "advisor", "model": ADVISOR,
              "max_uses": 3, "max_tokens": 4096}]
    messages = [{"role": "user", "content": f"{ADVISOR_STEER}\n\n<plan>\n{scope_text}</plan>"}]
    iterations, advisor_calls, text, reminded, resumes = [], 0, [], False, 0
    cache = {"read": 0, "write": 0}
    while True:
        # ME-002.1: automatic caching; tools and thinking never change mid-run, so resends read the prefix
        resp = post({"model": EXECUTOR, "max_tokens": 20000, "system": SYSTEM, "cache_control": {"type": "ephemeral"},
                     "thinking": {"type": "adaptive"}, "tools": tools, "messages": messages})
        u = resp.get("usage") or {}
        if isinstance(cache, dict):   # one response without the fields makes the run's cache unknown, never 0
            if isinstance(u.get("cache_read_input_tokens"), int) and isinstance(u.get("cache_creation_input_tokens"), int):
                cache = {"read": cache["read"] + u["cache_read_input_tokens"],
                         "write": cache["write"] + u["cache_creation_input_tokens"]}
            else:
                cache = "a response's usage lacked cache_read_input_tokens or cache_creation_input_tokens"
        content = resp.get("content") or []
        iterations += (resp.get("usage") or {}).get("iterations") or []
        advisor_calls += sum(1 for b in content if b.get("type") == "server_tool_use" and b.get("name") == "advisor")
        text += [b["text"] for b in content if b.get("type") == "text"]
        if resp.get("stop_reason") == "pause_turn":
            if resumes == MAX_RESUMES:   # review F2: six resumptions, never a seventh
                raise Refused(f"turn still paused after {MAX_RESUMES} resumptions")
            resumes += 1
            messages.append({"role": "assistant", "content": content})   # unchanged; the server resumes
            continue
        if resp.get("stop_reason") == "max_tokens":
            raise Refused("executor hit max_tokens before closing its findings block")
        if advisor_calls == 0 and not reminded:   # findings come from the reply after the reminder
            messages += [{"role": "assistant", "content": content}, {"role": "user", "content": REMINDER}]
            text, reminded = [], True
            continue
        return "\n".join(text), iterations, advisor_calls, cache


def findings(text):
    blocks = re.findall(r"```json\s*(\{.*?\})\s*```", text, re.S)
    if not blocks:
        raise Refused("executor returned no ```json findings block")
    try:
        f = json.loads(blocks[-1])
    except json.JSONDecodeError as e:
        raise Refused(f"findings block is not JSON: {e}")
    why = malformed(f)
    if why:   # review F3: a failed review never reads as a clean one
        raise Refused(f"findings block is malformed: {why}")
    return {k: f[k] for k in FIELDS}


FIELDS = {"contradictions": ("id", "requirements", "scenario", "smallest_change"),
          "ambiguities": ("id", "requirements", "question")}


def malformed(f):
    """None when `f` carries both findings lists with every field, else the reason. Used on the
    executor's block and on a record read back by check."""
    if not isinstance(f, dict):
        return "not an object"
    for key, need in FIELDS.items():
        if not isinstance(f.get(key), list):
            return f"{key} is not a list"
        for e in f[key]:
            if not isinstance(e, dict) or any(not e.get(n) for n in need) or not isinstance(e["requirements"], list):
                return f"a {key} entry lacks one of {', '.join(need)}"
    return None


def _review_scope(doc, name, sent, transport, constraints):
    """One scope's review and record; returns its contradiction count."""
    reply, iterations, calls, cache = review(sent, transport)
    if calls < 1:   # SR-001.2: "Fable reviewed this" stays true
        raise Refused(f"{name}: the executor finished without consulting the advisor, after a reminder; no record written, re-run")
    f = findings(reply)
    rec = {"schema": "spec-review/3", "review_id": uuid.uuid4().hex, "doc": doc.name, "item": None if name == "all" or constraints else name,
           "scope_sha256": hashlib.sha256(sent.encode()).hexdigest(),
           "reviewed_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
           "executor": EXECUTOR, "advisor": ADVISOR, "advisor_calls": calls, "usage": iterations,
           "cache": cache if isinstance(cache, dict) else None,
           "contradictions": f["contradictions"], "ambiguities": f["ambiguities"]}
    if not isinstance(cache, dict):
        rec["cache_reason"] = cache
    rp = record_path(doc, name)
    rp.parent.mkdir(parents=True, exist_ok=True)
    rp.write_text(json.dumps(rec, indent=2) + "\n")
    rp.with_suffix(".md").write_text(f"# Spec review: {doc.name} {name}\n\n_{rec['reviewed_at']} · "
                                     f"{EXECUTOR} with {ADVISOR} advisor ({calls} calls)_\n\n{reply}\n")
    n = len(f["contradictions"])
    print(f"spec_review {name}: {n} contradiction(s), {len(f['ambiguities'])} ambiguit(ies); "
          f"advisor called {calls}x; wrote {rp}")
    return n


def cmd_run(doc, items=None, post=post, constraints=False, ledger=None):
    """One review per item (SR-001.1), one for the whole file, or one for the constraints alone
    (SR-002.1). Exit 2 if any record has a contradiction."""
    doc = Path(doc)
    text = doc.read_text()
    if constraints and items:
        raise Refused("--constraints reviews the constraints alone; it takes no --items")
    # refuses an unknown item before any request
    scopes = [scope_constraints(text)] if constraints else [scope(text, i) for i in (items or [None])]
    worst = 0
    real = post is globals()["post"]   # SR-003.2: the real transport always spends against a ledger
    metered = real or ledger is not None
    prices = load_prices() if metered else None
    if metered:   # an unlisted model or a missing ledger refuses before any request
        _rates(prices, EXECUTOR), _rates(prices, ADVISOR)
        if not ledger_path(ledger).exists():
            raise Refused(f"budget_refused: no spend ledger at {ledger_path(ledger)}; a person creates one with `budget init`")
    for name, sent in scopes:
        meter = Metered(post, ledger, name, doc.name, prices) if metered else None
        try:   # SR-003.4: whatever ends the scope, including a failed record write, settles it once
            n = _review_scope(doc, name, sent, meter or post, constraints)
        except BaseException:
            if meter:
                meter.settle()
            raise
        worst = max(worst, 2 if n else 0)
        if meter and meter.settle():   # the record is written; the next scope never starts
            raise Refused(f"budget_overrun: {name} cost {meter.rid_settled:.6f} USD, above its reservation; "
                          f"recorded in {ledger_path(ledger)}; no further scope runs")
    return worst


def check(doc, items=None, constraints=False):
    """(ok, reason). Every item must pass on its own record, so a batch passes in any order.
    Read by cmd_check and by peer_review.py open. constraints=True checks constraints.json alone,
    where every contradiction blocks (SR-002.1)."""
    doc = Path(doc)
    if not doc.exists():
        return False, f"spec_review_missing: {doc} does not exist"
    if constraints and items:
        return False, "spec_review_missing: --constraints takes no --items"
    text, names, asks, noted, cleared = doc.read_text(), [], [], [], []

    def no(reason):   # review F1: a failing check still lists the constraints findings it set aside
        return False, reason + (f"; also {len(noted)} contradiction(s) among the constraints, not blocking under the "
                                "clean constraints record:" + "".join(noted) if noted else "") + (
            f"; {len(cleared)} contradiction(s) set aside by disposition (SR-003):" + "".join(cleared) if cleared else "")

    for item in (items or [None]):
        hint = f"run `spec_review.py run {doc}{' --constraints' if constraints else ' --items ' + item if item else ''}`"
        try:
            name, sent = scope_constraints(text) if constraints else scope(text, item)
        except Refused as e:
            return no(f"spec_review_missing: {e}")
        rp = record_path(doc, name)
        if not rp.exists():
            return no(f"spec_review_missing: no {rp.relative_to(doc.parent)} beside {doc.name}; {hint}")
        raw = rp.read_bytes()   # review F2: judged, validated and matched against one read
        rec = json.loads(raw)
        if rec.get("scope_sha256") != hashlib.sha256(sent.encode()).hexdigest():
            return no(f"spec_review_stale: {rp.name} reviewed a different {name} in {doc.name}; {hint}")
        if malformed(rec):
            return no(f"spec_review_missing: {rp.name} is malformed ({malformed(rec)}); {hint}")
        if (rec.get("advisor_calls") or 0) < 1:
            return no(f"spec_review_missing: {rp.name} records no advisor call; {hint}")
        open_ = rec.get("contradictions") or []
        gone = disposed(rp, rec, hashlib.sha256(raw).hexdigest())   # SR-003.7: only entries naming this record file as it is now
        if gone:
            open_ = [c for c in open_ if c.get("id") not in gone]
            cleared += [f"\n  {name} {cid} disproved by {d['by']}: {d['evidence']}" for cid, d in gone.items()]
        # SR-002.4/.5: an item's constraints-scoped contradictions don't fail it while the constraints
        # record is clean; with that record missing, stale or open they block as before
        among = [] if constraints else [c for c in open_ if effective_scope(c, item) == "constraints"]
        if among:
            c_ok, c_why = check(doc, constraints=True)
            if c_ok:
                open_ = [c for c in open_ if c not in among]
                noted += [f"\n  {name} {c.get('id', '?')} ({', '.join(map(str, c['requirements']))}): {c['scenario']}" for c in among]
            else:
                ids = ", ".join(c.get("id", "?") for c in among)
                return no((f"spec_review_open: {name} has {len(among)} contradiction(s) among the constraints ({ids}) and "
                           f"no clean constraints record ({c_why.split(';')[0]}); run `spec_review.py run {doc} --constraints`"))
        if open_:
            ids = ", ".join(c.get("id", "?") for c in open_)
            return no(f"spec_review_open: {name} has {len(open_)} open contradiction(s) ({ids}); amend {doc.name}, then re-run")
        names.append(name)
        asks += [f"\n  {name} {a['id']} ({', '.join(map(str, a['requirements']))}): {a['question']}" for a in rec["ambiguities"]]
    tail = f"; {len(asks)} open ambiguit{'y' if len(asks) == 1 else 'ies'}, not blocking:" + "".join(asks) if asks else ""
    if noted:
        tail += f"; {len(noted)} contradiction(s) among the constraints, not blocking under the clean constraints record:" + "".join(noted)
    if cleared:
        tail += f"; {len(cleared)} contradiction(s) set aside by disposition (SR-003):" + "".join(cleared)
    return True, f"spec_review_ok: {', '.join(names)} in {doc.name} match their records, no open contradictions{tail}"


def dispositions_path(rp):
    return rp.with_name(rp.stem + ".dispositions.json")


def _entries(path):
    if not path.exists():
        return []
    data = json.loads(path.read_text())
    return data.get("dispositions", []) if isinstance(data, dict) else data


def disposed(rp, rec, sha):
    """{id: entry} for contradictions a `disproved` entry names against `sha`, the record bytes the caller read.
    An id the record holds more than once is never set aside."""
    path = dispositions_path(rp)
    if not path.exists():
        return {}
    ids = [c.get("id") for c in rec.get("contradictions") or []]
    return {e["id"]: e for e in _entries(path)
            if e.get("record_sha256") == sha and e.get("disposition") == "disproved"
            and ids.count(e.get("id")) == 1 and e.get("by") and e.get("evidence")}


def dispose(doc, cid, by, evidence, items=None, constraints=False, disposition="disproved"):
    """SR-003.6: append one `disproved` entry beside the record; refuse, writing nothing, otherwise."""
    doc = Path(doc)
    if disposition != "disproved":
        raise Refused(f"disposition must be disproved, not {disposition!r}")
    if not (by or "").strip() or not (evidence or "").strip():
        raise Refused("dispose needs a non-empty --by and --evidence (Dorian's words, quoted)")
    if constraints and items:
        raise Refused("--constraints takes no --items")
    if items and len(items) != 1:
        raise Refused("dispose takes one item")
    if not doc.exists():
        raise Refused(f"{doc} does not exist")
    text = doc.read_text()
    name, sent = scope_constraints(text) if constraints else scope(text, items[0] if items else None)
    rp = record_path(doc, name)
    if not rp.exists():
        raise Refused(f"spec_review_missing: no {rp.name} beside {doc.name}")
    raw = rp.read_bytes()
    try:
        rec = json.loads(raw)
    except json.JSONDecodeError as e:
        raise Refused(f"{rp.name} is not JSON: {e}")
    if malformed(rec):
        raise Refused(f"{rp.name} is malformed ({malformed(rec)})")
    if rec.get("scope_sha256") != hashlib.sha256(sent.encode()).hexdigest():
        raise Refused(f"spec_review_stale: {rp.name} reviewed a different {name}; re-run before disposing")
    if (rec.get("advisor_calls") or 0) < 1:
        raise Refused(f"{rp.name} records no advisor call")
    n = [c.get("id") for c in rec["contradictions"]].count(cid)
    if n != 1:
        raise Refused(f"{rp.name} holds {cid} {n} times; a disposition names exactly one contradiction")
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from review_run import locked   # the one flock + atomic-replace helper (SR-003.6)
    entry = {"id": cid, "record_sha256": hashlib.sha256(raw).hexdigest(), "disposition": "disproved",
             "by": by.strip(), "evidence": evidence.strip(),
             "recorded_at": datetime.now(timezone.utc).isoformat(timespec="seconds")}
    with locked(dispositions_path(rp)) as db:
        if hashlib.sha256(rp.read_bytes()).hexdigest() != entry["record_sha256"]:
            raise Refused(f"{rp.name} changed while disposing; re-run dispose")
        db.pop("runs", None)   # locked() seeds an empty review_run ledger; this file holds dispositions only
        db.setdefault("dispositions", []).append(entry)
    print(f"spec_review {name}: {cid} disproved by {entry['by']}; wrote {dispositions_path(rp)}")
    return entry


def stub_post(body_json, advise=True):
    """A transport that pauses each new turn on an advisor call, then ends with `body_json` as
    findings; advise=False ends at once with no advisor call. Shared with test_spec_review_gate.py."""
    seen = []

    def stub(req):
        seen.append(req)
        if advise and req["messages"][-1]["role"] == "user":
            return {"stop_reason": "pause_turn", "usage": {"iterations": [{"type": "message"}]},
                    "content": [{"type": "server_tool_use", "id": "s1", "name": "advisor", "input": {}}]}
        assert not advise or req["messages"][-1]["role"] == "assistant", "resume must resend the paused turn"
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
    return [record_path(doc, i or "all") for i in (items or [None])]


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


def assert_api_error_is_refused():
    """A 400 from the API becomes Refused carrying the API's message, sent with the workspace header."""
    import http.server
    import threading
    global API_URL
    got = {}

    class H(http.server.BaseHTTPRequestHandler):
        def do_POST(h):
            got["ws"] = h.headers.get("anthropic-workspace-id")
            h.rfile.read(int(h.headers["Content-Length"]))
            h.send_response(400); h.end_headers()
            h.wfile.write(b'{"type":"error","error":{"type":"invalid_request_error","message":"no workspace"}}')

        def log_message(h, *a):
            pass
    srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), H)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    saved, API_URL = API_URL, f"http://127.0.0.1:{srv.server_port}/v1/messages"
    try:
        post({"model": "m"})
        raise AssertionError("a 400 was not refused")
    except Refused as e:
        assert str(e) == "Claude API 400: no workspace", e
        assert got["ws"] == "wrkspc_1"
    finally:
        API_URL = saved
        srv.shutdown()


TABLE = """## Items

| ID | Item | Acceptance criteria | Status | Review ID / merge |
|---|---|---|---|---|
| T-001 | Rates | 1. Works offline. 2. Fetches live rates. | planned | PR #9 |
| T-002 | Other | 1. Unrelated. | planned | |

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
        name, sent = scope(DEMO, "R-001")
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
        # review F1: a prefix of an id is not an id
        for bad in ("R", "R-00", "R-0011"):
            try:
                scope(DEMO, bad)
                raise AssertionError(f"{bad} matched")
            except Refused as e:
                assert f"no item {bad}" in str(e)
        assert scope(DEMO.replace("### R-001 — Rates", "### R-001: Rates"), "R-001")[0] == "R-001"
        # review F2: six resumptions, then refuse before a seventh
        def paused(n):
            calls = []
            def p(req):
                calls.append(req)
                if len(calls) <= n:
                    return {"stop_reason": "pause_turn", "content": [{"type": "server_tool_use", "name": "advisor", "input": {}}]}
                return {"stop_reason": "end_turn", "content": [{"type": "text", "text": "```json\n{\"contradictions\": [], \"ambiguities\": []}\n```"}]}
            p.calls = calls
            return p
        assert review("x", post=paused(6))[2] == 6 and len(paused(6).calls) == 0
        p7 = paused(7)
        try:
            review("x", post=p7)
            raise AssertionError("a seventh resumption was sent")
        except Refused as e:
            assert "after 6 resumptions" in str(e) and len(p7.calls) == 7
        # ME-002.1/.4/.5: every request asks for caching, a resume and a reminder included; sums come from usage
        def cached(n_pause, reads, writes, remind=False):
            calls, it = [], iter(zip(reads, writes))
            def p(req):
                calls.append(json.loads(json.dumps(req)))   # snapshot: review() keeps appending to messages
                r, w = next(it)
                u = {"cache_read_input_tokens": r, "cache_creation_input_tokens": w} if r is not None else {}
                if remind and len(calls) == 1:
                    return {"stop_reason": "end_turn", "usage": u, "content": [{"type": "text", "text": "no json"}]}
                if len(calls) <= n_pause + remind:
                    return {"stop_reason": "pause_turn", "usage": u,
                            "content": [{"type": "server_tool_use", "name": "advisor", "input": {}}]}
                return {"stop_reason": "end_turn", "usage": u,
                        "content": [{"type": "text", "text": "```json\n{\"contradictions\": [], \"ambiguities\": []}\n```"}]}
            p.calls = calls
            return p
        c = cached(1, [0, 900, 950], [800, 50, 10], remind=True)
        out = review("x", post=c)
        assert len(c.calls) == 3 and all(r["cache_control"] == {"type": "ephemeral"} for r in c.calls), c.calls
        assert c.calls[1]["messages"][-1]["content"] == REMINDER and c.calls[2]["messages"][-1]["role"] == "assistant"
        assert out[3] == {"read": 1850, "write": 860}, out[3]
        gap = review("x", post=cached(1, [5, None], [5, None]))[3]
        assert isinstance(gap, str) and "lacked" in gap, "a response without the fields makes cache unknown, not a partial sum"
        assert ADVISOR == os.environ.get("GSTACK_SPEC_ADVISOR", "claude-fable-5-2")
        # ME-002.5, review F3: the same three responses through cmd_run reach the saved record
        doc.write_text(DEMO)
        c3 = cached(1, [0, 900, 950], [800, 50, 10], remind=True)
        assert cmd_run(doc, ["R-001"], post=c3) == 0
        assert all(r["cache_control"] == {"type": "ephemeral"} for r in c3.calls) and len(c3.calls) == 3
        saved = json.loads(record_path(doc, "R-001").read_text())
        assert saved["cache"] == {"read": 1850, "write": 860} and "cache_reason" not in saved, saved
        import contextlib
        import io
        # SR-002.6: the constraints are reviewed alone, and an item's review blocks on the item
        clean = {"contradictions": [], "ambiguities": []}
        cname, csent = scope_constraints(DEMO)
        assert cname == "constraints" and "Offline first" in csent and "Ship it" in csent
        assert "R-001" not in csent and "Works offline" not in csent and "Amendments" not in csent, csent
        among = {"contradictions": [{"id": "C1", "requirements": ["Offline first", "Ship it"], "scope": "constraints",
                                     "scenario": "s", "smallest_change": "c"}], "ambiguities": []}
        cmd_run(doc, ["R-001"], post=stub_post(among))
        ok, why = check(doc, ["R-001"])
        assert not ok and "no clean constraints record (spec_review_missing" in why, why      # missing
        assert cmd_run(doc, post=stub_post(clean), constraints=True) == 0 and check(doc, constraints=True)[0]
        ok, why = check(doc, ["R-001"])
        assert ok and "1 contradiction(s) among the constraints, not blocking" in why and "R-001 C1" in why, why
        assert cmd_run(doc, post=stub_post(among), constraints=True) == 2                        # open: scope is ignored there
        assert "spec_review_open" in check(doc, constraints=True)[1]
        assert "no clean constraints record (spec_review_open" in check(doc, ["R-001"])[1]
        cmd_run(doc, post=stub_post(clean), constraints=True)
        doc.write_text(DEMO.replace("Offline first", "Online first"))                             # stale, for both
        assert "spec_review_stale" in check(doc, constraints=True)[1]
        doc.write_text(DEMO)
        cpath = record_path(doc, "constraints"); crec = json.loads(cpath.read_text()); crec["scope_sha256"] = "0" * 64
        cpath.write_text(json.dumps(crec))
        assert "no clean constraints record (spec_review_stale" in check(doc, ["R-001"])[1]
        cmd_run(doc, post=stub_post(clean), constraints=True)
        # a constraints label on an entry naming the reviewed item is read as item, and so is no label
        for entry in ({**among["contradictions"][0], "requirements": ["Offline first", "R-001.2"]},
                      {k: v for k, v in among["contradictions"][0].items() if k != "scope"}):
            cmd_run(doc, ["R-001"], post=stub_post({"contradictions": [entry], "ambiguities": []}))
            ok, why = check(doc, ["R-001"])
            assert not ok and "has 1 open contradiction(s) (C1)" in why, why
        # review F1: a record with both scopes fails on the item's and still lists the constraints one
        both = [among["contradictions"][0], {"id": "C2", "requirements": ["R-001.1", "R-001.2"], "scope": "item",
                                             "scenario": "offline", "smallest_change": "drop 2"}]
        cmd_run(doc, ["R-001"], post=stub_post({"contradictions": both, "ambiguities": []}))
        ok, why = check(doc, ["R-001"])
        assert not ok and "has 1 open contradiction(s) (C2)" in why and "also 1 contradiction(s) among the constraints" in why and "R-001 C1" in why, why
        cmd_run(doc, ["R-001"], post=stub_post(among)); cmd_run(doc, ["R-002"], post=stub_post(conflict))   # a later item fails
        ok, why = check(doc, ["R-001", "R-002"])
        assert not ok and "R-002 has 1 open contradiction(s)" in why and "R-001 C1" in why, why
        e = {"scope": "constraints", "requirements": ["cites R-0011 and XR-001", "GA-011"]}
        assert effective_scope(e, "R-001") == "constraints" and effective_scope(e, "GA-011") == "item"
        assert effective_scope(e, None) == "item", "whole-file mode reads every contradiction as item"
        # review F1: a hyphenated extension is a different item; a criterion suffix is the same one
        ext = {**among["contradictions"][0], "requirements": ["Offline first", "R-001-extra.1"]}
        assert effective_scope(ext, "R-001") == "constraints" and effective_scope({**ext, "requirements": ["R-001.2"]}, "R-001") == "item"
        cmd_run(doc, ["R-001"], post=stub_post({"contradictions": [ext], "ambiguities": []}))
        ok, why = check(doc, ["R-001"])
        assert ok and "R-001 C1 (Offline first, R-001-extra.1)" in why, why
        with contextlib.redirect_stdout(io.StringIO()) as out:   # review F2: no subcommand prints help, exit 1
            assert main([]) == 1 and "usage:" in out.getvalue()
        with contextlib.redirect_stderr(io.StringIO()) as err:
            assert main(["run", str(doc), "--constraints", "--items", "R-001"]) == 1 and "takes no --items" in err.getvalue()
        cpath.unlink(); cpath.with_suffix(".md").unlink()
        # review F3: malformed findings refuse, in the reply and in a record read back
        for block in ('{"error": "unable"}', '{"contradictions": null, "ambiguities": []}',
                      '{"contradictions": [{"id": "C1"}], "ambiguities": []}'):
            try:
                findings(f"```json\n{block}\n```")
                raise AssertionError(f"accepted {block}")
            except Refused as e:
                assert "malformed" in str(e)
        # a table-row item (the template's format): header kept, Status and Review ID cells blanked
        table = DEMO.split("## Items")[0] + TABLE
        name, sent = scope(table, "T-001")
        assert name == "T-001" and "| ID | Item |" in sent and "Works offline" in sent and "Offline first" in sent
        assert "T-002" not in sent and "planned" not in sent and "PR #9" not in sent, sent
        moved = table.replace("| planned | PR #9 |", "| done | PR #10 |")
        assert scope(moved, "T-001") == (name, sent), "a status or merge cell made the scope differ"
        assert scope(table, "T-001")[1] != scope(table.replace("Works offline", "Works online"), "T-001")[1]
        # whole-file mode makes the same promise: no status line and no status cell counts
        assert scope(moved)[1] == scope(table)[1] and "planned" not in scope(table)[1] and "| T-002 |" in scope(table)[1]
        assert scope(DEMO.replace("planned", "done"))[1] == scope(DEMO)[1]
        # one record per item: a batch passes when each item does, in any order
        doc.write_text(table)
        assert cmd_run(doc, ["T-002", "T-001"], post=stub_post({"contradictions": [], "ambiguities": []})) == 0
        assert check(doc, ["T-001", "T-002"])[0] and check(doc, ["T-002"])[0]
        assert record_path(doc, "T-001").exists() and record_path(doc, "T-002").exists()
        # review F4: check reports ambiguities and still passes
        cmd_run(doc, ["T-002"], post=stub_post({"contradictions": [], "ambiguities": [
            {"id": "A1", "requirements": ["T-002.1"], "question": "Unrelated to what?"}]}))
        ok, why = check(doc, ["T-001", "T-002"])
        assert ok and "1 open ambiguity, not blocking" in why and "T-002 A1 (T-002.1): Unrelated to what?" in why, why
        # review F3: a malformed record read back doesn't pass
        good = record_path(doc, "T-002").read_text()
        record_path(doc, "T-002").write_text(json.dumps({**json.loads(good), "contradictions": None}))
        assert "is malformed (contradictions is not a list)" in check(doc, ["T-002"])[1]
        record_path(doc, "T-002").write_text(good)
        # a turn that never consults the advisor writes no record, and a record without one doesn't pass
        record_path(doc, "T-001").unlink()
        s = stub_post({"contradictions": [], "ambiguities": []}, advise=False)
        try:
            cmd_run(doc, ["T-001"], post=s)
            raise AssertionError("an unadvised run was accepted")
        except Refused as e:
            assert "without consulting the advisor" in str(e) and not record_path(doc, "T-001").exists()
            assert len(s.seen) == 2 and s.seen[1]["messages"][-1]["content"] == REMINDER, "one reminder, then refuse"
        late = stub_post({"contradictions": [], "ambiguities": []})
        skip_once = lambda req: ({"stop_reason": "end_turn", "content": [{"type": "text", "text": "no json yet"}]}
                                 if len(req["messages"]) == 1 else late(req))
        assert cmd_run(doc, ["T-001"], post=skip_once) == 0, "a consult after the reminder counts"
        assert json.loads(record_path(doc, "T-001").read_text())["advisor_calls"] == 1
        nul = json.loads(record_path(doc, "T-001").read_text())   # the stub sends no cache fields
        assert nul["cache"] is None and "lacked" in nul["cache_reason"], nul
        cmd_run(doc, ["T-001"], post=stub_post({"contradictions": [], "ambiguities": []}))
        rec = json.loads(record_path(doc, "T-001").read_text()); rec["advisor_calls"] = 0
        record_path(doc, "T-001").write_text(json.dumps(rec))
        assert "records no advisor call" in check(doc, ["T-001"])[1]
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
            assert api_key() == "k1" and "anthropic-workspace-id" not in headers()
            (Path(d) / "ok.env").write_text('ANTHROPIC_API_KEY=k1\nANTHROPIC_WORKSPACE_ID=wrkspc_1\n')
            assert headers()["anthropic-workspace-id"] == "wrkspc_1"
            assert_api_error_is_refused()
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
        sp.add_argument("--constraints", action="store_true")
        if c == "run":
            sp.add_argument("--ledger")
    bp = sub.add_parser("budget")
    bp.add_argument("action", choices=("init", "show"))
    bp.add_argument("--stop-usd")
    bp.add_argument("--ledger")
    sp = sub.add_parser("dispose")
    sp.add_argument("doc")
    sp.add_argument("--items", type=lambda s: [x.strip() for x in s.split(",") if x.strip()])
    sp.add_argument("--constraints", action="store_true")
    sp.add_argument("--id", required=True)
    sp.add_argument("--by", required=True)
    sp.add_argument("--evidence", required=True)
    sp.add_argument("--disposition", default="disproved")
    argv = list(sys.argv[1:] if argv is None else argv)
    for i in range(len(argv) - 1):   # `--stop-usd -1` must reach budget_init's refusal, not argparse's
        if argv[i] == "--stop-usd":
            argv[i:i + 2] = [f"--stop-usd={argv[i + 1]}"]
            break
    a = p.parse_args(argv)
    if a.selftest:
        return selftest()
    try:
        if getattr(a, "constraints", False) and getattr(a, "items", None):   # review F2: no subcommand has neither
            raise Refused("--constraints reviews the constraints alone; it takes no --items")
        if a.cmd == "run":
            return cmd_run(a.doc, a.items, constraints=a.constraints, ledger=a.ledger)
        if a.cmd == "budget":
            if a.action == "init":
                if a.stop_usd is None:
                    raise Refused("budget init needs --stop-usd")
                budget_init(a.stop_usd, a.ledger)
            else:
                budget_show(a.ledger)
            return 0
        if a.cmd == "dispose":
            dispose(a.doc, a.id, a.by, a.evidence, a.items, a.constraints, a.disposition)
            return 0
        if a.cmd == "check":
            ok, reason = check(a.doc, a.items, constraints=a.constraints)
            print(reason)
            return 0 if ok else 2
    except Refused as e:
        print(f"refused: {e}", file=sys.stderr)
        return 1
    p.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main() or 0)
