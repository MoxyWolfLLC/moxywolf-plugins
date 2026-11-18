#!/usr/bin/env python3
"""CC-002: Council replay cases, saved by opt-in, redacted, gated, stored in the vault by project (DR-140).

  council_cases.py init      --store S [--writer ID] [--audience TEXT --approved-by NAME --words TEXT]
                             [--exclude SLUG ...] [--projects-root DIR] [--backup NAME ...]
  council_cases.py stage     --input deliberation.json --project SLUG --by NAME --consent yes [--name "text=role" ...]
  council_cases.py scan      <case-id>
  council_cases.py confirm   <case-id> --by NAME --audience TEXT --retention 12m-rule --words TEXT
  council_cases.py publish   <case-id> --store S
  council_cases.py apply     --store S            (the writer device only)
  council_cases.py verify    --store S
  council_cases.py status    --project SLUG --store S       exit 0 ready, 3 not ready
  council_cases.py retire|exclude|delete-record <case-id> --store S [--reason TEXT]
  council_cases.py cleared   <case-id> --where PLACE --store S
  council_cases.py due       --store S
  council_cases.py lookup    <case-id> --store S   the index entry, with pending excludes overlaid

The store is located from the workspace mount, then the Google Drive mount, or --store; with neither
it refuses with `vault not mounted`. There is no Drive API writer (CC-002 amendment, 2026-11-17).

Drive has no atomic append and no compare-and-swap, so the ledger and index have one writer, the
device store.json names. Everyone else drops an immutable, uniquely named request in inbox/, which
`apply` runs in request-time order. Each ledger and index write goes to a temp file renamed over the
old one. verify detects accidental and incomplete changes; it is not tamper evidence.

Readings of the spec review's open ambiguities (CC-002 A1-A12), so a reviewer can check them:
  A1 --retention takes one value, `12m-rule`; the manifest states the rule text, never a role or date.
  A2 an active held-out line's matching date is `null` ("none until retired").
  A3 status runs verify first; a conflict copy stops it with exit 4 and no readiness.
  A4 a published case counts only after `apply` gives it a ledger state.
  A5 the quarter rule is computed at apply, case by case, over the same eligible set status counts,
     including earlier adds in the same batch.
  A6 retire acts on either active role; the date becomes retirement plus 12 calendar months; the line keeps the role.
  A7 publish writes publication time into the staged manifest, gitleaks-scans that final manifest,
     then hashes it into the add request. The manifest never changes after that.
  A8 confirm's --by must equal the staging person and run on the staging device.
  A9 a source identity already in the ledger (any state) or in a pending add is refused, so a
     re-redacted restage can't double-count.
  A12 the manifest gitleaks pass inside publish is the second pass.
ponytail: one JSONL ledger rewritten whole on each apply; fine until a store holds thousands of lines.
"""
import argparse, fcntl, hashlib, json, math, os, re, shutil, subprocess, sys, tempfile, time, uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

RULE_ID = "12m-rule"
RULE = ("A proposal case expires 12 months after publication. An active held-out case has no deletion "
        "date until it is retired, then expires 12 months after retirement.")
STATES = ("active_proposal", "active_held_out", "retired", "excluded", "deleted")
READY_P, READY_H = 15, 5
VERIFY_CLAIM = "verify detects accidental and incomplete changes; it is not tamper evidence."
DEFAULT_EXCLUDED = ["cki", "living-lexicon", "mwe-ner"]
CONFLICT = re.compile(r" \(\d+\)(\.[A-Za-z0-9]+)?$")


class Refused(Exception):
    pass


def now():
    return datetime.now(timezone.utc).replace(microsecond=0)


def iso(t):
    return t.strftime("%Y-%m-%dT%H:%M:%SZ") if t else None


def parse(s):
    return datetime.strptime(s, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc) if s else None


def add_months(t, months=12):
    """Calendar months; a day the target month lacks becomes its last day (29 Feb + 12 months = 28 Feb)."""
    y, m = divmod(t.month - 1 + months, 12)
    y, m = t.year + y, m + 1
    nxt = datetime(y + (m == 12), m % 12 + 1, 1, tzinfo=t.tzinfo)
    return t.replace(year=y, month=m, day=min(t.day, (nxt - timedelta(days=1)).day))


def sha(data):
    return hashlib.sha256(data if isinstance(data, bytes) else data.encode()).hexdigest()


def fsha(p):
    return sha(Path(p).read_bytes())


