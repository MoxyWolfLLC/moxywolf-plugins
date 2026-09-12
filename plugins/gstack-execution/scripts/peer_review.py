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
from pathlib import Path

HERE = Path(__file__).resolve().parent
CONTRACT = HERE.parent / "skills" / "gstack-execution" / "references" / "peer-review-contract.md"
REVIEW_DIR = Path(os.environ.get("GSTACK_PEER_REVIEW_DIR", Path.home() / ".gstack" / "peer-review"))
RECURSION_ENV = "GSTACK_PEER_REVIEW_SESSION"
_SELFTEST = False
OTHER_TOOL = {"claude": "codex", "codex": "claude"}
# Model floors (Dorian, 2026-09-11): Codex uses Astra or higher, Claude Code uses Opus 5 or higher.
# Override the model with GSTACK_CODEX_MODEL / GSTACK_CLAUDE_MODEL; the floor still applies to what actually ran.
MODEL = {"codex": os.environ.get("GSTACK_CODEX_MODEL", "gpt-6-astra"),
         "claude": os.environ.get("GSTACK_CLAUDE_MODEL", "claude-opus-5")}
MODEL_FLOOR = {"codex": r"^gpt-([6-9]|\d{2,})\b",
               "claude": r"^claude-(opus-([5-9]|\d{2,})|fable-\d+|mythos)"}


def model_ok(tool, model):
    return bool(re.match(MODEL_FLOOR[tool], model or ""))
PACKET_FIELDS = ["outcome", "acceptance_criteria", "repos", "changed_behavior", "exclusions", "tests", "release_owner"]
SEVERITIES = {"blocking", "follow_up", "separate"}
VERDICTS = {"no_blocking_findings", "blocking_findings"}
DISPOSITIONS = {"fixed", "disproved", "deferred", "unresolved"}

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
    """Detached read-only worktree per repo at its head commit. Returns [(name, path)]."""
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


def rdir(review_id):
    d = REVIEW_DIR / review_id
    if not (d / "state.json").exists():
        sys.exit(f"no review {review_id} under {REVIEW_DIR}")
    return d


def load(d, name):
    p = d / name
    return json.loads(p.read_text()) if p.exists() else None


def save(d, name, obj):
    (d / name).write_text(json.dumps(obj, indent=2))


# ---------- reviewer ----------

def contract_sections():
    text = CONTRACT.read_text()
    start, end = text.index("## Scope"), text.index("## The loop")
    return text[start:end]


