#!/usr/bin/env python3
"""EV-011: an open question is a record with a revision, not a sentence in a finding.

  unknowns.py record --repo <path> --question "<text>" --needs <authority> --raised-by "<round or node>"
                     [--for <evidence id>...] [--against <evidence id>...]
      append a new unknown at revision 1, state open, naming what raised it; print its id.
  unknowns.py update --repo <path> --id <id> --revision <n> [--question ...] [--needs ...] [--for ...] [--against ...]
      append revision n+1 only when n is the newest stored revision; otherwise stale_revision, nothing written.
  unknowns.py close  --repo <path> --id <id> --revision <n> --evidence <ref> [--review <review id>]
      append a closed revision only when the evidence exists and its authority is at least what the
      unknown needs; otherwise authority_insufficient, nothing written.
  unknowns.py list   --repo <path> --branch <name> [--state open|closed]
      every current head in id order, then a count. With --state open, exit 1 when any is open.

Authorities, weakest first: repository (a reviewer finding citing file:line), ci_run (a CI run at the
reviewed head), runtime (a check that ran through check_ledger.py), human (a named person).
Evidence references: `round:<review id>:<n>:<finding id>` (repository), `ci:<review id>:<run id>`
(ci_run, head_matches and conclusion success), `ledger:<id>` (runtime, exit 0), `human:<review id>:<index>` (human:
an observation a person entered on that review's release handoff, EV-004; a bare login is not a record).

The ledger is `<review_root()>/unknowns/<owner>-<repo>/<branch>.jsonl`, under the declared review
directory (EV-009) and nowhere else. The newest line for an id is its current state; a line with a
stale revision is refused before it is written, which is what lets the reader trust the newest line.

The record shape and the revision rule are from morluto/rea at 7a6defa (MIT), whose record_unknown and
update_unknown keep unresolved questions as session state. No code copied; its registry and MCP tools
aren't taken.

ponytail: stdlib, one JSONL file per branch, linear scans. Fine until a branch carries thousands.
"""
import argparse
import contextlib
import fcntl
import hashlib
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import check_ledger as cl  # noqa: E402  repo_key, repo_id, branch_of: one convention
import peer_review as pr   # noqa: E402  review_root(), vocabulary

SHAPE = pr.vocab_shape("unknown")
NEEDS, STATES = SHAPE["needs"], SHAPE["states"]
RANK = {a: i for i, a in enumerate(NEEDS)}   # weakest first


def path(repo, branch, root):
    return Path(root) / "unknowns" / cl.repo_key(repo) / f"{branch}.jsonl"


def read(p):
    rows = []
    for n, line in enumerate(p.read_text().splitlines(), 1) if p.exists() else ():
        if line.strip():
            try:
                rows.append(json.loads(line))
            except ValueError:
                raise SystemExit(f"refused: {p} line {n} is not JSON; the ledger can't be read")
    return rows


def heads(rows, rid):
    """id -> newest line, for this repository only (a colliding directory name is not this repo)."""
    out = {}
    for r in rows:
        if r.get("repo") == rid and r.get("revision", 0) >= out.get(r["id"], {}).get("revision", 0):
            out[r["id"]] = r
    return out


def append(p, row):
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("a") as f:
        f.write(json.dumps(row) + "\n")