def atomic_write(path, text):
    """Temp file in the same folder, then rename over the old one."""
    path = Path(path)
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=".tmp-", suffix=path.suffix)
    with os.fdopen(fd, "w") as f:
        f.write(text)
    os.replace(tmp, path)


def jload(p, default=None):
    p = Path(p)
    return json.loads(p.read_text()) if p.exists() else default


def device_id():
    """A random id kept on this device; COUNCIL_CASES_DEVICE overrides it (tests)."""
    if os.environ.get("COUNCIL_CASES_DEVICE"):
        return os.environ["COUNCIL_CASES_DEVICE"]
    p = Path.home() / ".config" / "council-cases" / "device-id"
    if not p.exists():
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(uuid.uuid4().hex + "\n")
    return p.read_text().strip()


def staging_root():
    return Path(os.environ.get("COUNCIL_CASES_STAGING") or Path.home() / "council-case-staging")


PROJECTS_CANDIDATES = [
    Path.home() / "mnt" / "GitHub" / "Projects",
    *Path.home().glob("Library/CloudStorage/GoogleDrive-*/Shared drives/GitHub/Projects"),
]

VAULT_CANDIDATES = [
    Path.home() / "mnt" / "MoxyWolf Vault",
    Path("/mnt/user-data/uploads/MoxyWolf Vault"),
    *Path.home().glob("Library/CloudStorage/GoogleDrive-*/Shared drives/MoxyWolf Shared Files/MoxyWolf Vault"),
]


def store_root(arg):
    """--store, else the workspace mount, else the Google Drive mount. No Drive API writer."""
    if arg:
        return Path(arg)
    for v in VAULT_CANDIDATES:
        if v.is_dir():
            return v / "_Shared Knowledge" / "Agents and Plugins" / "council-cases"
    raise Refused("vault not mounted")


# --- redaction -------------------------------------------------------------------------------
def _session_record_redact():
    """CC-002.3: the secret patterns are session_record.py's, imported, never copied."""
    here = Path(__file__).resolve()
    for root in [here.parents[2] / "project-init" / "scripts", here.parents[3] / "project-init" / "scripts"]:
        if (root / "session_record.py").exists():
            sys.path.insert(0, str(root))
            try:
                from session_record import redact_text
                return redact_text
            finally:
                sys.path.remove(str(root))
    raise Refused("session_record.py not found: the project-init plugin must be installed beside council")


EMAIL = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")
PHONE = re.compile(r"(?<![\w-])(?:\+?\d{1,2}[\s.-]?)?(?:\(\d{3}\)|\d{3})[\s.-]\d{3}[\s.-]\d{4}(?![\w-])")
ACCOUNT = re.compile(r"(?<![\w-])\d(?:[ -]?\d){7,18}(?![\w-])")


def redact(text, names):
    """Secrets, then email/phone/account placeholders (same value, same placeholder), then names."""
    log = []
    text = _session_record_redact()(text, "case.md", log)
    counts = {"secret": len(log)}
    for kind, rx in (("EMAIL", EMAIL), ("PHONE", PHONE), ("ACCOUNT", ACCOUNT)):
        seen = {}
        def sub(m, kind=kind, seen=seen):
            seen.setdefault(m.group(0), f"[{kind}-{len(seen) + 1}]")
            return seen[m.group(0)]
        text = rx.sub(sub, text)
        counts[kind.lower()] = len(seen)
    replaced = []
    per_role = {}
    for raw in names:
        value, _, role = raw.partition("=")
        value, role = value.strip(), (role.strip() or "name").upper()
        if not value:
            continue
        letter = chr(ord("A") + per_role.get(role, 0)); per_role[role] = per_role.get(role, 0) + 1
        ph = f"[{role}-{letter}]"
        n = len(re.findall(re.escape(value), text))
        text = re.sub(re.escape(value), ph, text)
        replaced.append((value, ph, n))
    counts["name"] = len(replaced)
    return text, counts, replaced