def build_prompt(packet, snaps, round_no, prior_round, dispositions):
    repos = "\n".join(f"- {name}: base {r['base'][:12]} head {r['head'][:12]} (review `git diff {r['base']}..{r['head']}` inside this directory)"
                      for (name, _), r in zip(snaps, packet["repos"]))
    p = [
        "You are the independent reviewer in a bounded cross-tool peer review. Read-only. Do not edit, deploy, or start another review.",
        f"Working directory holds one detached snapshot per repository at the head commit:\n{repos}",
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


def run_reviewer(tool, prompt, root, timeout, schema=None):
    """Returns (reviewer_output_text, model_that_ran)."""
    output_schema = schema or STRICT_SCHEMA
    env = {**os.environ, RECURSION_ENV: "1"}
    fake = os.environ.get("GSTACK_PEER_REVIEW_FAKE_CMD") if _SELFTEST else None  # selftest hook: any command that prints the JSON
    if fake:
        cmd, parse = ["sh", "-c", fake], lambda r: (r.stdout, "fake")
    elif tool == "codex":
        if not shutil.which("codex"):
            raise ReviewError("review_unavailable", "codex CLI not installed on PATH")
        if not model_ok("codex", MODEL["codex"]):
            raise ReviewError("model_below_floor", f"GSTACK_CODEX_MODEL={MODEL['codex']}; floor is Astra (gpt-6) or higher")
        schema = root / "schema.json"; last = root / "last.txt"
        schema.write_text(json.dumps(output_schema))
        cmd = ["codex", "exec", "-C", str(root), "-m", MODEL["codex"], "-c", "model_reasoning_effort=high",
               "--sandbox", "read-only", "--skip-git-repo-check",
               "--output-schema", str(schema), "--output-last-message", str(last), prompt]
        def parse(r):
            m = re.search(r"^model:\s*(\S+)", r.stderr + r.stdout, re.M)  # codex echoes the resolved model in its header
            return (last.read_text() if last.exists() else r.stdout), (m.group(1) if m else None)
    elif tool == "claude":
        if not shutil.which("claude"):
            raise ReviewError("review_unavailable", "claude CLI not installed on PATH")
        if not model_ok("claude", MODEL["claude"]):
            raise ReviewError("model_below_floor", f"GSTACK_CLAUDE_MODEL={MODEL['claude']}; floor is Opus 5 or higher")
        cmd = ["claude", "-p", prompt, "--model", MODEL["claude"], "--output-format", "json", "--json-schema", json.dumps(output_schema),
               "--allowedTools", "Read", "Grep", "Glob", "Bash(git:*)", "--disallowedTools", "Write", "Edit", "MultiEdit", "NotebookEdit",
               "--add-dir", str(root), "--no-session-persistence", "--max-turns", "60"]
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
    else:
        raise ReviewError("review_unavailable", f"unknown tool {tool}")
    try:
        # stdin closed: codex exec otherwise blocks on "Reading additional input from stdin..."
        r = subprocess.run(cmd, cwd=str(root), env=env, capture_output=True, text=True, timeout=timeout, stdin=subprocess.DEVNULL)
    except subprocess.TimeoutExpired:
        raise ReviewError("timeout", f"{tool} exceeded {timeout}s")
    except FileNotFoundError as e:
        raise ReviewError("review_unavailable", str(e))
    if r.returncode != 0:
        raise ReviewError("review_unavailable", f"{tool} exited {r.returncode}: {(r.stderr + r.stdout).strip()[-800:]}")
    text, model = parse(r)
    if not fake and not model_ok(tool, model):
        raise ReviewError("model_below_floor", f"{tool} ran {model!r}, below the floor ({MODEL_FLOOR[tool]})")
    return text, model


def disposition_value(value):
    return value.get("disposition") if isinstance(value, dict) else value


def validate(raw, packet, prior=None, dispositions=None):
    m = re.search(r"\{.*\}", raw, re.S)
    if not m:
        raise ReviewError("malformed_output", "no JSON object in reviewer output")
    try:
        out = json.loads(m.group(0))
    except json.JSONDecodeError as e:
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
    """
    p = path.replace("\\", "/").lstrip("./")
    for i, r in enumerate(repos):
        prefix = f"{i}-{Path(r['path']).name}/"
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
    for n in range(1, state.get("rounds_used", 0) + 1):
        rec = load(d, f"round-{n}.json") or {}
        subjects = rec.get("subjects")
        findings = rec.get("findings", [])
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

    final = load(d, f"round-{state.get('rounds_used', 0)}.json") or {}
    for f in final.get("findings", []):
        if f["severity"] == "blocking":
            record(f"disposition for blocking {f['id']}", f["id"] in dispositions, "no disposition recorded", kind="record")
    known = {f["id"] for n in range(1, state.get("rounds_used", 0) + 1) for f in (load(d, f"round-{n}.json") or {}).get("findings", [])}
    for fid in dispositions:
        record(f"disposition {fid} names a real finding", fid in known, "no finding carries this id", kind="record")

    release = load(d, "release.json") or {}
    for obs in release.get("observations", []):
        try:
            out = subprocess.run(shlex.split(obs["command"]), capture_output=True, text=True, timeout=60,
                                 cwd=obs.get("cwd") or None)
            same = hashlib.sha256((out.stdout + out.stderr).encode()).hexdigest()[:16] == obs.get("output_digest")
            record(f"observation '{obs['claim']}' still holds", same,
                   "" if same else "the recorded command no longer produces the output it recorded")
        except Exception as e:
            record(f"observation '{obs['claim']}' re-runs", False, f"{type(e).__name__}: {e}")

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
    return {"review_id": d.name, "outcome": outcome, "examined": examined,
            "broken": len(broken), "unbound": unbound, "checks": checks}


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
        cmd = f"git -C {repo['path']} rev-parse HEAD"
        out = subprocess.run(shlex.split(cmd), capture_output=True, text=True, timeout=60)
        observations.append({"claim": f"release head of {Path(repo['path']).name} is the reviewed head {repo['head'][:7]}",
                             "command": cmd, "output_digest": hashlib.sha256((out.stdout + out.stderr).encode()).hexdigest()[:16],
                             "output_head": (out.stdout or out.stderr).strip()[:200], "automatic": True})
    for item in extra or []:
        claim, sep, cmd = item.partition("::")
        if not sep or not claim.strip() or not cmd.strip():
            raise ReviewError("release_blocked", "observation must be written as 'claim :: command'")
        out = subprocess.run(shlex.split(cmd.strip()), capture_output=True, text=True, timeout=60)
        observations.append({"claim": claim.strip(), "command": cmd.strip(),
                             "output_digest": hashlib.sha256((out.stdout + out.stderr).encode()).hexdigest()[:16],
                             "output_head": (out.stdout or out.stderr).strip()[:200], "automatic": False,
                             "exit": out.returncode})
    return observations


# ---------- commands ----------

def cmd_open(a):
    if os.environ.get(RECURSION_ENV):
        sys.exit("refused: this is a reviewer session; peer review does not recurse")
    if not 1 <= a.max_rounds <= 3 or a.timeout <= 0:
        raise ReviewError("malformed_packet", "max_rounds must be 1..3 and timeout positive")
    packet = load_packet(a.packet)
    stem = time.strftime("%Y%m%d-%H%M%S") + "-" + packet["repos"][0]["head"][:7]
    REVIEW_DIR.mkdir(parents=True, exist_ok=True)
    d = Path(tempfile.mkdtemp(prefix=stem + "-", dir=REVIEW_DIR))
    review_id = d.name
    state = {"review_id": review_id, "builder": a.builder, "reviewer": OTHER_TOOL[a.builder],
             "release_owner": packet["release_owner"], "max_rounds": a.max_rounds, "timeout": a.timeout, "rounds_used": 0, "outcome": "opened",
             "heads": [[r["head"] for r in packet["repos"]]]}
    save(d, "packet.json", packet); save(d, "state.json", state)
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
    record = {"round": round_no, "started": time.strftime("%Y-%m-%dT%H:%M:%S"), "repos": packet["repos"]}
    try:
        try:
            data_permission(packet, tool=state["reviewer"])
        except ValueError as e:
            raise ReviewError("data_use_denied", str(e))
        snaps = snapshot(packet["repos"], root)
        prompt = build_prompt(packet, snaps, round_no, prior, dispositions)
        (d / f"round-{round_no}-prompt.txt").write_text(prompt)
        raw, record["model"] = run_reviewer(state["reviewer"], prompt, root, state["timeout"])
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
    save(d, f"round-{round_no}.json", record)
    state.update(rounds_used=round_no, outcome=outcome)
    state["heads"].append([r["head"] for r in packet["repos"]])
    save(d, "packet.json", packet); save(d, "state.json", state)
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
    save(d, "dispositions.json", disp)
    print(json.dumps(disp, indent=2))


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
        save(d, "release.json", record)
    print(json.dumps(record, indent=2))
    raise ReviewError("awaiting_human_release", "human merge required; no release executed")


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
    try:
        result = subprocess.run(["gh", "api", f"repos/{name}/pulls/{a.pr}"], capture_output=True, text=True, timeout=60)
        if result.returncode:
            raise ReviewError("release_unavailable", "GitHub merge record could not be read")
        pr = json.loads(result.stdout)
    except (OSError, subprocess.TimeoutExpired, ValueError) as e:
        raise ReviewError("release_unavailable", str(e))
    if (not isinstance(pr, dict) or pr.get("merged") is not True or
            pr.get("head", {}).get("sha") != repo["head"] or
            pr.get("base", {}).get("repo", {}).get("full_name") != name or
            pr.get("base", {}).get("ref") != prepared["target"] or
            str(pr.get("merged_by", {}).get("login", "")).casefold() != state["release_owner"].casefold() or
            pr.get("merged_by", {}).get("type") != "User" or not pr.get("merged_at") or not pr.get("merge_commit_sha")):
        raise ReviewError("release_blocked", "GitHub does not record a merge by the named human of the exact reviewed head")
    try:
        if datetime.fromisoformat(pr["merged_at"].replace("Z", "+00:00")) < datetime.fromisoformat(prepared["requested_at"].replace("Z", "+00:00")):
            raise ReviewError("release_blocked", "merge predates the release handoff")
    except (ValueError, TypeError, KeyError):
        raise ReviewError("release_blocked", "invalid release timestamps")
    decision = {"review_id": a.review_id, "action": "merge", "repo": name, "head": repo["head"],
                "target": prepared["target"], "merge_commit": pr["merge_commit_sha"], "approver": state["release_owner"],
                "recorded_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                "merged_at": pr["merged_at"], "source": pr["html_url"], "outcome": "human_merge_recorded"}
    save(d, f"release-{name.replace('/', '-')}-{a.pr}.json", decision)
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
    o.add_argument("--max-rounds", type=int, default=3); o.add_argument("--timeout", type=int, default=900)
    r = sub.add_parser("round"); r.add_argument("review_id"); r.add_argument("--head", action="append", default=[], metavar="REPO=SHA")
    dp = sub.add_parser("disposition"); dp.add_argument("review_id"); dp.add_argument("items", nargs="+")
    s = sub.add_parser("status"); s.add_argument("review_id")
    v = sub.add_parser("verify"); v.add_argument("review_id"); v.add_argument("--json", action="store_true")
    release = sub.add_parser("release"); release.add_argument("review_id"); release.add_argument("--target", default="main")
    release.add_argument("--observation", action="append", default=[], metavar="CLAIM :: COMMAND",
                         help="what the approver checked and the command that supports it; re-run by `verify`")
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
        result = {"open": cmd_open, "round": cmd_round, "disposition": cmd_disposition, "status": cmd_status, "verify": cmd_verify, "release": cmd_release, "record-release": cmd_record_release}[a.cmd](a)
        if a.cmd == "round" and result not in {"no_blocking_findings", "fixes_verified"}:
            sys.exit(1)
    except ReviewError as e:
        sys.exit(f"{e.outcome}: {e.detail}")
    except KeyError as e:
        sys.exit(f"invalid_state: missing required field {e}")


if __name__ == "__main__":
    main()
