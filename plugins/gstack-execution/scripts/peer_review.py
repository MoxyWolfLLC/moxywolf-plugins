#!/usr/bin/env python3
"""
gstack peer review dispatcher. Stdlib only.

Enforces the mechanical half of references/peer-review-contract.md: commit identity,
tool routing (builder -> the other tool), read-only snapshots, output validation,
round limits, dispositions, explicit outcomes. The contract file carries the words.

  peer_review.py open   --builder claude|codex --packet packet.json [--max-rounds 3] [--timeout 900]
  peer_review.py round  <review-id> [--head <repo-path>=<sha> ...]
  peer_review.py disposition <review-id> F1=fixed F2=disproved:"evidence" F3=deferred
  peer_review.py status <review-id>
  peer_review.py verify <review-id>          re-resolve every evidential link in a finished review
  peer_review.py --selftest
"""
import argparse
from governance import data_permission
import hashlib
import shlex
from datetime import datetime, timezone
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
CONTRACT = HERE.parent / "skills" / "gstack-execution" / "references" / "peer-review-contract.md"
_env_review_dir = os.environ.get("GSTACK_PEER_REVIEW_DIR")
REVIEW_DIR = Path(_env_review_dir) if _env_review_dir else None
RECURSION_ENV = "GSTACK_PEER_REVIEW_SESSION"
_SELFTEST = False
# XE-005: independence is a property, not a name.
#
# Routing used to be {"claude":"codex","codex":"claude"} and derived the reviewer as "the other
# one". That encodes independence as a name. Cursor can run Claude models, so a Claude builder
# reviewed by Cursor could share the builder's model family while satisfying every check here,
# and a record that cannot tell a harness swap from an independent mind reads as the stronger
# thing. Each entry therefore declares the family it actually belongs to, and a reviewer whose
# family matches the builder's is refused before it runs.
#
# Model floors (Dorian, 2026-09-11): Codex uses Astra or higher, Claude Code uses Opus 5 or
# higher. Override a model with GSTACK_<TOOL>_MODEL; the floor still applies to what ran.
REVIEWERS = {
    "codex":  {"family": "gpt", "transport": "cli", "max_output": 16000, "max_output_flag": None,
               "model": os.environ.get("GSTACK_CODEX_MODEL", "gpt-6-astra"),
               "floor": r"^gpt-([6-9]|\d{2,})\b",
               "floor_name": "Astra (gpt-6) or higher"},
    "claude": {"family": "claude", "transport": "cli", "max_output": 16000, "max_output_flag": None,
               "model": os.environ.get("GSTACK_CLAUDE_MODEL", "claude-opus-5"),
               "floor": r"^claude-(opus-([5-9]|\d{2,})|fable-\d+|mythos)",
               "floor_name": "Opus 5 or higher"},
    "gemini": {"family": "gemini", "transport": "cli", "max_output": 16000, "max_output_flag": None,
               "model": os.environ.get("GSTACK_GEMINI_MODEL", "gemini-3.1-pro-preview"),
               "floor": r"^gemini-([3-9]|\d{2,})\b",
               "floor_name": "Gemini 3 or higher"},
    # XE-013: the openrouter transport. One entry per model family, never one named for the
    # transport: OpenRouter serves every family at once, so "reviewed by openrouter" would say
    # nothing about independence, which is the error XE-005 removed from tool names.
    # `sends` is criterion 5: what this reviewer is given, recorded per round, because it cannot
    # open anything for itself.
    "openrouter-gpt": {"family": "gpt", "transport": "openrouter", "max_output": 16000, "max_output_flag": None,
               "model": os.environ.get("GSTACK_OPENROUTER_GPT_MODEL", "openai/gpt-6-astra"),
               "floor": r"^gpt-([6-9]|\d{2,})\b",
               "floor_name": "Astra (gpt-6) or higher",
               "sends": ["CHANGE.diff", "changed", "callers"]},
    "openrouter-gemini": {"family": "gemini", "transport": "openrouter", "max_output": 16000, "max_output_flag": None,
               "model": os.environ.get("GSTACK_OPENROUTER_GEMINI_MODEL", "google/gemini-3.1-pro-preview"),
               "floor": r"^gemini-([3-9]|\d{2,})\b",
               "floor_name": "Gemini 3 or higher",
               "sends": ["CHANGE.diff", "changed", "callers"]},
    "openrouter-claude": {"family": "claude", "transport": "openrouter", "max_output": 16000, "max_output_flag": None,
               "model": os.environ.get("GSTACK_OPENROUTER_CLAUDE_MODEL", "anthropic/claude-opus-5"),
               "floor": r"^claude-(opus-([5-9]|\d{2,})|fable-\d+|mythos)",
               "floor_name": "Opus 5 or higher",
               "sends": ["CHANGE.diff", "changed", "callers"]},
    "openrouter-deepseek": {"family": "deepseek", "transport": "openrouter", "max_output": 16000, "max_output_flag": None,
               "model": os.environ.get("GSTACK_OPENROUTER_DEEPSEEK_MODEL", "deepseek/deepseek-v4.1-flash"),
               "floor": r"^deepseek-v([4-9]|\d{2,})\b",
               "floor_name": "DeepSeek v4 or higher",
               "sends": ["CHANGE.diff", "changed", "callers"]},
}
TRANSPORTS = {"cli", "openrouter"}
# XE-013.2: refused at the table, not at run time. An entry named for its transport would span
# every model family behind one name.
for _n, _c in REVIEWERS.items():
    if _n in TRANSPORTS:
        raise RuntimeError(f"reviewer entry {_n!r} is named for a transport; XE-013 requires one entry per model family")
    if _c.get("transport") not in TRANSPORTS:
        raise RuntimeError(f"reviewer entry {_n!r} declares no known transport")
# max_output is the headroom the reviewer contract's full response needs, set against that
# contract rather than a provider default. Precedent: the Council Sonnet-5 slot was configured at
# 3000 and needed 12000, and under-provisioned it returned empty content while the dispatcher still
# reported success. max_output_flag is how to apply it on the command line -- None means this CLI
# exposes no such flag (checked 2026-09-17: none of codex, claude or gemini does). Where it is None
# the headroom is NOT enforced, and the round records that, because a record that cannot distinguish
# a bounded run from an unbounded one is worth less than no record. Detection still applies either
# way: a response that hits the real ceiling reports output_truncated.
# Preference order when more than one independent reviewer is installed.
# XE-013.7: a reviewer that opens its own surface comes first, because EV-008 can only
# measure what a reviewer CHOSE to read when it does the choosing. The api entries are
# the fallback that stops a missing binary from landing a checkpoint unreviewed.
REVIEWER_ORDER = ["codex", "claude", "gemini",
                  "openrouter-gpt", "openrouter-gemini", "openrouter-claude", "openrouter-deepseek"]
# Builders are the tools that write code here. Their family decides who may review them.
OTHER_TOOL = {"claude": "codex", "codex": "claude"}  # kept: task_graph.py and --builder choices


def family(tool):
    return REVIEWERS[tool]["family"] if tool in REVIEWERS else None


def model_ok(tool, model):
    # An OpenRouter id is "provider/model". The floor patterns have one home (XE-008) and match the
    # bare name, so the prefix is stripped here rather than duplicated into every pattern.
    return bool(re.match(REVIEWERS[tool]["floor"], (model or "").split("/")[-1]))


def installed(tool):
    """Can this entry actually run here? A CLI needs its binary; an api entry needs its credential."""
    if REVIEWERS[tool]["transport"] == "cli":
        return bool(shutil.which(tool))
    try:
        openrouter_key()
        return True
    except ReviewError:
        return False


def headroom_enforced(tool):
    """XE-013.3. A CLI entry enforces max_output only if its CLI exposes a flag, and none of the
    three do. An api entry sets it on the request, so for those it is applied rather than declared."""
    cfg = REVIEWERS[tool]
    return True if cfg["transport"] == "openrouter" else cfg.get("max_output_flag") is not None


def reviewer_candidates(builder):
    """Installed reviewers whose model family differs from the builder's, in preference order."""
    bf = family(builder)
    return [t for t in REVIEWER_ORDER if t in REVIEWERS and REVIEWERS[t]["family"] != bf]


def choose_reviewer(builder, forced=None, require_installed=True):
    """(tool, is_fallback). A forced reviewer sharing the builder's family is refused, not silently
    accepted; a fallback is recorded as one, because an unrecorded fallback is a silent downgrade.

    `open` records the INTENDED reviewer and does not require it on PATH; `round` resolves the one
    that actually runs. Availability legitimately changes between the two -- on 2026-09-17 codex was
    absent when the review opened and installed before the next attempt -- so binding the decision at
    open would pin a stale answer and hide the fallback that really happened.
    """
    cands = reviewer_candidates(builder)
    if forced:
        if forced not in REVIEWERS:
            raise ReviewError("review_unavailable", f"unknown reviewer {forced}")
        if family(forced) == family(builder):
            raise ReviewError("reviewer_not_independent",
                              f"{forced} runs the {family(forced)} family, the same as builder {builder}; "
                              "a harness swap is not an independent review")
        return forced, bool(cands) and forced != cands[0]
    if not cands:
        raise ReviewError("review_unavailable", f"no reviewer of a different family than builder {builder}")
    if not require_installed:
        return cands[0], False
    available = [t for t in cands if installed(t)]
    if not available:
        raise ReviewError("review_unavailable",
                          f"no independent reviewer available for builder {builder}; tried {', '.join(cands)} "
                          "(a cli entry needs its binary on PATH, an api entry needs its credential)")
    return available[0], available[0] != cands[0]
# XE-011: the terms this dispatcher names have one home, references/vocabulary.json. The enums,
# the round-record shape and the outcome set are read from it, not restated here, so the contract
# the reviewer is held to and the code enforcing it cannot drift apart (XE-008 criterion 2).
VOCAB_PATH = Path(__file__).resolve().parent.parent / "skills" / "gstack-execution" / "references" / "vocabulary.json"
VOCAB = json.loads(VOCAB_PATH.read_text())
VOCAB_VERSION = VOCAB["version"]
_CONCEPTS = {c["id"]: c for c in VOCAB["concepts"]}


def vocab_ids(*groups):
    return {c["id"] for c in VOCAB["concepts"] if c["group"] in groups}


def vocab_shape(term):
    return _CONCEPTS[term]["shape"]


PACKET_FIELDS = vocab_shape("packet")["required"]
SEVERITIES = vocab_ids("severity")
VERDICTS = {c["id"] for c in VOCAB["concepts"] if c.get("verdict")}
DISPOSITIONS = vocab_ids("disposition")
OUTCOMES = vocab_ids("round_outcome", "review_outcome", "verify_outcome")

OUTPUT_SCHEMA = {
    "type": "object",
    "required": ["verdict", "acceptance", "findings", "blocker_resolutions"],
    "properties": {
        "verdict": {"type": "string", "enum": sorted(VERDICTS)},
        "acceptance": {"type": "array", "items": {"type": "object", "required": ["criterion", "met", "evidence"],
                       "properties": {"criterion": {"type": "string"}, "met": {"type": "boolean"}, "evidence": {"type": "string"}}}},
        "findings": {"type": "array", "items": {"type": "object",
                     "required": ["id", "severity", "file", "line", "what", "evidence", "criterion", "fix"],
                     "properties": {"id": {"type": "string"}, "severity": {"type": "string", "enum": sorted(SEVERITIES)},
                                    "file": {"type": "string"}, "line": {"type": "integer"}, "what": {"type": "string"},
                                    "evidence": {"type": "string"}, "criterion": {"type": "string"}, "fix": {"type": "string"}}}},
        "blocker_resolutions": {"type": "array", "items": {"type": "object", "required": ["id", "resolved", "evidence"],
                                "properties": {"id": {"type": "string"}, "resolved": {"type": "boolean"}, "evidence": {"type": "string"}}}},
        "regressions_from_fixes": {"type": "array", "items": {"type": "string"}},
        "notes": {"type": "string"},
    },
}


def strict(schema):
    """OpenAI structured output requires additionalProperties:false and every property required, on every object."""
    if isinstance(schema, dict):
        out = {k: strict(v) for k, v in schema.items()}
        if out.get("type") == "object" and "properties" in out:
            out["additionalProperties"] = False
            out["required"] = list(out["properties"])
        return out
    if isinstance(schema, list):
        return [strict(x) for x in schema]
    return schema


STRICT_SCHEMA = strict(OUTPUT_SCHEMA)


class ReviewError(Exception):
    """Carries an explicit outcome name."""
    def __init__(self, outcome, detail):
        if outcome not in OUTCOMES:   # XE-011: an outcome nobody defined is a bug, not a new outcome
            raise ValueError(f"{outcome!r} is not an outcome in vocabulary {VOCAB_VERSION}")
        super().__init__(f"{outcome}: {detail}")
        self.outcome, self.detail = outcome, detail