# --- the store -------------------------------------------------------------------------------
class Store:
    def __init__(self, root):
        self.root = Path(root)
        self.cfg = jload(self.root / "store.json")
        if self.cfg is None:
            raise Refused(f"no store.json at {self.root}; run init")

    @property
    def ledger_path(self):
        return self.root / "ledger.jsonl"

    def ledger(self):
        p = self.ledger_path
        return [json.loads(l) for l in p.read_text().splitlines() if l.strip()] if p.exists() else []

    def inbox(self):
        """Pending requests in request-time order (time, then the unique name)."""
        d = self.root / "inbox"
        reqs = [(json.loads(p.read_text()), p) for p in d.glob("*.json")] if d.exists() else []
        return sorted(reqs, key=lambda rp: (rp[0]["at"], rp[1].name))

    def request(self, op, case_id, **fields):
        """An immutable, uniquely named change request. Any device may write one."""
        d = self.root / "inbox"; d.mkdir(parents=True, exist_ok=True)
        rid = f"{time.time_ns():020d}-{uuid.uuid4().hex[:12]}"  # sorts in true request order
        req = {"id": rid, "op": op, "case_id": case_id, "at": iso(now()), "device": device_id(), **fields}
        atomic_write(d / f"{rid}.json", json.dumps(req, indent=1) + "\n")
        return req

    def case_dir(self, project, case_id):
        return self.root / project / case_id

    def current(self):
        """case_id -> its latest ledger line."""
        cur = {}
        for line in self.ledger():
            cur[line["case_id"]] = line
        return cur

    def pending(self, op):
        return {r["case_id"]: r for r, _ in self.inbox() if r["op"] == op}

    def conflicts(self):
        hits = []
        for p in [self.root, *[d for d in self.root.iterdir() if d.is_dir()]] if self.root.exists() else []:
            hits += [str(c.relative_to(self.root)) for c in p.iterdir() if CONFLICT.search(c.name)]
        return sorted(set(hits))

    def projects(self):
        skip = {"inbox", "quarantine"}
        return [d for d in self.root.iterdir() if d.is_dir() and d.name not in skip and not d.name.startswith(".")]


def effective_state(store, case_id, line):
    """CC-002.7: a pending exclude is an exclusion from the moment it's written."""
    if case_id in store.pending("exclude"):
        return "excluded"
    return line["state"] if line else None


def verify(store):
    """Read-only. Returns (conflicts, problems)."""
    conflicts = store.conflicts()
    if conflicts:
        return conflicts, []
    problems = []
    writer = store.cfg.get("writer")
    prev = None
    for n, line in enumerate(store.ledger(), 1):
        if line.get("prev") != prev:
            problems.append(f"ledger line {n}: chain broken (previous hash doesn't match)")
        if line.get("writer") != writer:
            problems.append(f"ledger line {n}: writer {line.get('writer')} isn't the store's writer")
        prev = sha(json.dumps(line, sort_keys=True))
    cur = store.current()
    pend_add = store.pending("add")
    pend_del = store.pending("delete-record")
    for cid, line in cur.items():
        d = store.case_dir(line["project"], cid)
        if line["state"] == "deleted" or cid in pend_del:
            continue
        if not d.is_dir():
            problems.append(f"{cid}: folder missing")
            continue
        for name, key in (("case.md", "case_sha256"), ("manifest.json", "manifest_sha256")):
            f = d / name
            if not f.exists() or fsha(f) != line[key]:
                problems.append(f"{cid}: {name} doesn't match the ledger")
    for proj in store.projects():
        for d in proj.iterdir():
            if d.is_dir() and d.name not in cur and d.name not in pend_add:
                problems.append(f"{proj.name}/{d.name}: folder with neither a ledger line nor a pending add")
    return [], problems


# --- commands --------------------------------------------------------------------------------
def opencontrols_projects(projects_root):
    """CC-002.6: any project whose project-surfaces.json names OpenControls."""
    out = []
    for f in Path(projects_root).glob("*/*/project-surfaces.json"):
        try:
            if "OpenControls" in f.read_text():
                pid = json.loads(f.read_text()).get("project_id")
                out += [pid] if pid else []
        except (OSError, ValueError):
            continue
    return out


