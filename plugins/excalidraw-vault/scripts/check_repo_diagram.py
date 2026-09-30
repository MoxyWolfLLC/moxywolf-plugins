#!/usr/bin/env python3
"""DG-001: check a repo-backed .excalidraw.md note against the commit it pins. Stdlib only.

Usage: check_repo_diagram.py <note> --repo <path>

Validates the citations as history at repo_head, never the working tree. Drift against the
repo's current HEAD is printed separately and never changes the exit code.
Exit 0 only when every check passes and at least one element was examined.
"""
import argparse, json, re, subprocess, sys
from pathlib import Path

CLAIM_TYPES = {"rectangle", "ellipse", "diamond", "arrow", "line"}
USERINFO = re.compile(r"^([a-z][a-z0-9+.-]*://)[^/@]+@", re.I)
SOURCE = re.compile(r"^(.+):(\d+)-(\d+)$")


def clean_origin(url):
    return USERINFO.sub(r"\1", url.strip())


def git(repo, *args):
    r = subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True)
    return r.returncode, r.stdout


def frontmatter(text):
    m = re.match(r"---\n(.*?)\n---\n", text, re.S)
    fm = {}
    for line in (m.group(1).splitlines() if m else []):
        k, sep, v = line.partition(":")
        if sep:
            fm[k.strip()] = v.strip().strip("'\"")
    return fm


def drawing(text):
    if "```compressed-json" in text:
        return None, "drawing is compressed-json; decompress it in Obsidian ('Decompress current Excalidraw file') and re-run"
    m = re.search(r"## Drawing\s*```json\s*\n(.*?)\n```", text, re.S)
    if not m:
        return None, "no ```json drawing block under '## Drawing'"
    try:
        return json.loads(m.group(1)), None
    except ValueError as e:
        return None, f"drawing JSON does not parse: {e}"


def claim_ids(doc):
    ids = []
    for el in doc.get("elements", []):
        if el.get("isDeleted") or el.get("type") not in CLAIM_TYPES:
            continue
        if (el.get("customData") or {}).get("claim") is False:
            continue
        ids.append(el["id"])
    return ids


def source_rows(text):
    """[(element, claim, source)] from the '## Sources' table."""
    m = re.search(r"^## Sources\s*\n(.*?)(?=^#|\Z)", text, re.S | re.M)
    rows = []
    for line in (m.group(1).splitlines() if m else []):
        line = line.strip()
        if not line.startswith("|"):
            continue
        cells = [c.strip().strip("`").strip() for c in line.strip("|").split("|")]
        if len(cells) < 3 or set("".join(cells)) <= set("-: ") or cells[0].lower() == "element":
            continue
        rows.append((cells[0], cells[1], cells[2]))
    return rows


def check(note, repo):
    """(failures, info, examined) -- failures and info are lists of strings."""
    text = Path(note).read_text(encoding="utf-8")
    fails, info = [], []
    fm = frontmatter(text)
    doc, err = drawing(text)
    if err:
        return [err], info, 0

    head = fm.get("repo_head", "")
    if not re.fullmatch(r"[0-9a-f]{40}", head):
        fails.append(f"repo_head {head!r} is not 40 hex characters")
    elif git(repo, "cat-file", "-e", f"{head}^{{commit}}")[0] != 0:
        fails.append(f"repo_head {head} does not exist in {repo}")
        head = ""
    origin = fm.get("repo_origin", "")
    if not origin:
        fails.append("repo_origin is missing")
    elif clean_origin(origin) != origin:
        fails.append("repo_origin carries userinfo (a user, password or token)")
    rc, actual = git(repo, "remote", "get-url", "origin")
    if origin and (rc != 0 or clean_origin(actual) != clean_origin(origin)):
        fails.append(f"repo_origin {clean_origin(origin)!r} does not match --repo's origin {clean_origin(actual) or '(none)'!r}")

    ids, rows = claim_ids(doc), source_rows(text)
    seen = {}
    for el, _, _ in rows:
        seen[el] = seen.get(el, 0) + 1
    for el in ids:
        if el not in seen:
            fails.append(f"element {el}: drawn with no Sources row")
    for el, n in seen.items():
        if n > 1:
            fails.append(f"element {el}: {n} Sources rows, expected one")
        if el not in ids:
            fails.append(f"row {el}: no such claim element in the drawing")

    lines_at = {}
    ok_head = re.fullmatch(r"[0-9a-f]{40}", head or "")
    for el, _, src in rows:
        if src.lower() == "unknown":
            continue
        m = SOURCE.match(src)
        if not m:
            fails.append(f"row {el}: source {src!r} is not path:start-end or unknown")
            continue
        path, start, end = m.group(1), int(m.group(2)), int(m.group(3))
        if not ok_head:
            continue
        if path not in lines_at:
            kind = git(repo, "cat-file", "-t", f"{head}:{path}")[1].strip()
            rc, body = git(repo, "show", f"{head}:{path}") if kind == "blob" else (1, "")
            lines_at[path] = (len(body.splitlines()) if rc == 0 else None, kind)
        n, kind = lines_at[path]
        if kind and kind != "blob":
            fails.append(f"row {el}: {path} is a {kind} at {head[:7]}, not a file")
        elif n is None:
            fails.append(f"row {el}: {path} does not exist at {head[:7]}")
        elif not 1 <= start <= end <= n:
            fails.append(f"row {el}: lines {start}-{end} outside {path} (1-{n} at {head[:7]})")

    if ok_head:
        cur = git(repo, "rev-parse", "HEAD")[1].strip()
        info.append(f"current HEAD {cur[:7]}" + ("" if cur == head else f", repo_head {head[:7]}"))
        if cur and cur != head:
            changed = set(git(repo, "diff", "--name-only", "-z", head, cur)[1].split("\0")) - {""}
            cited = {SOURCE.match(s).group(1) for _, _, s in rows if SOURCE.match(s)}
            for p in sorted(cited & changed):
                info.append(f"drift (not a failure): {p} changed since {head[:7]}")
    examined = len(ids) + len(rows)
    if examined == 0:
        fails.append("checked 0 elements and 0 rows; nothing was examined")
    return fails, info, examined


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("note")
    ap.add_argument("--repo", required=True)
    a = ap.parse_args(argv)
    fails, info, _ = check(a.note, a.repo)
    text = Path(a.note).read_text(encoding="utf-8")
    d, _ = drawing(text)
    print(f"checked {len(claim_ids(d)) if d else 0} claim elements and {len(source_rows(text))} Sources rows")
    for f in fails:
        print(f"FAIL {f}")
    for i in info:
        print(f"info {i}")
    print("PASS" if not fails else f"{len(fails)} failure(s)")
    return 0 if not fails else 1


if __name__ == "__main__":
    sys.exit(main())