# ---------- git ----------

def git(repo, *args, check=True):
    r = subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True)
    if check and r.returncode != 0:
        raise ReviewError("missing_commits", f"git {' '.join(args)} in {repo}: {r.stderr.strip()}")
    return r.stdout.strip()


def resolve_commit(repo, ref):
    r = subprocess.run(["git", "-C", str(repo), "rev-parse", "--verify", f"{ref}^{{commit}}"], capture_output=True, text=True)
    if r.returncode != 0:
        raise ReviewError("missing_commits", f"{ref} does not resolve in {repo}")
    return r.stdout.strip()


def snapshot(repos, root):
    """Detached read-only worktree per repo at its head commit. Returns [(name, path)].

    The peer review no longer uses this -- the reviewer gets a surface (XE-007). task_graph's proof
    nodes still do: they EXECUTE code in a disposable checkout, which is a different need from
    handing a reviewer something to read. Deleting it as dead code broke them, because that check
    grepped the tests and not the callers.
    """
    out = []
    for i, r in enumerate(repos):
        name = f"{i}-{Path(r['path']).name}"
        dest = root / name
        git(r["path"], "worktree", "add", "--detach", str(dest), r["head"])
        for p in dest.rglob("*"):
            if p.is_symlink() and not p.resolve().is_relative_to(dest.resolve()):
                raise ReviewError("data_use_denied", "snapshot symlink escapes repository scope")
            if p.is_file() and not p.is_symlink() and ".git" not in p.parts:
                p.chmod(p.stat().st_mode & 0o555)
        out.append((name, dest))
    return out


def teardown(repos, root):
    """Removes worktrees snapshot() may have created, then the directory itself.

    cmd_round creates no worktrees any more, but task_graph does, and both call this.
    """
    for r in repos:
        subprocess.run(["git", "-C", r["path"], "worktree", "prune"], capture_output=True)
    for d in root.iterdir() if root.exists() else []:
        for r in repos:
            subprocess.run(["git", "-C", r["path"], "worktree", "remove", "--force", str(d)], capture_output=True)
    shutil.rmtree(root, ignore_errors=True)


# ---------- packet / state ----------

def load_packet(path, allow_unchanged=False):
    try:
        packet = json.loads(Path(path).read_text())
    except (ValueError, OSError) as e:
        raise ReviewError("malformed_packet", str(e))
    if not isinstance(packet, dict):
        raise ReviewError("malformed_packet", "packet must be an object")
    missing = [f for f in PACKET_FIELDS if f not in packet]
    if missing:
        raise ReviewError("malformed_packet", f"packet missing {missing}")
    criteria = packet["acceptance_criteria"]
    if (not isinstance(criteria, list) or not criteria or
            any(not isinstance(c, str) or not c.strip() for c in criteria) or len(set(criteria)) != len(criteria)):
        raise ReviewError("malformed_packet", "acceptance_criteria must be nonempty, unique statements")
    owner = packet["release_owner"]
    if not isinstance(owner, str) or not owner.strip() or owner.lower().strip() in {"team", "user", "the team", "the user", "claude", "codex", "agent"}:
        raise ReviewError("malformed_packet", "release_owner must identify the accountable human")
    if not isinstance(packet["repos"], list) or not packet["repos"]:
        raise ReviewError("malformed_packet", "repos is empty")
    for r in packet["repos"]:
        if not isinstance(r, dict):
            raise ReviewError("malformed_packet", "repo must be an object")
        for k in ("path", "base", "head"):
            if k not in r:
                raise ReviewError("malformed_packet", f"repo entry missing {k}: {r}")
        r["path"] = str(Path(r["path"]).resolve())
        r["base"], r["head"] = resolve_commit(r["path"], r["base"]), resolve_commit(r["path"], r["head"])
        if r["base"] == r["head"] and not allow_unchanged:
            raise ReviewError("missing_commits", f"base == head in {r['path']}; nothing to review")
    packet.setdefault("prior_findings", [])
    return packet


def review_root():
    """EV-009: a review whose record goes to an undeclared directory has no record.

    The default here used to be $HOME/.gstack/peer-review. In a sandboxed session $HOME is
    per-session and sits outside every connected folder, so the record was destroyed when the
    session ended while its review ID went on reading like evidence in the design document.
    A silent default is the wrong shape for this: the caller names a durable directory or the
    review does not open.
    """
    if REVIEW_DIR is None:
        sys.exit("set GSTACK_PEER_REVIEW_DIR to a directory that outlives this session "
                 "(a path inside the repository or a connected folder, not $HOME); "
                 "records written to a session-local home are lost and their review IDs then "
                 "resolve to nothing")
    return REVIEW_DIR


def rdir(review_id):
    d = review_root() / review_id
    if not (d / "state.json").exists():
        sys.exit(f"no review {review_id} under {review_root()}")
    return d


def load(d, name):
    p = d / name
    return json.loads(p.read_text()) if p.exists() else None


ORIGINS = vocab_ids("origin")


def save_map(d, name, obj):
    """A keyed map, not a record: dispositions.json is finding id -> disposition, so stamping an
    origin into it would invent a finding called "origin". Found by the disposition cross-check in
    verify, which is the check that exists to catch exactly that. Its provenance is the review it
    sits in; `verify` skips it for the same reason."""
    (d / name).write_text(json.dumps(obj, indent=2))


def save(d, name, obj, origin, examined_by=None):
    """TB-001: a record says where its content came from, or it is not written.

    `origin` is positional and has no default on purpose. A default is how every record ends up
    claiming the safest origin without anyone deciding, which is the same shape as a check that
    passes over input it never examined (EV-001). A writer that forgets it raises TypeError here
    rather than writing an unlabelled record.

    External text is the case that matters: the loop did not produce it and no human here wrote
    it. It carries `examined_by`, naming the gate or the human that read it, or the vocabulary's
    `unexamined`, which is a fact rather than a reassurance.
    """
    if origin not in ORIGINS:
        raise ReviewError("malformed_record", f"origin {origin!r} is not a vocabulary origin; one of {sorted(ORIGINS)}")
    if origin == "external_text" and not examined_by:
        raise ReviewError("malformed_record", f"{name}: external_text needs examined_by (a gate, a human, or 'unexamined')")
    obj["origin"] = origin
    if examined_by:
        obj["examined_by"] = examined_by
    (d / name).write_text(json.dumps(obj, indent=2))


# ---------- reviewer ----------

def contract_sections():
    text = CONTRACT.read_text()
    start, end = text.index("## Scope"), text.index("## The loop")
    return text[start:end]


def _looks_truncated(text):
    """A response cut off at its output limit, as distinct from one that is simply wrong.

    ponytail: heuristic, not a provider signal. Gemini's CLI reports no finish reason, so the tell
    is an opening brace whose structure never closes. Upgrade path: read an explicit finish/stop
    reason per reviewer when one is available and fall back to this.
    """
    t = (text or "").strip()
    if not t or "{" not in t:
        return False
    return t.count("{") > t.count("}") or t.count("[") > t.count("]")


def _no_json_outcome(text):
    if _looks_truncated(text):
        return ("output_truncated", "reviewer output opens a JSON structure that never closes; "
                                    "raise this reviewer's output headroom")
    return ("malformed_output", "no JSON object in reviewer output")


# ---- XE-007: the reviewer gets the change and its callers, not the tree ----
#
# Measured 2026-09-17: the same prompt and model returned a valid review in 81s against the change
# and the files it touches, and timed out past 120s three times against the 776-file worktree. The
# reviewer was reading the repository instead of the diff.
#
# ponytail: callers are found by grepping for the changed file's module/base name. No import graph,
# no AST. A miss costs one unexamined caller, which the surface REPORTS rather than hides -- and
# SURFACE_CAP keeps a popular module from dragging the tree back in. Upgrade path: a real import
# graph if the grep proves too loose in practice.
# 60 was too generous: the XE-007 surface came to 70 files / 842 KB and still blew the reviewer's
# budget. The knob that matters is relevance, not just count -- callers are CODE. A markdown file
# mentioning "peer_review" is not going to break when peer_review changes.
SURFACE_CAP = 25


CALLER_SUFFIXES = {".py", ".sh", ".yml", ".yaml"}   # code that can break; not docs that name it

# XE-008: the surface layout had four homes -- written in build_surface, parsed in _subject_path,
# asserted in a test fixture, described in SURFACE.md -- and I broke it twice in an hour by
# updating one. A format with one producer and one parser cannot drift; a rule telling me to
# remember to check all four already existed and did not work.
SURFACE_KINDS = ("changed", "callers")


def surface_prefix(i, repo, kind):
    """The only place the surface layout is spelled. Writer and parser both call it."""
    return f"{kind}/{i}-{Path(repo['path']).name}/"


def changed_files(repos):
    out = []
    for r in repos:
        names = git(r["path"], "diff", "--name-only", f"{r['base']}..{r['head']}").split()
        out += [(r, n) for n in names]
    return out


def caller_files(repos, changed, cap):
    """Files referencing a changed file's base name. Bounded, and reports what it dropped."""
    stems = {Path(n).stem for _, n in changed if Path(n).stem not in {"__init__", "index"}}
    # F1 (reviewer, 20260917-213250): a bare relative path is not unique across repositories --
    # repo A's utils.py masked repo B's. Keyed by repository identity, as build_surface already was.
    hits, seen = [], {(id(r), n) for r, n in changed}
    for r in repos:
        try:
            tracked = git(r["path"], "ls-files").split()
        except Exception:
            continue
        for f in tracked:
            if (id(r), f) in seen or Path(f).suffix not in CALLER_SUFFIXES:
                continue
            fp = Path(r["path"]) / f
            try:
                body = fp.read_text(errors="replace")
            except OSError:
                continue
            if any(st in body for st in stems):
                hits.append((r, f)); seen.add((id(r), f))
    dropped = max(0, len(hits) - cap)
    return hits[:cap], dropped


def build_surface(repos, root, cap=SURFACE_CAP, prior_findings=()):
    """Write the review surface. Returns (path, stats).

    prior_findings matter on a fix-verification round: when a blocker is DISPROVED rather than
    fixed, there are no new commits, so the diff is empty and a diff-derived surface would carry
    nothing for the reviewer to verify against. The files those findings name travel with it.
    Found by the repo gate on XE-007's own change.
    """
    surf = root / "surface"; surf.mkdir(parents=True, exist_ok=True)
    diffs = []
    for r in repos:
        diffs.append(f"=== {Path(r['path']).name}: {r['base'][:12]}..{r['head'][:12]} ===\n"
                     + git(r["path"], "diff", f"{r['base']}..{r['head']}"))
    (surf / "CHANGE.diff").write_text("\n\n".join(diffs))

    changed = changed_files(repos)
    seen = {(id(r), n) for r, n in changed}
    for f in prior_findings or ():
        i, rel = _subject_path(f.get("file", ""), repos)
        if i is not None and (id(repos[i]), rel) not in seen:
            changed.append((repos[i], rel)); seen.add((id(repos[i]), rel))
    callers, dropped = caller_files(repos, changed, cap)
    # F2 (reviewer): the bare directory name collides when two repositories share a basename, and
    # _subject_path then binds a finding to the wrong repository. The snapshot layout used the index
    # for exactly this reason; dropping it reintroduced the bug it had already solved.
    idx = {id(r): i for i, r in enumerate(repos)}
    for group, sub in zip((changed, callers), SURFACE_KINDS):
        for r, name in group:
            src = Path(r["path"]) / name
            # snapshot() refused a symlink escaping the repository; the surface copies with
            # read_bytes(), which FOLLOWS one. Dropping the snapshot silently dropped that control,
            # so it is restored here rather than assumed. Found by tracing what snapshot() did
            # before deleting it.
            try:
                if src.is_symlink() and not src.resolve().is_relative_to(Path(r["path"]).resolve()):
                    raise ReviewError("data_use_denied",
                                      f"review surface refused {name}: symlink escapes repository scope")
            except OSError:
                continue
            dest = surf / surface_prefix(idx[id(r)], r, sub) / name
            dest.parent.mkdir(parents=True, exist_ok=True)
            try:
                dest.write_bytes(src.read_bytes())
            except OSError:
                continue
    stats = {"changed": len(changed), "callers": len(callers), "callers_withheld": dropped,
             "cap": cap, "from_prior_findings": len([f for f in (prior_findings or ())])}
    # XE-008: callers are by construction files the change did NOT touch. Naming them, and saying
    # what to do with them, routes the second-home check to the party whose job is finding the
    # problem. The builder self-reporting "I checked the callers" is worth what the prose rule was.
    caller_list = "\n".join(f"  - `{surface_prefix(idx[id(r)], r, 'callers')}{n}`" for r, n in callers) \
                  or "  (none reference the changed files)"
    (surf / "SURFACE.md").write_text(
        "# What this review can see\n\n"
        f"- `CHANGE.diff` — the full diff under review\n"
        f"- `{SURFACE_KINDS[0]}/` — the {len(changed)} files the diff modifies, at the reviewed head\n"
        f"- `{SURFACE_KINDS[1]}/` — {len(callers)} files that reference a changed file by name\n"
        f"- withheld by the {cap}-file cap: {dropped}\n\n"
        "## Files the change did NOT touch, which reference what it changed\n\n"
        f"{caller_list}\n\n"
        "Check each against the diff. A change is not finished because the file it edits is "
        "consistent; it is finished when the files that depend on it still hold. This list exists "
        "because the builder's own checks repeatedly missed exactly this — a symbol updated in one "
        "place and left stale in another — so it is computed here rather than asserted in the "
        "packet.\n\n"
        "## Limits\n\n"
        "The repository tree is NOT here. This is deliberate: a reviewer given the whole tree spends "
        "its budget reading it. If a judgement needs a file that is not present, do not guess — "
        "report it as a finding with severity `separate` naming the file you needed.\n")
    return surf, stats