def cmd_init(a):
    root = store_root(a.store); root.mkdir(parents=True, exist_ok=True)
    cfg = jload(root / "store.json", {})
    cfg.setdefault("schema", "council-cases/1")
    cfg.setdefault("writer", a.writer or device_id())
    excluded = set(cfg.get("excluded_projects", DEFAULT_EXCLUDED)) | set(DEFAULT_EXCLUDED) | set(a.exclude or [])
    roots = [Path(a.projects_root)] if a.projects_root else [r for r in PROJECTS_CANDIDATES if r.is_dir()]
    if not roots or not roots[0].is_dir():
        raise Refused("no readable projects root: pass --projects-root so every OpenControls project is excluded")
    excluded |= set(opencontrols_projects(roots[0]))
    cfg["excluded_projects"] = sorted(excluded)
    cfg["backups"] = sorted(set(cfg.get("backups", [])) | set(a.backup or []))
    if a.audience:
        if not (a.approved_by and a.words):
            raise Refused("an audience is written only with --approved-by and Dorian's --words")
        cfg["audience"] = a.audience
        cfg["audience_approval"] = {"by": a.approved_by, "words": a.words, "at": iso(now())}
    for sub in ("inbox", "inbox/applied", "quarantine"):
        (root / sub).mkdir(parents=True, exist_ok=True)
    atomic_write(root / "store.json", json.dumps(cfg, indent=1) + "\n")
    print(f"store {root}: writer {cfg['writer']}, audience {'approved' if cfg.get('audience') else 'not approved'}, "
          f"excluded {', '.join(cfg['excluded_projects'])}")


def offer_save(store, project, rating):
    """CC-002.1: ask the save question only after a real rating, for a non-excluded project, with an approved audience."""
    return rating not in (None, "skip") and project not in store.cfg.get("excluded_projects", []) and bool(store.cfg.get("audience"))


def render_case(d):
    parts = [f"# Council replay case\n\n## Query\n\n{d['query']}\n\n## Context\n\n{d.get('context') or ''}\n"]
    for r in d.get("responses", []):
        parts.append(f"\n## Response: {r['model']}\n\n{r['text']}\n")
    parts.append(f"\n## Synthesis\n\n{d.get('synthesis') or ''}\n")
    return "".join(parts)


def consented(answer):
    """CC-002.1: only an explicit yes saves; no, the default (nothing chosen) and silence don't."""
    return (answer or "").strip().lower() == "yes"


def cmd_stage(a):
    if not consented(a.consent):
        raise Refused("not saved: the save question wasn't answered yes")
    d = json.loads(Path(a.input).read_text())
    store = Store(store_root(a.store))
    if not offer_save(store, a.project, d.get("rating")):
        raise Refused("not offered: the rating is skip or null, the project is excluded, or no audience is approved")
    text, counts, replaced = redact(render_case(d), a.name or [])
    source = {"workspace": d["workspace"], "record_id": d["record_id"], "query_sha256": sha(d["query"]),
              "deliberated_at": d["deliberated_at"], "models": d.get("models", []),
              "staged_by": a.by, "device": device_id()}
    source_key = sha(json.dumps({k: source[k] for k in ("workspace", "record_id", "query_sha256", "deliberated_at", "models")}, sort_keys=True))
    case_id = sha(text + json.dumps(source, sort_keys=True))[:16]
    folder = staging_root() / case_id
    staging_root().mkdir(mode=0o700, parents=True, exist_ok=True)
    folder.mkdir(mode=0o700, exist_ok=True); os.chmod(folder, 0o700)
    (folder / "case.md").write_text(text)
    manifest = {"schema": "council-case/1", "case_id": case_id, "project": a.project, "rating": d["rating"],
                "source": source, "source_key": source_key, "redaction": counts,
                "retention_rule": RULE, "published_at": None, "confirmation": None}
    (folder / "manifest.json").write_text(json.dumps(manifest, indent=1) + "\n")
    print(f"staged {case_id}: read {folder / 'case.md'} before confirming")
    for value, ph, n in replaced:
        print(f"  replaced {value!r} with {ph} ({n}x)")
    return case_id


def gitleaks(path):
    exe = os.environ.get("COUNCIL_CASES_GITLEAKS") or shutil.which("gitleaks")
    if not exe:
        raise Refused("gitleaks not installed")
    r = subprocess.run([exe, "dir", str(path), "--no-banner", "--redact"], capture_output=True, text=True)
    return r.returncode


def staged(case_id):
    f = staging_root() / case_id
    if not (f / "case.md").exists():
        raise Refused(f"{case_id} isn't staged on this device")
    return f, json.loads((f / "manifest.json").read_text())


def cmd_scan(a):
    folder, _ = staged(a.case_id)
    with tempfile.TemporaryDirectory() as t:
        shutil.copy(folder / "case.md", t)
        rc = gitleaks(t)
    receipt = {"id": uuid.uuid4().hex, "exit_code": rc, "case_sha256": fsha(folder / "case.md"), "at": iso(now())}
    (staging_root() / f"{a.case_id}.scan.json").write_text(json.dumps(receipt) + "\n")
    print("scan: no findings" if rc == 0 else f"scan: findings (gitleaks exit {rc}); edit case.md and scan again")
    return rc


