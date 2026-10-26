"""Shared library for the mcp-demand-harness plugin.

Stdlib only. Every script in this plugin imports from here so the bank schema,
its validation rules, and the hashing that ties an export back to its source are
defined exactly once.

The bank is the one authored artifact. MCPJam suites, mcp-eval datasets and REST
probe plans are generated from it and are never edited by hand: an edit there is
lost on the next export and, worse, silently diverges from the evidence trail
that says why each question exists.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
from dataclasses import dataclass, field
from typing import Any, Iterable

PLUGIN_NAME = "mcp-demand-harness"
PLUGIN_VERSION = "0.1.0"
BANK_VERSION = 1

QUESTION_ID = re.compile(r"^Q-\d{4,}$")
PERSONA_ID = re.compile(r"^[a-z][a-z0-9-]*$")

# Evidence classes, strongest first. The class is the single most important
# field in the bank: it is what stops a model-written question from being read
# as proof that a customer wants something.
EVIDENCE_CLASSES = ("observed", "reported", "hypothesis", "generated")
EVIDENCE_MEANING = {
    "observed": "A real user's own words, captured by telemetry, support, or a session recording.",
    "reported": "A real user's need, relayed second-hand by a person (sales notes, CAB feedback, interviews).",
    "hypothesis": "Written by the team from personas and product knowledge. Not evidence of demand.",
    "generated": "Expanded by a model from a parent question. Weaker than its parent, never stronger.",
}

MODES = ("discovery", "strict")
KINDS = ("live", "composed", "boundary", "gap")
SURFACES = ("mcp", "rest")
STATUSES = ("active", "parked")
REVIEW_STATUSES = ("accepted", "draft")

PAYLOAD_KEYS = {"tool", "args", "must_contain", "must_not_match", "absence_acceptable"}
REST_KEYS = {"calls", "must_contain", "must_not_match", "absence_acceptable"}
REST_CALL_KEYS = {"method", "path", "query", "body"}

EXPECT_KEYS = {
    "first_tool_any_of",
    "must_call",
    "must_not_call",
    "must_contain",
    "must_not_match",
    "max_tool_calls",
    "must_refuse",
    "absence_acceptable",
    "rubric",
}

# Default cap on generated questions per persona, relative to that persona's
# non-generated questions. Keeps the bank from being mostly the model talking
# to itself.
DEFAULT_GENERATED_RATIO = 3.0


# --------------------------------------------------------------------- io


def load_json(path: str) -> Any:
    with open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)


def dump_json(obj: Any, path: str) -> None:
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(obj, fh, indent=2, ensure_ascii=False, sort_keys=False)
        fh.write("\n")


def sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return "sha256:" + h.hexdigest()


def sha256_text(text: str) -> str:
    return "sha256:" + hashlib.sha256(text.encode("utf-8")).hexdigest()


def empty_bank(product: str) -> dict:
    return {
        "bank_version": BANK_VERSION,
        "product": product,
        "generated_by": f"{PLUGIN_NAME} {PLUGIN_VERSION}",
        "personas": [],
        "questions": [],
    }


def next_question_id(bank: dict) -> str:
    nums = [int(q["id"][2:]) for q in bank.get("questions", []) if QUESTION_ID.match(q.get("id", ""))]
    return f"Q-{(max(nums) + 1) if nums else 1:04d}"


def normalise_text(text: str) -> str:
    """Key used to detect duplicate questions across sources."""
    t = text.lower()
    t = re.sub(r"[\u2018\u2019\u201c\u201d\"'`]", "", t)
    t = re.sub(r"[^a-z0-9]+", " ", t)
    return t.strip()


# ------------------------------------------------------------- validation


@dataclass
class Finding:
    level: str  # "error" | "warning"
    where: str
    message: str

    def __str__(self) -> str:
        return f"{self.level.upper():7} {self.where}: {self.message}"


@dataclass
class Report:
    findings: list[Finding] = field(default_factory=list)

    def error(self, where: str, msg: str) -> None:
        self.findings.append(Finding("error", where, msg))

    def warn(self, where: str, msg: str) -> None:
        self.findings.append(Finding("warning", where, msg))

    @property
    def errors(self) -> list[Finding]:
        return [f for f in self.findings if f.level == "error"]

    @property
    def ok(self) -> bool:
        return not self.errors


# Constructs that compile in Python but mean something else, or nothing, in
# JavaScript. MCPJam evaluates regex in JS; mcp-eval evaluates it in Python. A
# pattern has to mean the same thing in both or the two harnesses disagree about
# the same question.
_PY_ONLY = [
    (re.compile(r"\(\?P[<=]"), "named groups (?P<...>) are Python-only; use (?<name>...)"),
    (re.compile(r"\(\?[aiLmsux]+\)"), "inline flags like (?i) are applied by the exporter; do not write them"),
    (re.compile(r"\\[AZ]"), "\\A and \\Z are Python-only anchors; use ^ and $"),
    (re.compile(r"[*+?}][+]"), "possessive quantifiers are not portable"),
    (re.compile(r"\(\?>"), "atomic groups are not portable"),
]


def check_portable_regex(pattern: str) -> str | None:
    try:
        re.compile(pattern)
    except re.error as exc:
        return f"does not compile: {exc}"
    for rx, why in _PY_ONLY:
        if rx.search(pattern):
            return why
    return None


def _route_matcher(routes: Iterable[str] | None):
    if routes is None:
        return None
    rx = [re.compile("^" + re.sub(r"\\\{[^}]*\\\}", "[^/]+", re.escape(r)) + "$") for r in routes]
    return lambda path: any(x.match(path.split("?")[0]) for x in rx)


def validate_bank(bank: dict, tool_names: Iterable[str] | None = None, generated_ratio: float = DEFAULT_GENERATED_RATIO, for_export: bool = False, routes: Iterable[str] | None = None) -> Report:
    """Machine-checkable rules for a bank.

    `tool_names`, when given, is the live tool surface from the capability map.
    A strict question that expects a tool the server does not register would
    otherwise pass vacuously forever in any harness that only checks for absence
    of the wrong tool.

    `for_export` promotes the release gate on observed evidence from a warning
    to an error, because an export is the step that puts user words into a file
    that leaves the machine.
    """
    r = Report()
    tools = set(tool_names) if tool_names is not None else None
    route_ok = _route_matcher(routes)

    if bank.get("bank_version") != BANK_VERSION:
        r.error("bank", f"bank_version must be {BANK_VERSION}")
    if not bank.get("product"):
        r.error("bank", "product is required")

    personas = bank.get("personas") or []
    persona_ids = set()
    for i, p in enumerate(personas):
        pid = p.get("id", "")
        if not PERSONA_ID.match(pid):
            r.error(f"personas[{i}]", f"id {pid!r} must be lowercase kebab-case")
        if pid in persona_ids:
            r.error(f"personas[{i}]", f"duplicate persona id {pid}")
        persona_ids.add(pid)
        if not p.get("name"):
            r.error(f"personas[{pid}]", "name is required")
        if not p.get("source"):
            r.error(f"personas[{pid}]", "source is required: a persona nobody can trace is a guess")

    questions = bank.get("questions") or []
    by_id: dict[str, dict] = {}
    seen_text: dict[str, str] = {}
    for q in questions:
        qid = q.get("id", "")
        where = qid or "questions[?]"
        if not QUESTION_ID.match(qid):
            r.error(where, "id must look like Q-0001")
        if qid in by_id:
            r.error(where, "duplicate id")
        by_id[qid] = q

        text = (q.get("text") or "").strip()
        if not text:
            r.error(where, "text is required")
        elif len(text) > 2000:
            r.error(where, "text is longer than 2000 characters")
        else:
            key = normalise_text(text)
            if key in seen_text:
                r.warn(where, f"duplicates {seen_text[key]} after normalisation")
            else:
                seen_text[key] = qid

        for t in q.get("turns") or []:
            if not isinstance(t, str) or not t.strip():
                r.error(where, "turns must be non-empty strings")

        if q.get("persona") not in persona_ids:
            r.error(where, f"persona {q.get('persona')!r} is not declared in personas")

        mode = q.get("mode")
        if mode not in MODES:
            r.error(where, f"mode must be one of {MODES}")
        if q.get("kind") not in KINDS:
            r.error(where, f"kind must be one of {KINDS}")
        if q.get("status", "active") not in STATUSES:
            r.error(where, f"status must be one of {STATUSES}")
        surfaces = q.get("surfaces") or []
        if not surfaces or any(s not in SURFACES for s in surfaces):
            r.error(where, f"surfaces must be a non-empty subset of {SURFACES}")
        prio = q.get("priority", 2)
        if prio not in (1, 2, 3):
            r.error(where, "priority must be 1, 2 or 3")

        ev = q.get("evidence") or {}
        cls = ev.get("class")
        if cls not in EVIDENCE_CLASSES:
            r.error(where, f"evidence.class must be one of {EVIDENCE_CLASSES}")
        if not ev.get("source"):
            r.error(where, "evidence.source is required")
        if cls == "observed":
            if ev.get("redacted") is not True:
                r.error(where, "observed evidence must be redacted (evidence.redacted: true) before it enters the bank")
            if not ev.get("release_approved_by"):
                (r.error if for_export else r.warn)(
                    where,
                    "observed evidence has no evidence.release_approved_by; a named person must approve user words leaving the machine",
                )

        exp = q.get("expect") or {}
        unknown = set(exp) - EXPECT_KEYS
        if unknown:
            r.error(where, f"unknown expect keys {sorted(unknown)}")

        tool_lists = [exp.get(k) or [] for k in ("first_tool_any_of", "must_call", "must_not_call")]
        for lst in tool_lists:
            if not isinstance(lst, list):
                r.error(where, "tool expectations must be lists")
                continue
            if tools is not None:
                for name in lst:
                    if name not in tools:
                        r.error(where, f"expects tool {name!r}, which the capability map does not register")

        for s in exp.get("must_contain") or []:
            if not isinstance(s, str) or not s.strip():
                r.error(where, "must_contain entries must be non-empty strings")
        _check_patterns(r, where, "expect.must_not_match", exp.get("must_not_match"))

        payload = q.get("payload")
        if payload is not None:
            bad = set(payload) - PAYLOAD_KEYS
            if bad:
                r.error(where, f"unknown payload keys {sorted(bad)}")
            if not payload.get("tool"):
                r.error(where, "payload.tool is required: a payload check is a direct call to one tool")
            elif tools is not None and payload["tool"] not in tools:
                r.error(where, f"payload.tool {payload['tool']!r} is not registered")
            if not isinstance(payload.get("args", {}), dict):
                r.error(where, "payload.args must be an object")
            _check_patterns(r, where, "payload.must_not_match", payload.get("must_not_match"))

        rest = q.get("rest")
        if rest is not None:
            bad = set(rest) - REST_KEYS
            if bad:
                r.error(where, f"unknown rest keys {sorted(bad)}")
            calls = rest.get("calls") or []
            if not calls:
                r.error(where, "rest.calls must list at least one call")
            for c in calls:
                if set(c) - REST_CALL_KEYS:
                    r.error(where, f"rest call keys must be within {sorted(REST_CALL_KEYS)}")
                if c.get("method", "GET") not in ("GET", "POST", "PUT", "PATCH", "DELETE"):
                    r.error(where, "rest call method is not an HTTP method")
                if c.get("method", "GET") in ("PUT", "PATCH", "DELETE"):
                    r.error(where, "rest calls must be read-only; PUT/PATCH/DELETE would change customer or product state")
                path = c.get("path") or ""
                if not path.startswith("/"):
                    r.error(where, "rest call path must start with /")
                elif route_ok is not None and not route_ok(path):
                    r.error(where, f"rest call path {path} matches no route in the capability map")
            _check_patterns(r, where, "rest.must_not_match", rest.get("must_not_match"))
            if "rest" not in (q.get("surfaces") or []):
                r.error(where, "a question with rest.calls must list rest in surfaces")

        if q.get("review_status", "accepted") not in REVIEW_STATUSES:
            r.error(where, f"review_status must be one of {REVIEW_STATUSES}")
        if q.get("review_status") == "draft" and not ev.get("authored_by"):
            r.error(where, "a draft question must record evidence.authored_by")
        for need in q.get("requires_input") or []:
            if not isinstance(need, str) or not need:
                r.error(where, "requires_input entries must be non-empty strings")

        mtc = exp.get("max_tool_calls")
        if mtc is not None and (not isinstance(mtc, int) or mtc < 1):
            r.error(where, "max_tool_calls must be a positive integer")

        if exp.get("must_refuse") and not exp.get("rubric"):
            r.error(where, "must_refuse needs a rubric saying what a correct refusal looks like")

        deterministic = any(exp.get(k) for k in ("first_tool_any_of", "must_call", "must_not_call", "must_contain", "must_not_match", "max_tool_calls")) or bool(q.get("payload")) or bool(q.get("rest"))
        if mode == "strict":
            if not deterministic and not exp.get("rubric"):
                r.error(where, "a strict question needs at least one expectation")
            if not (q.get("why") or "").strip():
                r.error(where, "a strict question must say what a failure would mean (why)")
        if mode == "discovery":
            if exp.get("first_tool_any_of") or exp.get("must_call"):
                r.error(where, "discovery questions do not name expected tools; discovering them is the point")

    # Second pass: lineage.
    for q in questions:
        ev = q.get("evidence") or {}
        if ev.get("class") != "generated":
            continue
        parent = ev.get("parent")
        if not parent:
            r.error(q.get("id", "?"), "generated questions must name a parent")
            continue
        p = by_id.get(parent)
        if p is None:
            r.error(q["id"], f"parent {parent} does not exist")
        elif (p.get("evidence") or {}).get("class") == "generated":
            r.error(q["id"], f"parent {parent} is itself generated; expand from evidence, not from expansions")
        elif p.get("persona") != q.get("persona"):
            r.warn(q["id"], f"persona differs from parent {parent}")

    # Ratio cap per persona.
    counts: dict[str, list[int]] = {}
    for q in questions:
        pc = counts.setdefault(q.get("persona", "?"), [0, 0])
        if (q.get("evidence") or {}).get("class") == "generated":
            pc[1] += 1
        else:
            pc[0] += 1
    for pid, (seeds, gen) in counts.items():
        if gen and gen > generated_ratio * max(seeds, 0):
            r.error(f"persona {pid}", f"{gen} generated vs {seeds} seed questions exceeds the {generated_ratio:g}x cap")

    return r


def pattern_parts(entry) -> tuple[str, bool]:
    """(pattern, case_sensitive). A bare string is case-insensitive."""
    if isinstance(entry, str):
        return entry, False
    return entry.get("pattern", ""), bool(entry.get("case_sensitive", False))


def _check_patterns(r: "Report", where: str, label: str, entries) -> None:
    for entry in entries or []:
        if isinstance(entry, dict):
            if set(entry) - {"pattern", "case_sensitive"} or not isinstance(entry.get("pattern"), str):
                r.error(where, f"{label} objects take only pattern and case_sensitive")
                continue
        elif not isinstance(entry, str):
            r.error(where, f"{label} entries must be strings or {{pattern, case_sensitive}}")
            continue
        pat, _ = pattern_parts(entry)
        why = check_portable_regex(pat)
        if why:
            r.error(where, f"{label} {pat!r}: {why}")


def runnable(q: dict, include_drafts: bool = False) -> tuple[bool, str]:
    """Can this question be sent to a harness as written? (ok, reason-if-not)."""
    if q.get("status", "active") != "active":
        return False, "parked"
    if q.get("review_status") == "draft" and not include_drafts:
        return False, "draft awaiting human review"
    if q.get("requires_input"):
        return False, "needs customer input it does not carry: " + ", ".join(q["requires_input"])
    return True, ""


def bank_stats(bank: dict) -> dict:
    qs = [q for q in bank.get("questions", []) if q.get("status", "active") == "active"]
    by = lambda key: _count(qs, key)  # noqa: E731
    return {
        "active_questions": len(qs),
        "parked_questions": len(bank.get("questions", [])) - len(qs),
        "by_evidence_class": _count(qs, lambda q: (q.get("evidence") or {}).get("class")),
        "by_persona": by(lambda q: q.get("persona")),
        "by_mode": by(lambda q: q.get("mode")),
        "by_kind": by(lambda q: q.get("kind")),
        "by_surface": _count([s for q in qs for s in q.get("surfaces", [])], lambda s: s),
        "runnable": sum(1 for q in qs if runnable(q)[0]),
        "blocked_by_input": sum(1 for q in qs if q.get("requires_input")),
        "drafts": sum(1 for q in qs if q.get("review_status") == "draft"),
        "personas_without_evidence": sorted(
            p["id"] for p in bank.get("personas", [])
            if not any(q.get("persona") == p["id"] and (q.get("evidence") or {}).get("class") in ("observed", "reported") for q in qs)
        ),
        "personas_without_questions": sorted(
            p["id"] for p in bank.get("personas", []) if not any(q.get("persona") == p["id"] for q in qs)
        ),
    }


def _count(items, keyfn) -> dict:
    out: dict[str, int] = {}
    for it in items:
        k = keyfn(it)
        out[str(k)] = out.get(str(k), 0) + 1
    return dict(sorted(out.items()))


# ------------------------------------------------------------ regex utils


def js_case_fold(pattern: str) -> str:
    """Make a regex case-insensitive without flags.

    MCPJam's `responseMatches` takes "regex source, no flags", so the bank's
    case-insensitive semantics have to be spelled into the pattern. Each ASCII
    letter outside an escape becomes [xX]; inside a character class both cases
    are added. Escapes like \\b, \\d, \\s and \\w are left alone, which is the
    whole reason this is a parser and not a .lower().
    """
    out: list[str] = []
    i = 0
    in_class = False
    n = len(pattern)
    while i < n:
        c = pattern[i]
        if c == "\\" and i + 1 < n:
            out.append(pattern[i : i + 2])
            i += 2
            continue
        if in_class:
            if c == "]":
                in_class = False
                out.append(c)
            elif c.isascii() and c.isalpha():
                # Ranges like a-z: add the other-case range once.
                if i + 2 < n and pattern[i + 1] == "-" and pattern[i + 2].isascii() and pattern[i + 2].isalpha():
                    lo, hi = c, pattern[i + 2]
                    out.append(f"{lo}-{hi}{lo.swapcase()}-{hi.swapcase()}")
                    i += 3
                    continue
                out.append(c + c.swapcase())
            else:
                out.append(c)
            i += 1
            continue
        if c == "[":
            in_class = True
            out.append(c)
            if i + 1 < n and pattern[i + 1] == "^":
                out.append("^")
                i += 1
            i += 1
            continue
        if c == "(" and pattern.startswith("(?", i):
            # Group syntax: (?: (?= (?! (?<= (?<! (?<name>
            m = re.match(r"\(\?(?:[:=!]|<[=!]|<[A-Za-z_][A-Za-z0-9_]*>)", pattern[i:])
            if m:
                out.append(m.group(0))
                i += len(m.group(0))
                continue
        if c == "{":
            j = pattern.find("}", i)
            if j != -1 and re.fullmatch(r"\{\d+(,\d*)?\}", pattern[i : j + 1]):
                out.append(pattern[i : j + 1])
                i = j + 1
                continue
        if c.isascii() and c.isalpha():
            out.append(f"[{c.lower()}{c.upper()}]")
        else:
            out.append(c)
        i += 1
    return "".join(out)


def negative_whole_response(pattern: str) -> str:
    """A pattern that matches a response only if `pattern` occurs nowhere in it.

    Used where a harness has a positive regex predicate but no negative one.
    [\\s\\S] instead of . so a multi-line answer is covered without the s flag.
    """
    return r"^(?![\s\S]*(?:" + pattern + r"))[\s\S]*$"


# ----------------------------------------------------------------- yaml


def yaml_scalar(value: Any) -> str:
    """Emit a scalar as YAML.

    YAML 1.2 is a superset of JSON, so a JSON-encoded scalar is a valid YAML
    scalar with the same value. That keeps this emitter honest without a YAML
    dependency: strings are always double-quoted JSON strings.
    """
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return json.dumps(value)
    return json.dumps(str(value), ensure_ascii=False)


def to_yaml(obj: Any, indent: int = 0) -> str:
    pad = "  " * indent
    if isinstance(obj, dict):
        if not obj:
            return "{}"
        lines = []
        for k, v in obj.items():
            key = k if re.fullmatch(r"[A-Za-z_$][A-Za-z0-9_$-]*", k) else json.dumps(k)
            if isinstance(v, (dict, list)) and v:
                lines.append(f"{pad}{key}:")
                lines.append(to_yaml(v, indent + 1))
            else:
                lines.append(f"{pad}{key}: {to_yaml(v, 0) if isinstance(v, (dict, list)) else yaml_scalar(v)}")
        return "\n".join(lines)
    if isinstance(obj, list):
        if not obj:
            return "[]"
        lines = []
        for v in obj:
            if isinstance(v, dict) and v:
                inner = to_yaml(v, indent + 1).split("\n")
                first = inner[0][len("  " * (indent + 1)) :]
                lines.append(f"{pad}- {first}")
                lines.extend(inner[1:])
            elif isinstance(v, list) and v:
                lines.append(f"{pad}-")
                lines.append(to_yaml(v, indent + 1))
            else:
                lines.append(f"{pad}- {to_yaml(v, 0) if isinstance(v, (dict, list)) else yaml_scalar(v)}")
        return "\n".join(lines)
    return yaml_scalar(obj)


def write_yaml(obj: Any, path: str, header: str = "") -> None:
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        if header:
            for line in header.strip().splitlines():
                fh.write(f"# {line}".rstrip() + "\n")
        fh.write(to_yaml(obj))
        fh.write("\n")


# --------------------------------------------------------------- profile


def load_profile(path: str | None) -> dict:
    if not path:
        return {}
    return load_json(path)


def active_questions(bank: dict, surface: str | None = None) -> list[dict]:
    out = []
    for q in bank.get("questions", []):
        if q.get("status", "active") != "active":
            continue
        if surface and surface not in (q.get("surfaces") or []):
            continue
        out.append(q)
    return out


def named_person(name: str | None) -> bool:
    """A named human: at least a first and last name. Rejects blanks, "claude",
    "the team", "owner" and other stand-ins (conformance Test 2)."""
    if not name:
        return False
    parts = name.strip().split()
    stand_ins = {"claude", "agent", "team", "owner", "user", "admin", "the", "bot", "ai"}
    return len(parts) >= 2 and not any(x.lower() in stand_ins for x in parts)