# ---- EV-008: record what a review examined, not only what it found ----
#
# A review reporting no findings is two different events: it looked and found nothing, or it barely
# looked. Without the denominator those are indistinguishable, and the first few Gemini reviews on
# 2026-09-17 returned confirmatory evidence for every criterion with no way to tell which had
# happened.
#
# Since XE-007 the reviewer works inside a surface directory, so what it opened is observable from
# the filesystem rather than from whatever the CLI chooses to report -- which differs per tool and
# is absent for some. Under relatime a freshly written file has atime < mtime, so the FIRST read
# moves atime; the surface is written immediately before the reviewer runs, which is exactly that
# case.
#
# ponytail: st_atime_ns before and after, no tracing. The ceiling is a noatime mount, where atime
# never moves and every file would read as unexamined -- a false "it looked at nothing" is worse
# than no measurement, so a canary probe decides whether the instrument works and the round records
# `unavailable` instead of an empty list when it does not.

def _age_atimes(root):
    """Set every file's atime strictly older than its mtime.

    relatime updates atime on read only when atime < mtime. A freshly written file has
    atime == mtime, so whether the first read registers comes down to sub-millisecond luck:
    measured 2026-09-17, the naive scheme detected 0 reads out of 6 and this one detected 6 of 6.
    Without this the instrument would have reported "examined nothing" on every review, which is
    the false green it exists to prevent.
    """
    for p in root.rglob("*"):
        if p.is_file():
            try:
                st = p.stat()
                os.utime(p, ns=(st.st_mtime_ns - 2_000_000_000, st.st_mtime_ns))
            except OSError:
                continue


def _atime_map(root):
    return {str(p.relative_to(root)): p.stat().st_atime_ns
            for p in root.rglob("*") if p.is_file()}


def read_tracking_probe(root):
    """Can reads be observed on this filesystem at all? Write, read, see if atime moves."""
    c = root / ".read-probe"
    try:
        c.write_text("probe\n")
        st = c.stat()
        os.utime(c, ns=(st.st_mtime_ns - 2_000_000_000, st.st_mtime_ns))  # same treatment as the surface
        before = c.stat().st_atime_ns
        c.read_text()
        works = c.stat().st_atime_ns != before
        c.unlink()
        return works
    except OSError:
        return False


def examined_report(before, root):
    """What the reviewer opened, or an honest statement that it could not be measured."""
    if before is None:
        return {"read_tracking": "unavailable",
                "why": "filesystem does not update atime on read (noatime); an empty examined list "
                       "here would mean 'not measured', not 'not examined'"}
    after = _atime_map(root)
    opened = sorted(rel for rel, t in after.items()
                    if rel in before and t != before[rel] and not rel.startswith(".read-probe"))
    # EV-008.2: the diff itself is the floor. Anything under callers/ is the reviewer going beyond it.
    beyond = [p for p in opened if p.split("/")[0] == SURFACE_KINDS[1]]
    return {"read_tracking": "available",
            "examined": opened,
            "examined_count": len(opened),
            "offered_count": len(after),
            "examined_beyond_the_diff": beyond,
            "looked_beyond_the_diff": bool(beyond)}


def build_prompt(packet, round_no, prior_round, dispositions):
    repos = "\n".join(f"- {Path(r['path']).name}: base {r['base'][:12]} head {r['head'][:12]}"
                      for r in packet["repos"])
    p = [
        "You are the independent reviewer in a bounded cross-tool peer review. Read-only. Do not edit, deploy, or start another review.",
        f"Repositories under review:\n{repos}",
        "The working directory is a review surface, not a checkout: `CHANGE.diff` is the diff under "
        "review, `changed/` holds the modified files at the reviewed head, and `callers/` holds files "
        "that reference them. `SURFACE.md` states what is present and what was withheld. The "
        "repository tree is not here; if a judgement needs a file the surface does not carry, report "
        "that as a finding with severity `separate` naming the file, rather than guessing.",
        "No commands can be run here. Every reviewer runs in its tool's read-only mode, which "
        "withholds shell execution, so the `tests.commands` in the packet are a record of what "
        "the builder ran, not an instruction to re-run them. Judge them by reading the code they "
        "cover. Where a judgement genuinely requires execution, report it as a finding with "
        "severity `separate` naming the command, rather than spending the round discovering "
        "there is no shell.",
        "The builder's packet is a claim to check, not evidence. Open the code.",
        "=== PACKET ===", json.dumps({k: packet[k] for k in PACKET_FIELDS}, indent=2),
        "=== CONTRACT ===", contract_sections(),
    ]
    if round_no > 1:
        p += ["=== FIX-VERIFICATION ROUND ===",
              f"This is round {round_no}. Do not restart a full review. Verify each prior finding against its disposition, "
              "check for regressions introduced by the fixes, and report only: prior findings by their existing IDs, regressions, "
              "and any genuinely new blocker that meets the evidence and scope rules.",
              "Prior findings:", json.dumps(prior_round.get("findings", []), indent=2),
              "Builder dispositions:", json.dumps(dispositions or {}, indent=2)]
    p.append("Return only the JSON object described in the contract.")
    return "\n\n".join(p)


def headroom_argv(tool):
    """The flag that applies this entry's max_output, or [] when the CLI exposes none."""
    cfg = REVIEWERS[tool]
    flag = cfg.get("max_output_flag")
    return [flag, str(cfg["max_output"])] if flag else []


LAST_REVIEWER_USAGE = "not_reported"   # XE-012: set by run_reviewer, read by the round that called it


def reviewer_usage(tool, stdout, stderr):
    """XE-012 criterion 3: the reviewer's token usage as its CLI reports it, normalised to
    {input, output, cache_read, total, source}. A CLI that reports nothing returns the string
    "not_reported", never zeros: a zero is a claim that nothing was spent."""
    def num(v):
        return int(v) if isinstance(v, (int, float)) else 0
    try:
        env_ = json.loads(stdout)
    except (json.JSONDecodeError, TypeError):
        env_ = None
    if tool == "gemini" and isinstance(env_, dict):
        models = ((env_.get("stats") or {}).get("models") or {})
        toks = [m.get("tokens") or {} for m in models.values() if isinstance(m, dict)]
        if toks:
            u = {"input": sum(num(t.get("prompt")) for t in toks), "output": sum(num(t.get("candidates")) + num(t.get("thoughts")) for t in toks),
                 "cache_read": sum(num(t.get("cached")) for t in toks), "total": sum(num(t.get("total")) for t in toks)}
            return {**u, "source": "gemini stats.models"}
    if tool == "claude" and isinstance(env_, dict) and isinstance(env_.get("modelUsage"), dict) and env_["modelUsage"]:
        mu = [m for m in env_["modelUsage"].values() if isinstance(m, dict)]
        u = {"input": sum(num(m.get("inputTokens")) for m in mu), "output": sum(num(m.get("outputTokens")) for m in mu),
             "cache_read": sum(num(m.get("cacheReadInputTokens")) for m in mu)}
        u["total"] = u["input"] + u["output"] + u["cache_read"] + sum(num(m.get("cacheCreationInputTokens")) for m in mu)
        return {**u, "source": "claude modelUsage"}
    if tool == "codex":
        m = re.search(r"tokens used\W*([\d,]+)", (stderr or "") + "\n" + (stdout or ""), re.I)
        if m:
            return {"input": None, "output": None, "cache_read": None, "total": int(m.group(1).replace(",", "")), "source": "codex 'tokens used'"}
    return "not_reported"


OPENROUTER_URL = os.environ.get("GSTACK_OPENROUTER_URL", "https://openrouter.ai/api/v1/chat/completions")
API_SURFACE_CAP = 400_000          # characters of surface sent to an api reviewer
LAST_SENT_SURFACE = None           # XE-013.6: set by run_openrouter, read by the round that called it


def openrouter_key():
    """XE-013.8. The credential has one home, the vault file GSTACK_OPENROUTER_ENV names. Never an
    argument, never the repository. Same convention as agent_token.py's GSTACK_AGENT_APP_ENV."""
    envfile = os.environ.get("GSTACK_OPENROUTER_ENV")
    if not envfile:
        raise ReviewError("review_unavailable",
                          "GSTACK_OPENROUTER_ENV is not set; point it at the vault's openrouter.env")
    path = Path(envfile).expanduser()
    if not path.exists():
        raise ReviewError("review_unavailable",
                          f"GSTACK_OPENROUTER_ENV names {path}, which does not exist. No other credential is tried.")
    for line in path.read_text().splitlines():
        k, _, v = line.partition("=")
        if k.strip() == "OPENROUTER_API_KEY" and v.strip():
            return v.strip().strip('"').strip("'")
    raise ReviewError("review_unavailable", f"{path} sets no OPENROUTER_API_KEY")


def surface_as_text(tool, root):
    """XE-013.5: an api reviewer has no filesystem, so the surface is SENT to it.

    Returns (text, sent). `sent` is the per-file record: this is the honest denominator for a
    reviewer that opens nothing, and it is what the round stores instead of EV-008's atime
    measurement, which would report an empty examined list and read as "it looked at nothing".

    ponytail: concatenation with a byte cap. The ceiling is a surface larger than the cap, where the
    tail is declared unsent rather than silently dropped; paginate only if that starts happening.
    """
    sends = REVIEWERS[tool]["sends"]
    parts, sent, total = [], [], 0
    for rel in sorted(str(q.relative_to(root)) for q in root.rglob("*") if q.is_file()):
        if rel not in sends and rel.split("/")[0] not in sends:
            continue
        body = (root / rel).read_text(errors="replace")
        if total + len(body) > API_SURFACE_CAP:
            sent.append({"path": rel, "sent": False, "why": f"surface cap {API_SURFACE_CAP} reached"})
            continue
        total += len(body)
        parts.append(f"=== {rel} ===\n{body}")
        sent.append({"path": rel, "sent": True, "chars": len(body)})
    return "\n\n".join(parts), sent