def scan_ok(case_id, folder):
    """Returns the receipt when it's clean and still matches case.md."""
    r = jload(staging_root() / f"{case_id}.scan.json")
    if not r:
        raise Refused("no gitleaks receipt; run scan")
    if r["exit_code"] != 0:
        raise Refused("the scan found secrets")
    if r["case_sha256"] != fsha(folder / "case.md"):
        raise Refused("the scan is stale: case.md changed since")
    return r


STAGED_FILES = ["case.md", "manifest.json"]


def only_staged_files(folder):
    """F3: exactly the two files cross the publish boundary; anything else in the folder refuses."""
    extra = sorted(p.name for p in folder.iterdir() if p.name not in STAGED_FILES)
    if extra:
        raise Refused("unexpected files in the staged case: " + ", ".join(extra))


def cmd_confirm(a):
    folder, m = staged(a.case_id)
    store = Store(store_root(a.store))
    receipt = scan_ok(a.case_id, folder)
    only_staged_files(folder)
    if m["published_at"]:
        raise Refused("already in publication; the manifest no longer changes")
    if a.by != m["source"]["staged_by"] or device_id() != m["source"]["device"]:
        raise Refused("only the person who staged this case, on the device that staged it, confirms it")
    if not store.cfg.get("audience"):
        raise Refused("audience not approved")
    if a.audience != store.cfg["audience"]:
        raise Refused("--audience doesn't match the store's approved audience exactly")
    if a.retention != RULE_ID:
        raise Refused(f"--retention must be {RULE_ID}: the manifest states the rule, not a role or a date")
    files = STAGED_FILES
    m["confirmation"] = {"by": a.by, "audience": a.audience, "retention": RULE_ID, "words": a.words,
                         "at": iso(now()), "files": files, "scan_id": receipt["id"],
                         "case_sha256": receipt["case_sha256"]}
    (folder / "manifest.json").write_text(json.dumps(m, indent=1) + "\n")
    print("will publish:", ", ".join(str(folder / f) for f in files))