@contextlib.contextmanager
def locked(p):
    """F4 (review 20261013-124809): read, check and append are one transaction per ledger. Two
    writers that both read revision 1 would both have appended revision 2; under the lock the
    second one reads 2 and is refused."""
    p.parent.mkdir(parents=True, exist_ok=True)
    with (p.parent / (p.name + ".lock")).open("a") as lk:
        fcntl.flock(lk, fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(lk, fcntl.LOCK_UN)


def _ledger(repo, root=None):
    """root is passed by peer_review.py, whose own review_root() is the one that was set: when it
    runs as __main__, this module's `pr` is a second instance with no REVIEW_DIR (CI run 38456179646)."""
    b = cl.branch_of(repo)
    if not b:
        raise SystemExit(f"refused: {repo} is not a git checkout on a branch")
    return b, path(repo, b, root or pr.review_root())


def _ctx(repo, root=None):
    """Current heads, read under no lock: callers that write take `locked(p)` and reread inside it."""
    b, p = _ledger(repo, root)
    return b, p, heads(read(p), cl.repo_id(repo))


def new_id(repo, question, raised_by):
    return hashlib.sha256(f"{cl.repo_id(repo)}\0{raised_by}\0{question.strip()}".encode()).hexdigest()[:12]


def record(repo, question, needs, raised_by, for_=(), against=(), head=None, root=None):
    """Append an open unknown, or return the existing id when the same question was raised by the
    same party before: a round that repeats itself doesn't open a second record. `raised_by` names
    the round or node that raised it and has no default (F6, review 20261013-124809)."""
    if needs not in NEEDS:
        raise SystemExit(f"refused: --needs must be one of {NEEDS}")
    if not question.strip():
        raise SystemExit("refused: an unknown needs its question")
    if not (raised_by or "").strip():
        raise SystemExit("refused: --raised-by must name the round or node that raised the question")
    b, p = _ledger(repo, root)
    with locked(p):
        cur = heads(read(p), cl.repo_id(repo))
        uid = new_id(repo, question, raised_by)
        if uid in cur:
            return uid, False
        append(p, {"id": uid, "revision": 1, "state": "open", "question": question.strip(), "needs": needs,
                   "for": list(for_), "against": list(against), "raised_by": raised_by,
                   "head": head or cl._git(repo, "rev-parse", "HEAD"), "repo": cl.repo_id(repo), "at": time.time()})
    return uid, True


def _next(cur, uid, revision):
    if uid not in cur:
        raise pr.ReviewError("stale_revision", f"no unknown {uid} on this branch")
    newest = cur[uid]["revision"]
    if revision != newest:
        raise pr.ReviewError("stale_revision", f"{uid} is at revision {newest}, not {revision}; reread it: "
                                              + json.dumps(cur[uid]))
    if cur[uid]["state"] == "closed":
        raise pr.ReviewError("stale_revision", f"{uid} is closed at revision {newest}")
    return dict(cur[uid], revision=newest + 1, at=time.time())


def update(repo, uid, revision, **changes):
    b, p = _ledger(repo)
    with locked(p):
        cur = heads(read(p), cl.repo_id(repo))
        row = _next(cur, uid, revision)
        for k, v in changes.items():
            if v is not None:
                row[k] = v
        if row["needs"] not in NEEDS:
            raise SystemExit(f"refused: --needs must be one of {NEEDS}")
        append(p, row)
    return row


def evidence_authority(ref, repo, review=None):
    """What authority an evidence reference carries, or None when it doesn't exist. Existence is
    checked against the record it names, never taken from the caller's word."""
    kind, _, rest = ref.partition(":")
    root = pr.review_root()
    if kind == "human":
        # F3 (review 20261013-124809): a login is a name, not a record. A person's evidence is an
        # observation they entered on a release handoff (EV-004), `human:<review id>:<index>` into
        # that review's release.json observations, and only one a person wrote, never the automatic
        # head check.
        review_id, _, idx = rest.partition(":")
        q = root / review_id / "release.json"
        if not idx.isdigit() or not q.exists():
            return None
        obs = (json.loads(q.read_text()).get("observations") or [])
        i = int(idx)
        return "human" if i < len(obs) and not obs[i].get("automatic") else None
    if kind == "ledger":
        for r in cl.read(cl.ledger_path(repo, cl.branch_of(repo), root)) if cl.ledger_path(repo, cl.branch_of(repo), root).exists() else ():
            if r.get("id") == rest and r.get("repo") == cl.repo_id(repo):
                return "runtime" if r.get("exit_code") == 0 else None
        return None
    if kind == "ci":
        review_id, _, run_id = rest.partition(":")
        # the dispatcher's fetched run record is what proves a run: XE-018 writes one per run per round
        for q in (root / review_id).glob("round-*.json") if (root / review_id).exists() else ():
            rec = json.loads(q.read_text())
            for c in rec.get("ci_runs") or []:
                if str(c.get("run_id")) == run_id and c.get("head_matches") and c.get("conclusion") == "success":
                    return "ci_run"
        return None
    if kind == "round":
        review_id, _, rest2 = rest.partition(":")
        n, _, fid = rest2.partition(":")
        q = root / review_id / f"round-{n}.json"
        if q.exists():
            rec = json.loads(q.read_text())
            if any(f.get("id") == fid for f in rec.get("findings") or []):
                return "repository"
        return None
    return None


def close(repo, uid, revision, evidence, review=None):
    b, p = _ledger(repo)
    with locked(p):
        cur = heads(read(p), cl.repo_id(repo))
        row = _next(cur, uid, revision)
        have = evidence_authority(evidence, repo, review)
        if have is None:
            raise pr.ReviewError("authority_insufficient", f"evidence {evidence!r} does not exist in the records it names")
        if RANK[have] < RANK[row["needs"]]:
            raise pr.ReviewError("authority_insufficient", f"{uid} needs {row['needs']}; {evidence!r} carries {have}")
        row.update(state="closed", closed_by=evidence, closed_authority=have)
        append(p, row)
    return row


def current(repo, branch=None, root=None):
    """The newest line per id, for peer_review: [] with no ledger, never None-as-zero."""
    b = branch or cl.branch_of(repo)
    if not b:
        return []
    p = path(repo, b, root or pr.review_root())
    return sorted(heads(read(p), cl.repo_id(repo)).values(), key=lambda r: r["id"]) if p.exists() else []


def cmd_list(repo, branch, state=None):
    rows = [r for r in current(repo, branch) if state in (None, r["state"])]
    for r in rows:
        print(f"{r['state']:6} {r['id']} r{r['revision']} needs {r['needs']}: {r['question']}")
    n_open = sum(1 for r in rows if r["state"] == "open")
    print(f"{len(rows)} unknown{'s' if len(rows) != 1 else ''} listed, {n_open} open, in {path(repo, branch, pr.review_root())}")
    return 1 if state == "open" and n_open else 0


def main(argv):
    ap = argparse.ArgumentParser(prog="unknowns.py")
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("record"); r.add_argument("--repo", required=True); r.add_argument("--question", required=True)
    r.add_argument("--needs", required=True); r.add_argument("--for", dest="for_", action="append", default=[])
    r.add_argument("--against", action="append", default=[])
    r.add_argument("--raised-by", required=True, help="the round or node that raised it, e.g. '<review id> round 2' or 'node check'")
    u = sub.add_parser("update"); u.add_argument("--repo", required=True); u.add_argument("--id", required=True)
    u.add_argument("--revision", type=int, required=True); u.add_argument("--question"); u.add_argument("--needs")
    u.add_argument("--for", dest="for_", action="append"); u.add_argument("--against", action="append")
    c = sub.add_parser("close"); c.add_argument("--repo", required=True); c.add_argument("--id", required=True)
    c.add_argument("--revision", type=int, required=True); c.add_argument("--evidence", required=True); c.add_argument("--review")
    l = sub.add_parser("list"); l.add_argument("--repo", required=True); l.add_argument("--branch", required=True)
    l.add_argument("--state", choices=STATES)
    a = ap.parse_args(argv)
    try:
        if a.cmd == "record":
            uid, created = record(a.repo, a.question, a.needs, a.raised_by, a.for_, a.against)
            print(uid + ("" if created else "  (already open; not duplicated)"))
            return 0
        if a.cmd == "update":
            print(json.dumps(update(a.repo, a.id, a.revision, question=a.question, needs=a.needs,
                                    **{"for": a.for_, "against": a.against})))
            return 0
        if a.cmd == "close":
            print(json.dumps(close(a.repo, a.id, a.revision, a.evidence, a.review)))
            return 0
        return cmd_list(a.repo, a.branch, a.state)
    except pr.ReviewError as e:
        print(f"{e.outcome}: {e.detail}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