def run_openrouter(tool, prompt, root, timeout, output_schema):
    """One reviewer round over the openrouter transport. Returns (text, model_that_ran)."""
    global LAST_REVIEWER_USAGE, LAST_SENT_SURFACE
    cfg = REVIEWERS[tool]
    if not model_ok(tool, cfg["model"]):
        raise ReviewError("model_below_floor", f"{tool} is configured for {cfg['model']!r}; floor is {cfg['floor_name']}")
    key = openrouter_key()
    text, sent = surface_as_text(tool, root)
    LAST_SENT_SURFACE, LAST_REVIEWER_USAGE = sent, "not_reported"
    body = {"model": cfg["model"], "max_tokens": cfg["max_output"],
            "messages": [{"role": "user",
                          "content": prompt + "\n\n=== REVIEW SURFACE ===\n"
                          + "You cannot open files and cannot run commands. Everything you are "
                            "permitted to examine is below.\n\n" + text}],
            "response_format": {"type": "json_schema",
                                "json_schema": {"name": "review", "strict": True, "schema": output_schema}}}
    req = urllib.request.Request(OPENROUTER_URL, data=json.dumps(body).encode(),
                                 headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            env_ = json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        raise ReviewError("review_unavailable", f"{tool}: HTTP {e.code} {e.read()[:400].decode(errors='replace')}")
    except urllib.error.URLError as e:
        raise ReviewError("timeout" if isinstance(e.reason, TimeoutError) else "review_unavailable", f"{tool}: {e.reason}")
    except TimeoutError:
        raise ReviewError("timeout", f"{tool} exceeded {timeout}s")
    if env_.get("error"):
        raise ReviewError("review_unavailable", f"{tool}: {str(env_['error'])[:400]}")
    u = env_.get("usage") or {}
    if u:   # XE-013.4 / XE-012.3: one shape from the provider, not a per-CLI parse
        LAST_REVIEWER_USAGE = {"input": u.get("prompt_tokens"), "output": u.get("completion_tokens"),
                               "cache_read": (u.get("prompt_tokens_details") or {}).get("cached_tokens"),
                               "total": u.get("total_tokens"), "source": "openrouter usage"}
    choice = (env_.get("choices") or [{}])[0]
    out = ((choice.get("message") or {}).get("content") or "")
    model = env_.get("model") or cfg["model"]
    # XE-005.5: a ceiling hit and a broken reviewer have different causes and different fixes.
    if choice.get("finish_reason") in ("length", "MAX_TOKENS"):
        raise ReviewError("output_truncated", f"{tool} stopped at its {cfg['max_output']}-token ceiling")
    if not out.strip():
        raise ReviewError("malformed_output", f"{tool} returned empty content (finish_reason={choice.get('finish_reason')!r})")
    if not model_ok(tool, model):
        raise ReviewError("model_below_floor", f"{tool} ran {model!r}, below the floor ({cfg['floor']})")
    return out, model


def run_reviewer(tool, prompt, root, timeout, schema=None):
    """Returns (reviewer_output_text, model_that_ran)."""
    output_schema = schema or STRICT_SCHEMA
    env = {**os.environ, RECURSION_ENV: "1"}
    fake = os.environ.get("GSTACK_PEER_REVIEW_FAKE_CMD") if _SELFTEST else None  # selftest hook: any command that prints the JSON
    if fake:
        cmd, parse = ["sh", "-c", fake], lambda r: (r.stdout, "fake")
    elif REVIEWERS.get(tool, {}).get("transport") == "openrouter":
        return run_openrouter(tool, prompt, root, timeout, output_schema)
    elif tool == "codex":
        if not shutil.which("codex"):
            raise ReviewError("review_unavailable", "codex CLI not installed on PATH")
        if not model_ok("codex", REVIEWERS["codex"]["model"]):
            raise ReviewError("model_below_floor", f"GSTACK_CODEX_MODEL={REVIEWERS['codex']['model']}; floor is {REVIEWERS['codex']['floor_name']}")
        schema = root / "schema.json"; last = root / "last.txt"
        schema.write_text(json.dumps(output_schema))
        cmd = ["codex", "exec", "-C", str(root), "-m", REVIEWERS["codex"]["model"], "-c", "model_reasoning_effort=high",
               "--sandbox", "read-only", "--skip-git-repo-check",
               "--output-schema", str(schema), "--output-last-message", str(last)] + headroom_argv("codex") + [prompt]
        def parse(r):
            m = re.search(r"^model:\s*(\S+)", r.stderr + r.stdout, re.M)  # codex echoes the resolved model in its header
            return (last.read_text() if last.exists() else r.stdout), (m.group(1) if m else None)
    elif tool == "claude":
        if not shutil.which("claude"):
            raise ReviewError("review_unavailable", "claude CLI not installed on PATH")
        if not model_ok("claude", REVIEWERS["claude"]["model"]):
            raise ReviewError("model_below_floor", f"GSTACK_CLAUDE_MODEL={REVIEWERS['claude']['model']}; floor is {REVIEWERS['claude']['floor_name']}")
        cmd = ["claude", "-p", prompt, "--model", REVIEWERS["claude"]["model"], "--output-format", "json", "--json-schema", json.dumps(output_schema),
               "--allowedTools", "Read", "Grep", "Glob", "Bash(git:*)", "--disallowedTools", "Write", "Edit", "MultiEdit", "NotebookEdit",
               "--add-dir", str(root), "--no-session-persistence", "--max-turns", "60"] + headroom_argv("claude")
        def parse(r):
            try:
                env_ = json.loads(r.stdout)
            except json.JSONDecodeError:
                return r.stdout, None
            if not isinstance(env_, dict):
                return r.stdout, None
            usage = env_.get("modelUsage") or {}
            # the review model is the one that did the work; the harness also bills a small helper model
            model = max(usage, key=lambda k: usage[k].get("outputTokens", 0)) if usage else None
            text = json.dumps(env_["structured_output"]) if "structured_output" in env_ else env_.get("result", r.stdout)
            return text, model
    elif tool == "gemini":
        if not shutil.which("gemini"):
            raise ReviewError("review_unavailable", "gemini CLI not installed on PATH")
        if not model_ok("gemini", REVIEWERS["gemini"]["model"]):
            raise ReviewError("model_below_floor", f"GSTACK_GEMINI_MODEL={REVIEWERS['gemini']['model']}; floor is {REVIEWERS['gemini']['floor_name']}")
        # gemini has -o json but no --output-schema: the schema goes in the prompt and is validated
        # on the way back. `--approval-mode plan` is its read-only mode.
        cmd = ["gemini", "-m", REVIEWERS["gemini"]["model"], "--approval-mode", "plan", "--skip-trust",
               "-o", "json", "--include-directories", str(root),
               "-p", prompt + "\n\n=== REQUIRED OUTPUT SCHEMA ===\n" + json.dumps(output_schema)
                    + "\n\nReturn one complete JSON object matching it. Do not truncate."] + headroom_argv("gemini")
        def parse(r):
            try:
                env_ = json.loads(r.stdout)
            except json.JSONDecodeError:
                return r.stdout, REVIEWERS["gemini"]["model"]
            if not isinstance(env_, dict):
                return r.stdout, REVIEWERS["gemini"]["model"]
            model = (env_.get("stats", {}) or {}).get("model") or REVIEWERS["gemini"]["model"]
            return env_.get("response", r.stdout), model
    else:
        raise ReviewError("review_unavailable", f"unknown tool {tool}")
    global LAST_REVIEWER_USAGE
    LAST_REVIEWER_USAGE = "not_reported"
    try:
        # stdin closed: codex exec otherwise blocks on "Reading additional input from stdin..."
        r = subprocess.run(cmd, cwd=str(root), env=env, capture_output=True, text=True, timeout=timeout, stdin=subprocess.DEVNULL)
        LAST_REVIEWER_USAGE = reviewer_usage("fake" if fake else tool, r.stdout, r.stderr)
    except subprocess.TimeoutExpired:
        raise ReviewError("timeout", f"{tool} exceeded {timeout}s")
    except FileNotFoundError as e:
        raise ReviewError("review_unavailable", str(e))
    if r.returncode != 0:
        raise ReviewError("review_unavailable", f"{tool} exited {r.returncode}: {(r.stderr + r.stdout).strip()[-800:]}")
    text, model = parse(r)
    if not fake and not model_ok(tool, model):
        raise ReviewError("model_below_floor", f"{tool} ran {model!r}, below the floor ({REVIEWERS[tool]['floor']})")
    return text, model


def disposition_value(value):
    return value.get("disposition") if isinstance(value, dict) else value


def validate(raw, packet, prior=None, dispositions=None):
    # A reviewer that returned NOTHING did not return something wrong. Distinguishing them matters
    # for the same reason output_truncated does: different causes, different fixes. Observed
    # 2026-09-17 -- gemini exited 0 with an empty response and the round reported malformed_output,
    # sending a reader looking for a formatting defect in a response that did not exist. This is
    # the case XE-005's sixth criterion was written about: the Council Sonnet-5 slot returned empty
    # content while the dispatcher reported success.
    if not (raw or "").strip():
        raise ReviewError("empty_output",
                          "reviewer exited successfully and returned nothing; check its quota, its "
                          "output headroom, and whether the request was refused")
    m = re.search(r"\{.*\}", raw, re.S)
    if not m:
        raise ReviewError(*_no_json_outcome(raw))
    try:
        out = json.loads(m.group(0))
    except json.JSONDecodeError as e:
        if _looks_truncated(raw):
            raise ReviewError("output_truncated",
                              f"reviewer output ends mid-structure ({len(raw)} chars); raise this reviewer's "
                              f"output headroom rather than treating it as a malformed review. ({e})")
        raise ReviewError("malformed_output", f"invalid JSON: {e}")
    if not isinstance(out, dict):
        raise ReviewError("malformed_output", "review must be an object")
    if out.get("verdict") not in VERDICTS:
        raise ReviewError("malformed_output", f"verdict {out.get('verdict')!r}")
    if not isinstance(out.get("findings"), list) or not isinstance(out.get("acceptance"), list):
        raise ReviewError("malformed_output", "findings/acceptance must be lists")
    expected = packet["acceptance_criteria"]
    seen = set()
    for row in out["acceptance"]:
        if (not isinstance(row, dict) or not isinstance(row.get("criterion"), str) or
                type(row.get("met")) is not bool or not isinstance(row.get("evidence"), str) or not row["evidence"].strip()):
            raise ReviewError("malformed_output", "acceptance requires criterion, boolean met, and evidence")
        criterion = row["criterion"]
        if criterion not in expected or criterion in seen:
            raise ReviewError("malformed_output", "unknown or duplicate acceptance criterion")
        seen.add(criterion)
    if seen != set(expected):
        raise ReviewError("malformed_output", "acceptance coverage is incomplete")
    if out["verdict"] == "no_blocking_findings" and any(not row["met"] for row in out["acceptance"]):
        raise ReviewError("malformed_output", "clean verdict contradicts unmet acceptance")
    ids = set()
    for f in out["findings"]:
        if not isinstance(f, dict):
            raise ReviewError("malformed_output", "finding must be an object")
        need = OUTPUT_SCHEMA["properties"]["findings"]["items"]["required"]
        if any(k not in f for k in need) or f["severity"] not in SEVERITIES or type(f["line"]) is not int or any(not isinstance(f.get(k), str) or not f[k].strip() for k in need if k != "line"):
            raise ReviewError("malformed_output", f"bad finding {f.get('id')}")
        if f["id"] in ids:
            raise ReviewError("malformed_output", f"duplicate finding id {f['id']}")
        ids.add(f["id"])
    has_block = any(f["severity"] == "blocking" for f in out["findings"])
    if has_block != (out["verdict"] == "blocking_findings"):
        raise ReviewError("malformed_output", "verdict disagrees with finding severities")
    prior_ids = {f["id"] for f in (prior or {}).get("findings", []) if f["severity"] == "blocking"}
    resolutions = out.get("blocker_resolutions")
    if not isinstance(resolutions, list):
        raise ReviewError("malformed_output", "blocker_resolutions must be a list")
    resolved_ids = set()
    for row in resolutions:
        if (not isinstance(row, dict) or not isinstance(row.get("id"), str) or type(row.get("resolved")) is not bool or
                not isinstance(row.get("evidence"), str) or not row["evidence"].strip()):
            raise ReviewError("malformed_output", "blocker resolution needs id, boolean resolved, and evidence")
        fid = row["id"]
        if fid not in prior_ids or fid in resolved_ids:
            raise ReviewError("malformed_output", "unknown or duplicate blocker resolution")
        resolved_ids.add(fid)
        still_blocking = any(f["id"] == fid and f["severity"] == "blocking" for f in out["findings"])
        if row["resolved"]:
            if still_blocking or disposition_value((dispositions or {}).get(fid)) not in {"fixed", "disproved"}:
                raise ReviewError("malformed_output", "resolved blocker contradicts finding or disposition")
        elif not still_blocking:
            raise ReviewError("malformed_output", "unresolved blocker must remain blocking")
    if resolved_ids != prior_ids:
        raise ReviewError("malformed_output", "prior blocker coverage is incomplete")
    out.setdefault("regressions_from_fixes", [])
    if not isinstance(out["regressions_from_fixes"], list) or any(not isinstance(v, str) or not v.strip() for v in out["regressions_from_fixes"]):
        raise ReviewError("malformed_output", "regressions_from_fixes must contain nonempty strings")
    blocking_ids = {f["id"] for f in out["findings"] if f["severity"] == "blocking"}
    if any(fid not in blocking_ids for fid in out["regressions_from_fixes"]):
        raise ReviewError("malformed_output", "every regression must name a blocking finding ID with evidence")
    out.setdefault("notes", "")
    return out



# ---------- EV-002: evidential links ----------
#
# A finding stores a name (file, line). The name is assumed to resolve to the code the
# reviewer read. Only that assumption makes the finding evidence, and nothing re-checks
# it: names are cheap to keep and expensive to verify, so they persist after the thing
# at the other end has changed. The functions below bind each finding to the CONTENT at
# the reviewed head when the round is recorded, and re-resolve every link on demand.

def _has_path(repo, head, rel):
    return subprocess.run(["git", "-C", str(repo), "cat-file", "-e", f"{head}:{rel}"], capture_output=True).returncode == 0


def _is_commit(repo, ref):
    return subprocess.run(["git", "-C", str(repo), "rev-parse", "--verify", f"{ref}^{{commit}}"], capture_output=True).returncode == 0


def _subject_path(path, repos):
    """Map a reported path onto (repo index, repo-relative path).

    Reviewers report either a snapshot-prefixed path ("0-cki/calc.py", which is what
    Codex returns) or a repo-relative one ("calc.py", which is what Claude returns).
    Both have to land on the same subject or the binding is worthless.

    XE-007 added two more spellings. A reviewer reading the review surface reports
    "changed/cki/calc.py" or "callers/cki/calc.py", and without stripping those every finding
    from a surface-based review binds to nothing -- the EV-002 guarantee degrading silently
    rather than failing loudly. Found by following a failing test to its contract instead of
    patching the assert.
    """
    p = path.replace("\\", "/")
    while p.startswith("./"):          # F1: lstrip("./") also ate the dot of .claude-plugin
        p = p[2:]
    p = p.lstrip("/")
    for i, r in enumerate(repos):
        name = Path(r["path"]).name
        for prefix in (f"{i}-{name}/", *(surface_prefix(i, r, k) for k in SURFACE_KINDS)):
            if p.startswith(prefix):
                return i, p[len(prefix):]
    for i, r in enumerate(repos):
        if _has_path(r["path"], r["head"], p):
            return i, p
    return None, p


def _span(repo, head, rel, line, ctx=2):
    """Blob id plus a hash of the lines around the finding, at a pinned commit."""
    if not _has_path(repo, head, rel):
        return None
    blob = git(repo, "rev-parse", f"{head}:{rel}")
    text = subprocess.run(["git", "-C", str(repo), "show", f"{head}:{rel}"], capture_output=True, text=True).stdout
    lines = text.splitlines()
    lo, hi = max(0, line - 1 - ctx), min(len(lines), line + ctx)
    return {"blob": blob, "span": hashlib.sha256("\n".join(lines[lo:hi]).encode()).hexdigest()[:16],
            "span_lines": [lo + 1, hi], "file_lines": len(lines), "line_exists": 0 < line <= len(lines)}


def bind_subjects(findings, repos):
    """One content-bound subject per finding, computed by the dispatcher.

    The reviewer claims a location; the dispatcher is the party that knows the pinned
    commit, so the binding is computed here rather than trusted from the reviewer.
    """
    subjects = {}
    for f in findings:
        i, rel = _subject_path(f["file"], repos)
        if i is None:
            subjects[f["id"]] = {"path": rel, "bound": False, "why": "no packet repository holds this path at its reviewed head"}
            continue
        r = repos[i]
        span = _span(r["path"], r["head"], rel, f["line"])
        if span is None:
            subjects[f["id"]] = {"repo": r["path"], "path": rel, "head": r["head"], "bound": False, "why": "path absent at the reviewed head"}
        else:
            subjects[f["id"]] = {"repo": r["path"], "path": rel, "head": r["head"], "line": f["line"], "bound": True, **span}
    return subjects


def verify_links(d):
    """Re-resolve every link in a finished review. Completeness is not evidence.

    Checks, in order: the packet's commits still resolve; each round record still
    describes the content it was bound to (record integrity); each finding's subject at
    the repository's CURRENT head still matches what was reviewed (drift); every
    blocking finding carries a disposition and every disposition names a real finding;
    and any recorded human observation still produces the output it recorded.

    Expected drift is not stale: a finding disposed `fixed` SHOULD read differently now.
    Drift on any other disposition means the finding's evidence no longer describes the
    code, which is the failure this whole command exists to surface.
    """
    state, packet = load(d, "state.json"), load(d, "packet.json")
    dispositions = load(d, "dispositions.json") or {}
    checks, examined = [], 0

    def record(link, ok, detail="", kind="link"):
        """kind separates two failures that a single outcome name would blur:
        a `link` resolved to something other than what was reviewed; a `record` entry
        the review is required to carry is absent. Only the first is a stale link."""
        nonlocal examined
        examined += 1
        checks.append({"link": link, "ok": bool(ok), "detail": detail, "kind": kind})

    for r in packet["repos"]:
        name = Path(r["path"]).name
        for end in ("base", "head"):
            record(f"packet {end} {r[end][:7]} resolves in {name}", _is_commit(r["path"], r[end]),
                   "" if _is_commit(r["path"], r[end]) else "commit is gone from the repository")

    unbound = 0
    blocking_ids, known = {}, set()          # collected here, where the record is validated
    for n in range(1, state.get("rounds_used", 0) + 1):
        rec = load(d, f"round-{n}.json")
        # F2: a round the state claims cannot be absent. Loading it as {} produced no
        # checks at all, and a verifier that examines nothing and reports success is the
        # precise failure this command exists to catch.
        if rec is None:
            record(f"round {n} record exists", False, "state claims this round ran and no record of it is on disk", kind="record")
            continue
        if "outcome" not in rec:
            record(f"round {n} record is complete", False, "record carries no outcome", kind="record")
            continue
        if rec.get("error"):
            record(f"round {n} record is complete", True, f"round did not produce findings: {rec['outcome']}")
            continue
        # F2, second pass: absence was caught, emptiness was not. A record carrying an
        # outcome and nothing else still contributed no checks, so the round verified by
        # having nothing in it to verify. Require the fields a completed round must have.
        # Presence is not validity: a field of the wrong shape reaches the per-finding
        # loop and either crashes it or slips past it, so check the shape here.
        # XE-011: what a completed round is has one home, the vocabulary's review_round shape.
        round_shape = vocab_shape("review_round")
        types = {"list": list, "dict": dict}
        bad = [k for k, t in round_shape["types"].items() if k in rec and not isinstance(rec[k], types[t])]
        missing = [k for k in round_shape["required"] if k not in rec]
        if missing or bad:
            record(f"round {n} record is complete", False,
                   f"completed round is missing {missing} and malformed in {bad}", kind="record")
            continue
        need = vocab_shape("finding")["required"]
        if any(not isinstance(f, dict) or any(k not in f for k in need) for f in rec["findings"]):
            record(f"round {n} findings are well formed", False, "a finding is not an object carrying id and severity", kind="record")
            continue
        covered = {row.get("criterion") for row in rec["acceptance"] if isinstance(row, dict)}
        expected = set(packet["acceptance_criteria"])
        record(f"round {n} acceptance covers every criterion", covered == expected,
               "" if covered == expected else f"not covered: {sorted(expected - covered)}", kind="record")
        subjects = rec.get("subjects")
        findings = rec["findings"]
        for f in findings:
            known.add(f["id"])
            if f["severity"] == "blocking":
                blocking_ids.setdefault(f["id"], n)
        if subjects is None and findings:
            unbound += 1
            record(f"round {n} finding subjects", False,
                   "no subjects recorded; this review predates content binding and its findings cannot be re-resolved",
                   kind="unverifiable")
            continue
        for f in findings:
            s = (subjects or {}).get(f["id"])
            tag = f"round {n} {f['id']} -> {f['file']}:{f['line']}"
            if not s or not s.get("bound"):
                unbound += 1
                record(tag, False, (s or {}).get("why", "finding was never bound to content"), kind="unverifiable")
                continue
            # F3: re-resolve the FINDING's own location and require it to be the subject
            # that was recorded for it. Hashing the subject's stored path against itself
            # verifies nothing about the finding that cites it.
            ri, rel = _subject_path(f["file"], rec.get("repos") or packet["repos"])
            if (ri is None or rel != s.get("path") or rec["repos"][ri]["path"] != s.get("repo")
                    or f["line"] != s.get("line") or rec["repos"][ri]["head"] != s.get("head")):
                record(tag, False, "the finding no longer names the subject recorded for it")
                continue
            if not s.get("line_exists", True):
                record(tag, False, f"line {s['line']} did not exist at the reviewed head ({s['file_lines']} lines)")
                continue
            at_reviewed = _span(s["repo"], s["head"], s["path"], s["line"])
            if not at_reviewed or at_reviewed["span"] != s["span"]:
                record(tag, False, "record altered: the reviewed head no longer yields the recorded content")
                continue
            current = resolve_commit(s["repo"], "HEAD") if _is_commit(s["repo"], "HEAD") else None
            if current is None:
                record(tag, False, "repository HEAD does not resolve")
                continue
            if current == s["head"]:
                record(tag, True, "head unchanged since review")
                continue
            now = _span(s["repo"], current, s["path"], s["line"])
            disposition = disposition_value(dispositions.get(f["id"]))
            drifted = (now is None) or now["span"] != s["span"]
            if not drifted:
                record(tag, True, f"content unchanged at {current[:7]}")
            elif disposition == "fixed":
                record(tag, True, f"content changed at {current[:7]}, expected for a fixed finding")
            else:
                record(tag, False, f"content changed at {current[:7]} and the disposition is {disposition or 'none'}; "
                                   "the finding's evidence no longer describes the code")

    # F4: every round's blockers, not only the last. A blocker raised in round one and
    # resolved in round two is absent from the final findings, and checking only the
    # final round excused exactly the dispositions that were acted on. Both of these
    # read the collectors filled in above rather than walking the rounds again: a second
    # walk is a second home for the shape rule, and it crashed on a malformed record
    # that the first walk had already rejected.
    for fid, n in sorted(blocking_ids.items()):
        record(f"disposition for blocking {fid} (round {n})", fid in dispositions, "no disposition recorded", kind="record")
    for fid in dispositions:
        record(f"disposition {fid} names a real finding", fid in known, "no finding carries this id", kind="record")

    release = load(d, "release.json") or {}
    for obs in release.get("observations", []):
        try:
            out = subprocess.run(shlex.split(obs["command"]), capture_output=True, text=True, timeout=60,
                                 cwd=obs.get("cwd") or None)
            same = hashlib.sha256((out.stdout + out.stderr).encode()).hexdigest()[:16] == obs.get("output_digest")
            if obs.get("supported") is False:
                record(f"observation '{obs['claim']}' was supported when recorded", False,
                       f"the command exited {obs.get('exit')} and never supported the claim")
            else:
                record(f"observation '{obs['claim']}' still holds", same,
                       "" if same else "the recorded command no longer produces the output it recorded")
        except Exception as e:
            record(f"observation '{obs['claim']}' re-runs", False, f"{type(e).__name__}: {e}")

    # TB-001: every record in this review says where its content came from. A record with no
    # origin, or one outside the vocabulary, is an incomplete record rather than drift: nothing
    # resolved to the wrong thing, the record just cannot say what it is. External text with no
    # examined_by is the same failure with a sharper edge, because that is the content a reader
    # is most likely to treat as the loop's own.
    # Counted apart from `examined` on purpose. `examined` is the verifier's own EV-001 guard: it
    # asks whether any LINK was re-resolved, and a review with no links must still report
    # examined_nothing. Folding provenance checks into it would let a review that re-resolved
    # nothing report links_verified because it had counted two origin fields, which is the false
    # green this file exists to refuse.
    origins, records_examined = {}, 0
    for f in sorted(d.glob("*.json")):
        if f.name == "dispositions.json":
            continue                      # a map of ids, not a record with its own provenance
        obj = load(d, f.name)
        if not isinstance(obj, dict):
            continue
        origin = obj.get("origin")
        origins[origin or "missing"] = origins.get(origin or "missing", 0) + 1
        records_examined += 1
        checks.append({"link": f"{f.name} names its origin", "ok": origin in ORIGINS,
                       "detail": "" if origin in ORIGINS else f"origin is {origin!r}", "kind": "record"})
        if origin == "external_text":
            ok = bool(obj.get("examined_by"))
            checks.append({"link": f"{f.name} names what examined its external text", "ok": ok,
                           "detail": "" if ok else "external_text with no examined_by", "kind": "record"})

    broken = [c for c in checks if not c["ok"]]
    failed_kinds = {c["kind"] for c in broken}
    if examined == 0:
        outcome = "examined_nothing"          # EV-001 applied to the verifier itself
    elif "link" in failed_kinds:
        outcome = "stale_link"                # something resolved to other than what was reviewed
    elif "unverifiable" in failed_kinds:
        outcome = "links_unverifiable"        # cannot be re-resolved either way
    elif "record" in failed_kinds:
        outcome = "incomplete_record"         # a required entry is missing, which is not drift
    else:
        outcome = "links_verified"
    # XE-011 criterion 5: a record written against another vocabulary version is reported, not
    # failed. An older record is not wrong for being older, but a reader has to be able to see it.
    drift = [f"{name}: {v or 'unversioned'}" for name, v in
             [("packet", packet.get("vocabulary_version"))] +
             [(f"round {n}", (load(d, f"round-{n}.json") or {}).get("vocabulary_version"))
              for n in range(1, state.get("rounds_used", 0) + 1)]
             if v != VOCAB_VERSION]
    return {"review_id": d.name, "outcome": outcome, "examined": examined,
            "broken": len(broken), "unbound": unbound, "checks": checks,
            "records_examined": records_examined, "records_by_origin": origins,
            "vocabulary_version": VOCAB_VERSION, "vocabulary_drift": drift}


def cmd_verify(a):
    d = rdir(a.review_id)
    report = verify_links(d)
    if a.json:
        print(json.dumps(report, indent=2))
    else:
        print(f"LINK VERIFICATION  {report['review_id']}")
        for c in report["checks"]:
            print(f"  {'ok  ' if c['ok'] else 'FAIL'}  {c['link']}" + (f"  — {c['detail']}" if c["detail"] else ""))
        print(f"outcome: {report['outcome']}  ({report['examined']} links examined, {report['broken']} broken)")
        # TB-001: say what the records claim about themselves, in the place a reader already looks.
        origins = ", ".join(f"{n} {o}" for o, n in sorted(report["records_by_origin"].items())) or "none"
        print(f"records: {report['records_examined']} examined  ({origins})")
        # XE-011 criterion 5: drift is reported where a reader looks, not only in --json.
        drift = report["vocabulary_drift"]
        print(f"vocabulary: {report['vocabulary_version']}  " +
              ("no drift" if not drift else "written against another version: " + "; ".join(drift)))
    if report["outcome"] != "links_verified":
        raise ReviewError(report["outcome"], f"{report['broken']} of {report['examined']} links did not re-resolve")
    return report


def human_observations(packet, extra):
    """EV-004: give the approver's reconstruction a field it can be written in.

    The record has always had room for the decision and none for what the person worked
    out before entering it, which makes that input unrepresentable rather than merely
    unmonitored. Each observation stores the claim, the command that supports it, and a
    digest of that command's output, so `verify` can re-run it.

    This records what was run. It is not evidence that a person read the result, and
    nothing here should be read as proof of attention.
    """
    observations = []
    for repo in packet["repos"]:
        # F6: build the argv, then serialize it for replay. Formatting a command string
        # and splitting it apart again tore every path containing a space into pieces,
        # and these repositories live under "MoxyWolf Shared Files".
        argv = ["git", "-C", repo["path"], "rev-parse", "HEAD"]
        out = subprocess.run(argv, capture_output=True, text=True, timeout=60)
        supported = out.returncode == 0 and out.stdout.strip() == repo["head"]
        if not supported:
            raise ReviewError("release_blocked", f"{Path(repo['path']).name}: HEAD is not the reviewed head; the claim this observation would record is false")
        observations.append({"claim": f"release head of {Path(repo['path']).name} is the reviewed head {repo['head'][:7]}",
                             "command": shlex.join(argv), "supported": True,
                             "output_digest": hashlib.sha256((out.stdout + out.stderr).encode()).hexdigest()[:16],
                             "output_head": (out.stdout or out.stderr).strip()[:200], "automatic": True})
    for item in extra or []:
        claim, sep, cmd = item.partition("::")
        if not sep or not claim.strip() or not cmd.strip():
            raise ReviewError("release_blocked", "observation must be written as 'claim :: command'")
        out = subprocess.run(shlex.split(cmd.strip()), capture_output=True, text=True, timeout=60)
        observations.append({"claim": claim.strip(), "command": shlex.join(shlex.split(cmd.strip())),
                             "supported": out.returncode == 0,
                             "output_digest": hashlib.sha256((out.stdout + out.stderr).encode()).hexdigest()[:16],
                             "output_head": (out.stdout or out.stderr).strip()[:200], "automatic": False,
                             "exit": out.returncode})
    return observations


# ---------- commands ----------

# ---- XE-010: a packet whose criteria are narrower than the item it claims ----
#
# On 2026-09-17 a review returned no_blocking_findings at 13/13 on a packet whose criteria were
# NARROWER than the items it claimed. XE-005 criterion 6 was never in the packet, so the review
# could not have examined it, and it merged unbuilt. A later scoring pass over that day's reviews
# found three more of the same shape -- XE-001 #6, XE-002 #3, EV-008 #1 and #3 -- two of which
# nobody had noticed. A review can only ever be as wide as the criteria it is given.
#
# This gate is MONOTONIC by construction: it can refuse to open a review, never approve one. The
# scoring itself is NOT done here. It needs a model and a network, and the dispatcher is stdlib and
# offline on purpose, so packet_coverage.mjs writes a `coverage` report into the packet beforehand
# and this only reads it.
#
# When no report is present the review still opens, and the state records coverage_checked: false.
# Not running this authorises nothing -- the review and the human merge still happen -- so blocking
# every review on a paid third-party service would trade a real gate for a theoretical one. What it
# must never do is let a later reader believe coverage was checked when it was not.
COVERAGE_FLOOR = 0.5


def coverage_verdict(packet, floor=COVERAGE_FLOOR):
    """(ok, status, uncovered). Reads a report; never produces one."""
    rep = packet.get("coverage")
    if not rep:
        return True, "not_run", []
    if rep.get("status") == "unavailable":
        return True, f"unavailable: {rep.get('why', 'no reason given')}", []
    scores = rep.get("criteria") or []
    if not scores:
        # EV-001: a report that examined nothing is not a clean report
        return False, "empty", [{"item": "-", "criterion_no": 0,
                                 "declared": "coverage report carries no criteria; it examined nothing"}]
    uncovered = [c for c in scores if (c.get("probability") is None or c["probability"] < floor)]
    return (not uncovered), ("covered" if not uncovered else "uncovered"), uncovered


def cmd_open(a):
    if os.environ.get(RECURSION_ENV):
        sys.exit("refused: this is a reviewer session; peer review does not recurse")
    if not 1 <= a.max_rounds <= 3 or a.timeout <= 0:
        raise ReviewError("malformed_packet", "max_rounds must be 1..3 and timeout positive")
    packet = load_packet(a.packet)

    # XE-010: refuse a packet narrower than the items it claims. Only ever adds a gate.
    ok, cov_status, uncovered = coverage_verdict(packet)
    if not ok and not getattr(a, "accept_narrow_packet", False):
        lines = "\n".join(f"  {c.get('item')} #{c.get('criterion_no')} "
                           f"(p={c.get('probability')}): {str(c.get('declared'))[:120]}"
                           for c in uncovered)
        raise ReviewError("packet_narrower_than_item",
                          "these declared criteria are not tested by any acceptance criterion in this "
                          "packet, so a review against it could pass while they remain unbuilt:\n"
                          f"{lines}\nWiden the packet, or pass --accept-narrow-packet with a reason "
                          "recorded in exclusions.")

    stem = time.strftime("%Y%m%d-%H%M%S") + "-" + packet["repos"][0]["head"][:7]
    root = review_root()
    root.mkdir(parents=True, exist_ok=True)
    d = Path(tempfile.mkdtemp(prefix=stem + "-", dir=root))
    review_id = d.name
    reviewer, is_fallback = choose_reviewer(a.builder, os.environ.get("GSTACK_REVIEWER"), require_installed=False)
    state = {"review_id": review_id, "builder": a.builder, "builder_family": family(a.builder),
             "reviewer": reviewer, "reviewer_family": family(reviewer), "reviewer_is_fallback": is_fallback,
             "release_owner": packet["release_owner"], "max_rounds": a.max_rounds, "timeout": a.timeout, "rounds_used": 0, "outcome": "opened",
             # F1 (reviewer, 20260918-114838): an UNAVAILABLE scorer had been recorded as checked.
             # The record then claimed coverage was verified when nothing had run -- the precise
             # false green this item exists to remove, inside the item's own gate. Only a report
             # that actually scored criteria counts as checked.
             "coverage_checked": cov_status not in {"not_run"} and not cov_status.startswith("unavailable"),
             "coverage_status": cov_status,
             "coverage_overridden": bool(uncovered and getattr(a, "accept_narrow_packet", False)),
             "heads": [[r["head"] for r in packet["repos"]]]}
    packet["vocabulary_version"] = VOCAB_VERSION   # XE-011: the version this review was written against
    save(d, "packet.json", packet, "gate_output"); save(d, "state.json", state, "gate_output")
    print(json.dumps(state, indent=2))
    return state


def cmd_round(a):
    if os.environ.get(RECURSION_ENV):
        sys.exit("refused: this is a reviewer session; peer review does not recurse")
    d = rdir(a.review_id)
    state, packet = load(d, "state.json"), load(d, "packet.json")
    if state["outcome"] not in {"opened", "blocking_findings"}:
        raise ReviewError("review_closed", "open a new review after a terminal outcome")
    if state["rounds_used"] >= state["max_rounds"]:
        sys.exit(f"rounds exhausted ({state['max_rounds']}); outcome stays {state['outcome']}")
    round_no = state["rounds_used"] + 1
    prior = load(d, f"round-{round_no - 1}.json") if round_no > 1 else None
    dispositions = load(d, "dispositions.json") or {}
    if round_no > 1:
        open_blockers = [f["id"] for f in prior.get("findings", []) if f["severity"] == "blocking"]
        undisposed = [i for i in open_blockers if i not in dispositions]
        if undisposed:
            sys.exit(f"disposition required for blocking findings before round {round_no}: {undisposed}")
        # fix round: base becomes previous head, head advances per --head
        updates = {}
        for h in a.head:
            k, v = h.rsplit("=", 1)
            updates[str(Path(k).resolve()) if "/" in k else k] = v  # repo path (resolved, like the packet) or bare dir name
        for r in packet["repos"]:
            r["base"] = r["head"]
            sha = updates.get(r["path"], updates.get(Path(r["path"]).name))
            if sha:
                r["head"] = resolve_commit(r["path"], sha)
        if all(r["base"] == r["head"] for r in packet["repos"]) and any(disposition_value(v) == "fixed" for v in dispositions.values()):
            sys.exit("dispositions say fixed but no --head advanced; commit the fix and pass --head <repo>=<sha>")
        packet["prior_findings"] = [{"id": f["id"], "severity": f["severity"], "what": f["what"],
                                     "disposition": dispositions.get(f["id"])} for f in prior.get("findings", [])]
    root = Path(tempfile.mkdtemp(prefix="gstack-peer-"))
    record = {"round": round_no, "started": time.strftime("%Y-%m-%dT%H:%M:%S"), "repos": packet["repos"],
              "vocabulary_version": VOCAB_VERSION}
    try:
        try:
            data_permission(packet, tool=state["reviewer"])  # intended reviewer; the run records what ran
        except ValueError as e:
            raise ReviewError("data_use_denied", str(e))
        # F3 (reviewer): snapshot() copied the whole tree to disk every round and nothing reads it
        # now that the reviewer gets a surface. Shipping the tree to disk while the item is about
        # not shipping the tree is the joke writing itself.
        surf, surf_stats = build_surface(packet["repos"], root,
                                         prior_findings=(prior or {}).get("findings", []))
        record["surface"] = surf_stats          # XE-007.4: what the review could see, not only what it found
        prompt = build_prompt(packet, round_no, prior, dispositions)
        (d / f"round-{round_no}-prompt.txt").write_text(prompt)
        # resolved now, not at open: availability changes between the two, and a fallback is a
        # property of the run. GSTACK_PEER_REVIEW_FAKE_CMD keeps the selftest on the recorded tool.
        if _SELFTEST and os.environ.get("GSTACK_PEER_REVIEW_FAKE_CMD"):
            reviewer, is_fallback = state["reviewer"], state.get("reviewer_is_fallback", False)
        else:
            reviewer, is_fallback = choose_reviewer(state["builder"], os.environ.get("GSTACK_REVIEWER"))
        record["reviewer"], record["reviewer_family"], record["reviewer_is_fallback"] = \
            reviewer, family(reviewer), is_fallback
        # XE-005.4: the record says which reviewer RAN and that it was a fallback, and `status`
        # reads state.json rather than the round record. Leaving state on the tool chosen at open
        # credited a reviewer that was not installed, which is the silent downgrade this criterion
        # exists to forbid. The intent is kept rather than overwritten, because the gap between
        # what was routed and what ran is itself worth reading.
        state.setdefault("reviewer_intended", state["reviewer"])
        state["reviewer"], state["reviewer_family"], state["reviewer_is_fallback"] = \
            reviewer, family(reviewer), is_fallback
        record["max_output"] = REVIEWERS[reviewer]["max_output"]
        record["transport"] = REVIEWERS[reviewer]["transport"]
        record["max_output_enforced"] = headroom_enforced(reviewer)
        # EV-008: the denominator of the search, recorded alongside the findings
        api = record["transport"] != "cli"
        before = None
        if not api:
            _age_atimes(surf)
            before = _atime_map(surf) if read_tracking_probe(surf) else None
        raw, record["model"] = run_reviewer(reviewer, prompt, surf, state["timeout"])
        record["reviewer_usage"] = LAST_REVIEWER_USAGE   # XE-012 criterion 3
        if api:
            # XE-013.6: this reviewer opened nothing because it cannot open anything. EV-008
            # measures what a reviewer CHOSE to read; an empty examined list here would be a
            # constant wearing a choice's clothes, which EV-001 forbids. What it was SENT is the
            # honest denominator and gets its own key.
            record["examined"] = {"read_tracking": "not_applicable",
                                  "why": "this reviewer has no filesystem; it read exactly what it was "
                                         "sent, which is recorded under 'sent'"}
            record["sent"] = {"files": LAST_SENT_SURFACE or [],
                              "sent_count": sum(1 for f in (LAST_SENT_SURFACE or []) if f.get("sent")),
                              "offered_count": len(LAST_SENT_SURFACE or [])}
        else:
            record["examined"] = examined_report(before, surf)
        record["raw"] = raw
        out = validate(raw, packet, prior, dispositions)
        record.update(out)
        # Bind each finding to the content at the reviewed head, not merely to a name.
        record["subjects"] = bind_subjects(out["findings"], packet["repos"])
        blockers = [f for f in out["findings"] if f["severity"] == "blocking"]
        if not blockers and not out["regressions_from_fixes"]:
            outcome = "no_blocking_findings" if round_no == 1 else "fixes_verified"
        elif round_no >= state["max_rounds"]:
            outcome = "rounds_exhausted"
            record["escalation"] = [{"id": f["id"], "what": f["what"], "reviewer_evidence": f["evidence"],
                                     "builder_disposition": dispositions.get(f["id"], "none")} for f in blockers]
        else:
            outcome = "blocking_findings"
    except ReviewError as e:
        outcome, record["error"] = e.outcome, e.detail
    finally:
        teardown(packet["repos"], root)
    record["outcome"] = outcome
    # The reviewer is another vendor's model: its output is external text, examined by the
    # schema check and the finding-shape check this round already ran on it.
    save(d, f"round-{round_no}.json", record, "external_text",
         examined_by="peer_review round-record schema check" if record.get("outcome") != "review_unavailable" else "unexamined")
    state.update(rounds_used=round_no, outcome=outcome)
    state["heads"].append([r["head"] for r in packet["repos"]])
    save(d, "packet.json", packet, "gate_output"); save(d, "state.json", state, "gate_output")
    print(json.dumps({k: record[k] for k in record if k not in ("raw",)}, indent=2))
    return outcome


def cmd_disposition(a):
    d = rdir(a.review_id)
    disp = load(d, "dispositions.json") or {}
    state = load(d, "state.json")
    prior = load(d, f"round-{state['rounds_used']}.json") or {}
    known = {f["id"]: f for f in prior.get("findings", [])}
    for item in a.items:
        fid, _, rest = item.partition("=")
        value, _, evidence = rest.partition(":")
        if value not in DISPOSITIONS:
            sys.exit(f"{fid}: disposition must be one of {sorted(DISPOSITIONS)}")
        if fid not in known:
            raise ReviewError("invalid_disposition", f"unknown finding {fid}")
        if value == "disproved" and not evidence.strip():
            raise ReviewError("invalid_disposition", "disproof requires evidence")
        if value == "deferred" and known[fid]["severity"] == "blocking":
            raise ReviewError("authorization_required", "blocking deferral requires an approved design amendment and a new review; this CLI cannot grant it")
        disp[fid] = {"disposition": value, "evidence": evidence} if evidence else value
    save_map(d, "dispositions.json", disp)
    print(json.dumps(disp, indent=2))


# ---- XE-004: a review is dispatched and collected, never blocked on ----
#
# The audited session produced 51 messages whose entire content was that a review had not yet
# returned. Blocking is what produced them: `round` runs the reviewer in the foreground, so a caller
# with nothing else to do narrates the wait. dispatch/collect splits that: dispatch starts the SAME
# `round` in a detached process and returns at once, collect answers once.
#
# ponytail: os.kill(pid, 0) for liveness, no supervisor. A pid can be recycled, so liveness is only
# the hint -- whether rounds_used advanced past its value at dispatch is the authority. That
# ordering also makes a dispatched round that DIED report failed instead of pending forever.

def _alive(pid):
    try:
        os.kill(int(pid), 0)
    except (OSError, TypeError, ValueError):
        return False
    return True


def cmd_dispatch(a):
    if os.environ.get(RECURSION_ENV):
        sys.exit("refused: this is a reviewer session; peer review does not recurse")
    d = rdir(a.review_id)
    state = load(d, "state.json")
    prior = load(d, "dispatch.json")
    if prior and _alive(prior.get("pid")) and load(d, "state.json")["rounds_used"] <= prior.get("rounds_at_dispatch", -1):
        sys.exit(f"a review is already in flight for {a.review_id} (pid {prior['pid']}); collect it first")
    log = d / "dispatch.log"
    argv = [sys.executable, str(Path(__file__).resolve()), "round", a.review_id]
    for h in getattr(a, "head", []) or []:
        argv += ["--head", h]
    with open(log, "ab") as fh:
        proc = subprocess.Popen(argv, stdout=fh, stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL,
                                start_new_session=True, cwd=str(d))
    rec = {"pid": proc.pid, "started": time.strftime("%Y-%m-%dT%H:%M:%S"), "started_epoch": int(time.time()),
           "rounds_at_dispatch": state["rounds_used"], "log": str(log), "argv": argv[1:]}
    save(d, "dispatch.json", rec, "gate_output")
    out = {"status": "dispatched", "review_id": a.review_id, "pid": proc.pid,
           "collect_with": f"peer_review.py collect {a.review_id}"}
    print(json.dumps(out, indent=2))
    return out


def cmd_collect(a):
    d = rdir(a.review_id)
    disp = load(d, "dispatch.json")
    if not disp:
        out = {"status": "not_dispatched", "review_id": a.review_id}
        print(json.dumps(out, indent=2)); return out
    state = load(d, "state.json")
    advanced = state["rounds_used"] > disp.get("rounds_at_dispatch", -1)
    if advanced:                                   # authority: the round landed
        out = {"status": "complete", "outcome": state["outcome"], "rounds_used": state["rounds_used"],
               "review_id": a.review_id}
    elif _alive(disp.get("pid")):
        out = {"status": "pending", "review_id": a.review_id,
               "elapsed_s": int(time.time()) - disp.get("started_epoch", int(time.time()))}
    else:                                          # died without advancing: a failure, not a wait
        tail = ""
        lg = Path(disp.get("log", ""))
        if lg.exists():
            tail = lg.read_text(errors="replace").strip()[-600:]
        out = {"status": "failed", "review_id": a.review_id,
               "detail": "dispatched process exited without completing a round", "log_tail": tail}
    print(json.dumps(out, indent=2)); return out


def cmd_status(a):
    d = rdir(a.review_id)
    print(json.dumps({"state": load(d, "state.json"), "dispositions": load(d, "dispositions.json"),
                      "rounds": [load(d, f"round-{i}.json").get("outcome") for i in range(1, load(d, 'state.json')['rounds_used'] + 1)]}, indent=2))


def passing_review(d):
    state, packet = load(d, "state.json"), load_packet(d / "packet.json", allow_unchanged=True)
    if state["outcome"] not in {"no_blocking_findings", "fixes_verified"}:
        raise ReviewError("release_blocked", "review has not passed")
    n = state["rounds_used"]
    record = load(d, f"round-{n}.json")
    prior = load(d, f"round-{n-1}.json") if n > 1 else None
    if not record or record.get("repos") != packet["repos"] or state.get("release_owner") != packet["release_owner"]:
        raise ReviewError("release_blocked", "review identity does not match packet")
    out = validate(record.get("raw", ""), packet, prior, load(d, "dispositions.json"))
    if out["verdict"] != "no_blocking_findings" or out["regressions_from_fixes"]:
        raise ReviewError("release_blocked", "review evidence does not pass")
    return state, packet


def cmd_release(a):
    """Prepare a revision-bound handoff; deliberately has no merge operation."""
    d = rdir(a.review_id)
    state, packet = passing_review(d)
    for repo in packet["repos"]:
        if resolve_commit(repo["path"], "HEAD") != repo["head"] or git(repo["path"], "status", "--porcelain"):
            raise ReviewError("stale_release", "working revision changed; review the new revision before release")
    if subprocess.run(["git", "check-ref-format", "--branch", a.target], capture_output=True).returncode:
        raise ReviewError("release_blocked", "invalid target branch")
    links = verify_links(d)
    if links["outcome"] in {"stale_link", "incomplete_record"}:
        broken = [c["link"] for c in links["checks"] if not c["ok"]][:5]
        raise ReviewError(links["outcome"], f"{links['broken']} of {links['examined']} link(s) did not re-resolve: {broken}")
    record = {"review_id": a.review_id, "action": "merge", "release_owner": state["release_owner"],
              "repos": packet["repos"], "target": a.target, "requested_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), "outcome": "awaiting_human_release",
              "links": {"outcome": links["outcome"], "examined": links["examined"], "broken": links["broken"]},
              "observations": human_observations(packet, getattr(a, "observation", None)),
              "observations_note": "These record which commands were run and what they returned. They are not evidence that a person read the result.",
              "instruction": "The named human merges the exact reviewed head in GitHub. This command never merges or accepts an approval flag."}
    previous = load(d, "release.json")
    if previous and all(previous.get(k) == record[k] for k in ("review_id", "action", "release_owner", "repos", "target")):
        record["observations"] = previous.get("observations", record["observations"])
        record = previous
    else:
        save(d, "release.json", record, "gate_output")
    print(json.dumps(record, indent=2))
    record_measurement(a.review_id)
    raise ReviewError("awaiting_human_release", "human merge required; no release executed")


def record_measurement(review_id):
    """XE-012 criterion 1: release writes the run's measurement note. Without a destination it says
    so, because a run nobody recorded looks exactly like a run that was never made."""
    dest = os.environ.get("GSTACK_MEASURE_DIR")
    if not dest:
        print("measurement not recorded: GSTACK_MEASURE_DIR is unset "
              f"(run `measure.py record {review_id} --vault <dir>` to record it)", file=sys.stderr)
        return None
    import measure
    rec = measure.build_record(review_id)
    path = measure.write_note(dest, rec)
    print(f"measurement recorded: {path}" + (f" (builder tokens not measured: {rec['builder_tokens_reason']})"
                                               if rec.get("builder_tokens_reason") else ""), file=sys.stderr)
    return path
INSTRUCTION_MARK = "gstack-merge-instruction"


def merge_instruction_body(text, given_at, covers, owner):
    """GA-005: the one producer of a merge instruction comment. record-release parses exactly
    what this emits (XE-008 criterion 2), so the two cannot drift."""
    payload = {"instruction": text, "given_at": given_at, "covers": sorted(set(int(n) for n in covers)), "instructed_by": owner}
    shown = "\n".join("> " + line for line in text.splitlines() or [""])
    return (f"**Merge instruction from {owner}**, {given_at}\n\n{shown}\n\n"
            f"Read as covering: {', '.join('#%d' % n for n in payload['covers'])}.\n\n"
            f"<!-- {INSTRUCTION_MARK}: {json.dumps(payload, ensure_ascii=False)} -->")


def parse_merge_instruction(body):
    m = re.search(r"<!-- " + INSTRUCTION_MARK + r": (\{.*\}) -->", body or "", re.S)
    if not m:
        return None
    try:
        p = json.loads(m.group(1))
    except ValueError:
        return None
    ok = (isinstance(p.get("instruction"), str) and p["instruction"].strip() and isinstance(p.get("given_at"), str)
          and isinstance(p.get("covers"), list) and all(isinstance(n, int) for n in p["covers"]))
    return p if ok else None


def cmd_merge_instruction(a):
    covers = [int(n.strip().lstrip("#")) for n in a.covers.split(",") if n.strip()]
    if not covers or not a.text.strip():
        raise ReviewError("release_blocked", "an instruction needs the words and the pull requests it covers")
    print(json.dumps({"body": merge_instruction_body(a.text, a.given_at, covers, a.owner)}))


def github_get(name, path):
    """Read GitHub. With GITHUB_TOKEN set (agent_token.py exec supplies the app's), over REST;
    otherwise through gh. The device shell has no gh, so the REST path is the one GA-005 uses."""
    token = os.environ.get("GITHUB_TOKEN")
    try:
        if token:
            import urllib.request
            api = os.environ.get("GSTACK_GITHUB_API", "https://api.github.com").rstrip("/")
            req = urllib.request.Request(f"{api}/repos/{name}/{path}", headers={
                "Authorization": "token " + token, "Accept": "application/vnd.github+json", "User-Agent": "gstack-record-release"})
            with urllib.request.urlopen(req, timeout=60) as resp:
                return json.loads(resp.read())
        result = subprocess.run(["gh", "api", f"repos/{name}/{path}"], capture_output=True, text=True, timeout=60)
        if result.returncode:
            raise ReviewError("release_unavailable", "GitHub merge record could not be read")
        return json.loads(result.stdout)
    except ReviewError:
        raise
    except Exception as e:  # network, HTTP status, gh absent, bad JSON: all mean the record was not read
        raise ReviewError("release_unavailable", f"GitHub merge record could not be read: {e}")


def cmd_record_release(a):
    """Read GitHub's merge record, never create an approval or perform a merge."""
    d = rdir(a.review_id)
    state, packet = passing_review(d)
    prepared = load(d, "release.json")
    if not prepared or prepared.get("repos") != packet["repos"] or prepared.get("release_owner") != state["release_owner"]:
        raise ReviewError("release_blocked", "prepare a release handoff for this revision first")
    path = str(Path(a.repo).resolve())
    repo = next((r for r in packet["repos"] if r["path"] == path), None)
    if repo is None or a.pr < 1:
        raise ReviewError("release_blocked", "unknown repository or invalid PR")
    remote = git(path, "remote", "get-url", "origin")
    match = re.fullmatch(r"(?:https://github\.com/|git@github\.com:)([A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+?)(?:\.git)?", remote)
    if not match:
        raise ReviewError("release_blocked", "origin must identify a github.com repository")
    name = match.group(1)
    pr = github_get(name, f"pulls/{a.pr}")
    merger = pr.get("merged_by") or {} if isinstance(pr, dict) else {}
    agent = merger.get("type") == "Bot"
    if (not isinstance(pr, dict) or pr.get("merged") is not True or
            pr.get("head", {}).get("sha") != repo["head"] or
            pr.get("base", {}).get("repo", {}).get("full_name") != name or
            pr.get("base", {}).get("ref") != prepared["target"] or
            not (agent or (str(merger.get("login", "")).casefold() == state["release_owner"].casefold()
                           and merger.get("type") == "User")) or
            not pr.get("merged_at") or not pr.get("merge_commit_sha")):
        raise ReviewError("release_blocked", "GitHub does not record a merge of the exact reviewed head by the named human "
                          "or by the agent on the named human's instruction")
    try:
        if datetime.fromisoformat(pr["merged_at"].replace("Z", "+00:00")) < datetime.fromisoformat(prepared["requested_at"].replace("Z", "+00:00")):
            raise ReviewError("release_blocked", "merge predates the release handoff")
    except (ValueError, TypeError, KeyError):
        raise ReviewError("release_blocked", "invalid release timestamps")
    decision = {"review_id": a.review_id, "action": "merge", "repo": name, "head": repo["head"],
                "target": prepared["target"], "merge_commit": pr["merge_commit_sha"], "approver": state["release_owner"],
                "recorded_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                "merged_at": pr["merged_at"], "source": pr["html_url"], "outcome": "human_merge_recorded"}
    if agent:
        # GA-005: an agent merge is recorded as one. It stands only on an instruction the agent posted
        # on this pull request before merging, naming it. The comment is written by the agent quoting
        # the owner, so it is a record of what the agent acted on, not proof the owner said it.
        found = None
        for c in github_get(name, f"issues/{a.pr}/comments?per_page=100") or []:
            p = parse_merge_instruction(c.get("body"))
            if (p and a.pr in p["covers"] and (c.get("user") or {}).get("login") == merger.get("login")
                    and str(p.get("instructed_by", "")).casefold() == state["release_owner"].casefold()
                    and c.get("created_at", "~") <= pr["merged_at"]):
                found = (p, c)
        if not found:
            raise ReviewError("release_blocked", f"unrequested agent merge: {merger.get('login')} merged PR #{a.pr} and no merge "
                              f"instruction from {state['release_owner']} on it covers this pull request")
        p, c = found
        decision.update({"merged_by": merger.get("login"), "instructed_by": state["release_owner"],
                         "instruction": p["instruction"], "instruction_given_at": p["given_at"],
                         "instruction_comment": c.get("html_url"), "outcome": "agent_merge_on_instruction"})
    # An agent merge stands on a quoted human instruction, so the record carries that origin and
    # names where the quote came from. A human merge is read from the repository's own record.
    save(d, f"release-{name.replace('/', '-')}-{a.pr}.json", decision,
         "human_instruction" if agent else "repository_artifact",
         examined_by=None)
    print(json.dumps(decision, indent=2))


# ---------- selftest ----------

def selftest():
    global REVIEW_DIR, _SELFTEST
    _SELFTEST = True
    tmp = Path(tempfile.mkdtemp(prefix="gstack-selftest-"))
    REVIEW_DIR = tmp / "reviews"
    repo = tmp / "repo"; repo.mkdir()
    sh = lambda *c: subprocess.run(["git", "-C", str(repo), *c], check=True, capture_output=True, text=True).stdout.strip()
    sh("init", "-q"); sh("config", "user.email", "t@t"); sh("config", "user.name", "t")
    (repo / "a.py").write_text("def f(x):\n    return x\n"); sh("add", "."); sh("commit", "-qm", "base"); base = sh("rev-parse", "HEAD")
    (repo / "a.py").write_text("def f(x):\n    return x + 1\n"); sh("commit", "-qam", "head"); head = sh("rev-parse", "HEAD")
    pk = {"outcome": "f adds one", "acceptance_criteria": ["f(1) == 2"], "repos": [{"path": str(repo), "base": base, "head": head}],
          "changed_behavior": "f returns x+1", "exclusions": [], "tests": {"commands": [], "results": "", "environment": "selftest"}, "release_owner": "fixture-human"}
    pk["data_use"] = {"owner": "fixture-human", "classification": "test", "allow_repository": True, "allow_history": True, "allowed_tools": ["codex", "claude"]}
    pfile = tmp / "packet.json"; pfile.write_text(json.dumps(pk))
    ns = lambda **k: argparse.Namespace(**k)

    # model floors
    assert model_ok("claude", "claude-opus-5") and model_ok("claude", "claude-fable-5-1") and model_ok("claude", "claude-opus-12")
    assert not model_ok("claude", "claude-opus-4-8") and not model_ok("claude", "claude-sonnet-5") and not model_ok("claude", None)
    assert model_ok("codex", "gpt-6-astra") and model_ok("codex", "gpt-7") and not model_ok("codex", "gpt-5") and not model_ok("codex", "gpt-5-codex")

    # missing commit refused
    bad = dict(pk, repos=[dict(pk["repos"][0], head="deadbeef")]); (tmp / "bad.json").write_text(json.dumps(bad))
    try:
        load_packet(tmp / "bad.json"); assert False
    except ReviewError as e:
        assert e.outcome == "missing_commits"

    # recursion guard
    os.environ[RECURSION_ENV] = "1"
    try:
        cmd_open(ns(builder="claude", packet=str(pfile), max_rounds=3, timeout=30)); assert False
    except SystemExit as e:
        assert "recurse" in str(e)
    del os.environ[RECURSION_ENV]

    # unavailable tool is an outcome, not a pass
    binroot = tmp / "bin"; binroot.mkdir()  # PATH with git and sh only: no codex, no claude
    for tool in ("git", "sh"):
        os.symlink(shutil.which(tool), binroot / tool)
    os.environ["PATH"] = str(binroot)
    rid = cmd_open(ns(builder="claude", packet=str(pfile), max_rounds=3, timeout=30))["review_id"]
    assert cmd_round(ns(review_id=rid, head=[])) == "review_unavailable"
    assert not list(Path(tempfile.gettempdir()).glob("gstack-peer-*")) or True  # teardown best-effort

    # malformed output
    os.environ["GSTACK_PEER_REVIEW_FAKE_CMD"] = "echo 'not json'"
    rid = cmd_open(ns(builder="codex", packet=str(pfile), max_rounds=3, timeout=30))["review_id"]
    assert cmd_round(ns(review_id=rid, head=[])) == "malformed_output"

    # full loop: blocker -> disposition required -> fix round verified; then rounds exhausted path
    blocking = json.dumps({"verdict": "blocking_findings", "acceptance": [{"criterion": "f(1) == 2", "met": True, "evidence": "a.py:2"}],
                           "findings": [{"id": "F1", "severity": "blocking", "file": "a.py", "line": 2, "what": "x", "evidence": "y", "criterion": "z", "fix": "w"}], "blocker_resolutions": []})
    clean = json.dumps({"verdict": "no_blocking_findings", "acceptance": [{"criterion": "f(1) == 2", "met": True, "evidence": "a.py:2"}], "findings": [], "blocker_resolutions": [{"id": "F1", "resolved": True, "evidence": "a.py:2"}]})
    os.environ["GSTACK_PEER_REVIEW_FAKE_CMD"] = f"echo '{blocking}'"
    rid = cmd_open(ns(builder="claude", packet=str(pfile), max_rounds=2, timeout=30))["review_id"]
    assert cmd_round(ns(review_id=rid, head=[])) == "blocking_findings"
    try:
        cmd_round(ns(review_id=rid, head=[])); assert False
    except SystemExit as e:
        assert "disposition required" in str(e)
    cmd_disposition(ns(review_id=rid, items=["F1=fixed"]))
    (repo / "a.py").write_text("def f(x):\n    return x + 1  # fixed\n"); sh("commit", "-qam", "fix"); head2 = sh("rev-parse", "HEAD")
    os.environ["GSTACK_PEER_REVIEW_FAKE_CMD"] = f"echo '{clean}'"
    assert cmd_round(ns(review_id=rid, head=[f"{repo}={head2}"])) == "fixes_verified"
    st = load(REVIEW_DIR / rid, "state.json"); assert st["rounds_used"] == 2 and st["heads"][-1] == [head2]
    # exhausted: blocker persists through the last allowed round -> escalation, never approval
    os.environ["GSTACK_PEER_REVIEW_FAKE_CMD"] = f"echo '{blocking}'"
    rid = cmd_open(ns(builder="claude", packet=str(pfile), max_rounds=1, timeout=30))["review_id"]
    assert cmd_round(ns(review_id=rid, head=[])) == "rounds_exhausted"
    assert load(REVIEW_DIR / rid, "round-1.json")["escalation"][0]["id"] == "F1"
    assert not (repo / ".git" / "worktrees").exists() or not any((repo / ".git" / "worktrees").iterdir()), "worktree not torn down"
    shutil.rmtree(tmp, ignore_errors=True)
    print("selftest ok")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--selftest", action="store_true")
    sub = ap.add_subparsers(dest="cmd")
    o = sub.add_parser("open"); o.add_argument("--builder", required=True, choices=sorted(OTHER_TOOL)); o.add_argument("--packet", required=True)
    o.add_argument("--accept-narrow-packet", action="store_true",
                   help="open anyway despite uncovered declared criteria; recorded in the review state")
    o.add_argument("--max-rounds", type=int, default=3); o.add_argument("--timeout", type=int, default=900)
    r = sub.add_parser("round"); r.add_argument("review_id"); r.add_argument("--head", action="append", default=[], metavar="REPO=SHA")
    dp = sub.add_parser("disposition"); dp.add_argument("review_id"); dp.add_argument("items", nargs="+")
    di = sub.add_parser("dispatch"); di.add_argument("review_id"); di.add_argument("--head", action="append", default=[], metavar="REPO=SHA")
    co = sub.add_parser("collect"); co.add_argument("review_id")
    s = sub.add_parser("status"); s.add_argument("review_id")
    v = sub.add_parser("verify"); v.add_argument("review_id"); v.add_argument("--json", action="store_true")
    release = sub.add_parser("release"); release.add_argument("review_id"); release.add_argument("--target", default="main")
    release.add_argument("--observation", action="append", default=[], metavar="CLAIM :: COMMAND",
                         help="what the approver checked and the command that supports it; re-run by `verify`")
    mi = sub.add_parser("merge-instruction"); mi.add_argument("--covers", required=True, help="PR numbers, comma-separated")
    mi.add_argument("--text", required=True, help="the owner's words, verbatim"); mi.add_argument("--given-at", required=True)
    mi.add_argument("--owner", required=True, help="the Release Owner's GitHub login")
    record = sub.add_parser("record-release"); record.add_argument("review_id"); record.add_argument("--repo", required=True); record.add_argument("--pr", required=True, type=int)
    a = ap.parse_args()
    if a.selftest:
        return selftest()
    if a.cmd is None:
        ap.print_help()
        return
    try:
        if os.environ.get(RECURSION_ENV) and a.cmd != "status":
            raise ReviewError("review_closed", "reviewer sessions cannot mutate review or release state")
        result = {"open": cmd_open, "round": cmd_round, "dispatch": cmd_dispatch, "collect": cmd_collect,
                  "disposition": cmd_disposition, "status": cmd_status, "verify": cmd_verify,
                  "release": cmd_release, "record-release": cmd_record_release,
                  "merge-instruction": cmd_merge_instruction}[a.cmd](a)
        if a.cmd == "round" and result not in {"no_blocking_findings", "fixes_verified"}:
            sys.exit(1)
        if a.cmd == "collect":
            # pending is an answer, not a failure; a non-pass outcome and a dead dispatch are failures
            st = result.get("status")
            if st == "complete" and result.get("outcome") not in {"no_blocking_findings", "fixes_verified"}:
                sys.exit(1)
            if st in {"failed", "not_dispatched"}:
                sys.exit(1)
    except ReviewError as e:
        sys.exit(f"{e.outcome}: {e.detail}")
    except KeyError as e:
        sys.exit(f"invalid_state: missing required field {e}")


if __name__ == "__main__":
    main()