def copy_case(folder, dest):
    """Copy to a hidden temp folder beside the destination, then rename it into place."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.parent / f".tmp-{dest.name}-{uuid.uuid4().hex[:6]}"
    tmp.mkdir()
    for f in STAGED_FILES:
        shutil.copy2(folder / f, tmp / f)
    os.replace(tmp, dest)


def cmd_publish(a):
    store = Store(store_root(a.store))
    conflicts, _ = verify(store)
    if conflicts:
        raise Refused("conflict copies in the store: " + ", ".join(conflicts))
    folder, m = staged(a.case_id)
    cid, project = a.case_id, m["project"]
    dest = store.case_dir(project, cid)
    line = store.current().get(cid)
    if cid in store.pending("exclude") or cid in store.pending("delete-record"):
        raise Refused(f"{cid} has a pending exclude or delete-record")
    if line:
        if line["state"].startswith("active"):
            print(f"{cid}: already published"); return
        raise Refused(f"{cid} is {line['state']}")
    pend = store.pending("add").get(cid)
    if pend:
        if dest.is_dir():
            print(f"{cid}: already published (awaiting apply)"); return
        if fsha(folder / "manifest.json") != pend["manifest_sha256"] or fsha(folder / "case.md") != pend["case_sha256"]:
            raise Refused("the staged files no longer match the pending add request")
        copy_case(folder, dest); print(f"{cid}: finished the interrupted copy"); return
    # first publication: every gate holds, in order
    if not store.cfg.get("audience"):
        raise Refused("audience not approved")
    if project in store.cfg.get("excluded_projects", []):
        raise Refused(f"project {project} is excluded")
    receipt = scan_ok(cid, folder)
    only_staged_files(folder)
    c = m.get("confirmation")
    if not c:
        raise Refused("not confirmed; run confirm")
    if c.get("scan_id") != receipt["id"] or c.get("case_sha256") != fsha(folder / "case.md"):
        raise Refused("case.md was edited or rescanned after confirmation; confirm again")
    if c["audience"] != store.cfg["audience"]:
        raise Refused("the confirmed audience isn't the store's approved audience")
    key = m["source_key"]
    for other in store.current().values():
        if other.get("source_key") == key:
            raise Refused(f"this deliberation is already in the store as {other['case_id']} ({other['state']})")
    for other in store.pending("add").values():
        if other.get("source_key") == key:
            raise Refused(f"this deliberation is already pending as {other['case_id']}")
    m["published_at"] = iso(now())
    final = json.dumps(m, indent=1) + "\n"
    with tempfile.TemporaryDirectory() as t:
        (Path(t) / "manifest.json").write_text(final)
        if gitleaks(t) != 0:
            raise Refused("the manifest scan found a secret (check the confirmation's words)")
    (folder / "manifest.json").write_text(final)
    store.request("add", cid, project=project, source_key=key, rating=m["rating"],
                  published_at=m["published_at"], case_sha256=fsha(folder / "case.md"),
                  manifest_sha256=fsha(folder / "manifest.json"))
    copy_case(folder, dest)
    print(f"{cid}: published to {dest}; the writer records it at the next apply")


def rebuild_index(store):
    cur = store.current()
    idx = {"rebuilt_at": iso(now()), "cases": {cid: {k: l.get(k) for k in
           ("project", "state", "role", "delete_after", "rating", "published_at")} for cid, l in cur.items()}}
    atomic_write(store.root / "index.json", json.dumps(idx, indent=1, sort_keys=True) + "\n")


def append_line(store, line):
    lines = store.ledger()
    line["prev"] = sha(json.dumps(lines[-1], sort_keys=True)) if lines else None
    text = "".join(json.dumps(l, sort_keys=True) + "\n" for l in lines + [line])
    atomic_write(store.ledger_path, text)


def apply_one(store, req):
    """Returns a ledger line to write, or None to leave the request pending."""
    cid, op, at = req["case_id"], req["op"], now()
    cur = store.current().get(cid)
    base = {"case_id": cid, "writer": store.cfg["writer"], "at": iso(at), "request": req["id"]}
    if op == "add":
        if cur:
            return "noop"
        d = store.case_dir(req["project"], cid)
        try:
            if fsha(d / "case.md") != req["case_sha256"] or fsha(d / "manifest.json") != req["manifest_sha256"]:
                return None
        except OSError:  # not synced yet, or half-copied: leave it pending
            return None
        cases = [c for c in eligible(store, at) if c[1] == req["project"]]
        held, total = sum(c[2] == "active_held_out" for c in cases), len(cases)
        if held < math.ceil((total + 1) / 4):
            state, after = "active_held_out", None
        else:
            state, after = "active_proposal", iso(add_months(parse(req["published_at"])))
        return {**base, **{k: req[k] for k in ("project", "source_key", "rating", "published_at", "case_sha256", "manifest_sha256")},
                "state": state, "role": state.split("_", 1)[1], "delete_after": after}
    if not cur and op == "delete-record":
        add = store.pending("add").get(cid)
        if not add or store.case_dir(add["project"], cid).exists():
            return None
        return {**base, **{k: add[k] for k in ("project", "source_key", "rating", "published_at", "case_sha256", "manifest_sha256")},
                "role": None, "state": "deleted", "delete_after": None, "remaining": ["drive_trash"] + list(store.cfg.get("backups", [])),
                "cleared": [], "drive_trash_expires": iso(at + timedelta(days=30))}
    if not cur:
        return None
    keep = {k: cur.get(k) for k in ("project", "source_key", "rating", "published_at", "case_sha256", "manifest_sha256", "role")}
    if op == "retire":
        if not cur["state"].startswith("active"):
            return "noop"
        return {**base, **keep, "state": "retired", "delete_after": iso(add_months(at))}
    if op == "exclude":
        if cur["state"] == "deleted":
            return "noop"
        return {**base, **keep, "state": "excluded", "delete_after": iso(at), "reason": req.get("reason")}
    if op == "delete-record":
        if cur["state"] == "deleted":
            return "noop"
        if store.case_dir(cur["project"], cid).exists():
            return None
        remaining = ["drive_trash"] + list(store.cfg.get("backups", []))
        return {**base, **keep, "state": "deleted", "delete_after": cur.get("delete_after"),
                "remaining": remaining, "cleared": [], "drive_trash_expires": iso(at + timedelta(days=30))}
    if op == "cleared":
        if cur["state"] != "deleted":
            return None
        cleared = sorted(set(cur.get("cleared", [])) | {req["where"]})
        return {**base, **keep, **{k: cur.get(k) for k in ("remaining", "drive_trash_expires", "delete_after")},
                "state": "deleted", "cleared": cleared}
    raise Refused(f"unknown request op {op}")


def apply_lock(store):
    """An exclusive lock on this device, held for the whole apply. The lock file is local, not on Drive,
    because only the writer device applies; a second apply on it waits for nothing and refuses."""
    d = Path.home() / ".config" / "council-cases"; d.mkdir(parents=True, exist_ok=True)
    f = open(d / f"apply-{sha(str(store.root.resolve()))[:16]}.lock", "w")
    try:
        fcntl.flock(f, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        f.close(); raise Refused("another apply is running on this device")
    return f


def cmd_apply(a):
    store = Store(store_root(a.store))
    if device_id() != store.cfg["writer"]:
        raise Refused(f"apply runs only on the writer device {store.cfg['writer']}")
    lock = apply_lock(store)
    try:
        return _apply(store)
    finally:
        lock.close()


def _apply(store):
    conflicts, problems = verify(store)
    if conflicts:
        raise Refused("conflict copies in the store: " + ", ".join(conflicts))
    if any("chain broken" in p or "isn't the store's writer" in p for p in problems):
        raise Refused("the ledger fails verify; repair it by hand first: " + "; ".join(problems))
    rebuild_index(store)  # recovers an apply interrupted between ledger and index
    applied_ids = {l.get("request") for l in store.ledger()}
    (store.root / "inbox" / "applied").mkdir(parents=True, exist_ok=True)
    n = 0
    for _ in range(2):  # a second pass retires an add that a tombstone in the first pass made moot
        for req, path in store.inbox():
            if req["id"] not in applied_ids:
                line = apply_one(store, req)
                if line is None:
                    continue
                if line != "noop":
                    append_line(store, line); n += 1; applied_ids.add(req["id"])
            os.replace(path, store.root / "inbox" / "applied" / path.name)
    rebuild_index(store)
    _, problems = verify(store)
    for p in problems:
        if "neither a ledger line nor a pending add" in p:
            rel = p.split(":")[0]
            q = store.root / "quarantine" / rel.replace("/", "__")
            os.replace(store.root / rel, q); print(f"quarantined {rel}")
    print(f"applied {n} ledger line(s); {len(store.inbox())} request(s) still pending")


def cmd_verify(a):
    store = Store(store_root(a.store))
    conflicts, problems = verify(store)
    print(VERIFY_CLAIM)
    if conflicts:
        print("conflict copies: " + ", ".join(conflicts)); return 4
    for p in problems:
        print("problem: " + p)
    print(f"verify: {'ok' if not problems else f'{len(problems)} problem(s)'}")
    return 1 if problems else 0


def eligible(store, at):
    """CC-002.10: published (has a ledger state), rated, full query and context, active, in date, verifies."""
    _, problems = verify(store)
    bad = {p.split(":")[0] for p in problems}
    out = []
    for cid, l in store.current().items():
        st = effective_state(store, cid, l)
        if st not in ("active_proposal", "active_held_out") or cid in store.pending("delete-record") or cid in bad:
            continue
        if l.get("delete_after") and parse(l["delete_after"]) <= at:
            continue
        d = store.case_dir(l["project"], cid)
        m = jload(d / "manifest.json", {})
        text = (d / "case.md").read_text() if (d / "case.md").exists() else ""
        q = re.search(r"## Query\n\n(.+?)\n\n## Context\n\n(.*?)\n\n## ", text, re.S)
        if m.get("rating") is None or not q or not q.group(1).strip():
            continue
        out.append((cid, l["project"], st))
    return out


def cmd_status(a):
    store = Store(store_root(a.store))
    conflicts, _ = verify(store)
    if conflicts:
        print(VERIFY_CLAIM); print("conflict copies: " + ", ".join(conflicts) + "; no readiness until they're resolved")
        return 4
    _, problems = verify(store)
    glob = [p for p in problems if p.startswith("ledger line")]
    if glob:
        print(VERIFY_CLAIM); print("ledger fails verify: " + "; ".join(glob) + "; no readiness until it's repaired")
        return 1
    cases = [c for c in eligible(store, now()) if c[1] == a.project]
    p = sum(c[2] == "active_proposal" for c in cases)
    h = sum(c[2] == "active_held_out" for c in cases)
    waiting = len(store.inbox())
    print(f"{a.project}: {p} eligible proposal, {h} eligible held-out; {waiting} request(s) awaiting apply")
    print("thresholds 15 proposal / 5 held-out are an operational starting point.")
    if p >= READY_P and h >= READY_H:
        print("ready"); return 0
    print(f"not ready: {p}/{READY_P} proposal, {h}/{READY_H} held-out"); return 3


def cmd_change(a):
    store = Store(store_root(a.store))
    cur = store.current().get(a.case_id)
    if not cur and a.case_id not in store.pending("add"):
        raise Refused(f"{a.case_id} isn't in the store")
    if a.op == "delete-record":
        proj = cur["project"] if cur else store.pending("add")[a.case_id]["project"]
        if store.case_dir(proj, a.case_id).exists():
            raise Refused("delete the case folder first; delete-record only records a deletion")
    fields = {"reason": a.reason} if a.op == "exclude" else {}
    if a.op == "exclude" and not a.reason:
        raise Refused("exclude needs --reason")
    if a.op == "cleared":
        fields = {"where": a.where}
    store.request(a.op, a.case_id, **fields)
    print(f"{a.op} {a.case_id}: requested; readers honour a pending exclude at once")


def lookup(store, case_id):
    """Index lookup for every reader: the index entry with pending exclude and delete-record overlaid."""
    entry = dict((jload(store.root / "index.json", {}).get("cases") or {}).get(case_id) or {})
    if case_id in store.pending("exclude"):
        entry["state"] = "excluded"
    if not entry and case_id in store.pending("add"):
        entry = {"state": "pending_add", "project": store.pending("add")[case_id]["project"]}
    return entry or {"state": "unknown"}


def cmd_lookup(a):
    store = Store(store_root(a.store))
    print(json.dumps({"case_id": a.case_id, **lookup(store, a.case_id)}))


def cmd_due(a):
    store = Store(store_root(a.store)); at = now()
    for cid, l in sorted(store.current().items()):
        st = effective_state(store, cid, l)
        if st == "deleted":
            left = sorted(set(l.get("remaining", [])) - set(l.get("cleared", [])))
            if left:
                print(f"{cid}\tdeleted, not fully removed: clear {', '.join(left)}")
            continue
        if st == "excluded" or (l.get("delete_after") and parse(l["delete_after"]) <= at):
            print(f"{cid}\t{l['project']}\t{st}\tdue for deletion (delete the folder, then delete-record)")


def fully_removed(line):
    return line["state"] == "deleted" and set(line.get("remaining", [])) <= set(line.get("cleared", []))


def main(argv=None):
    ap = argparse.ArgumentParser(description="Council replay cases (CC-002)")
    sp = ap.add_subparsers(dest="cmd", required=True)
    def sub(name, *args, case=False):
        p = sp.add_parser(name); p.add_argument("--store")
        if case:
            p.add_argument("case_id")
        return p
    p = sub("init"); p.add_argument("--writer"); p.add_argument("--audience"); p.add_argument("--approved-by")
    p.add_argument("--words"); p.add_argument("--exclude", action="append"); p.add_argument("--projects-root")
    p.add_argument("--backup", action="append", help="a backup holding store copies; each must be cleared after a deletion")
    p = sub("stage"); p.add_argument("--input", required=True); p.add_argument("--project", required=True)
    p.add_argument("--by", required=True); p.add_argument("--name", action="append")
    p.add_argument("--consent", help="the person's answer to the save question; only `yes` stages")
    sub("scan", case=True)
    p = sub("confirm", case=True); p.add_argument("--by", required=True); p.add_argument("--audience", required=True)
    p.add_argument("--retention", required=True); p.add_argument("--words", required=True)
    sub("publish", case=True); sub("apply"); sub("verify"); sub("due"); sub("lookup", case=True)
    p = sub("status"); p.add_argument("--project", required=True)
    for op in ("retire", "exclude", "delete-record", "cleared"):
        p = sub(op, case=True); p.add_argument("--reason"); p.add_argument("--where", required=op == "cleared")
        p.set_defaults(op=op)
    a = ap.parse_args(argv)
    fn = {"init": cmd_init, "stage": cmd_stage, "scan": cmd_scan, "confirm": cmd_confirm, "publish": cmd_publish,
          "apply": cmd_apply, "verify": cmd_verify, "status": cmd_status, "due": cmd_due, "lookup": cmd_lookup}.get(a.cmd, cmd_change)
    try:
        rc = fn(a)
    except Refused as e:
        print(f"refused: {e}", file=sys.stderr); return 2
    return rc if isinstance(rc, int) and a.cmd in ("verify", "status", "scan") else 0


if __name__ == "__main__":
    sys.exit(main())
