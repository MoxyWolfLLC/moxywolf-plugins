#!/usr/bin/env python3
"""BP-001: register a pillar's hub term in @moxywolf/hub-links, and pin it in a target repo.

  hub_term.py register --hub-links <path> --term <phrase> --owner <site> --site-url <url> --path <hub path>
  hub_term.py pin      --repo <path> --site <slug> --file <auto_linker_file>

Exit codes: 0 done (or already registered); 1 refused, with the reason on stderr; 2 usage.

register adds the site to SITES when it's missing, one HUB_LINKS entry before the "future pillar
terms" marker, and a test asserting the relative link on the owner and the absolute link elsewhere.
It then builds and tests the package. A failing build or test restores the files and commits
nothing. On success it commits, pushes through ship.py's push (moxywolf-agent on GitHub) and pulls
back. A phrase an existing pattern already matches is a no-op.
pin     updates the target's hub-links pin with the repo's own package manager, then checks that the
        renderer file passes site: '<slug>'. A mismatch is refused, naming both slugs; the renderer is
        never rewritten here.

ponytail: TypeScript is edited as text at two fixed anchors, not parsed. The anchors are the same
ones /blog-term documents; if either moves, register refuses rather than guessing.
"""
import argparse
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import ship  # noqa: E402

MARKER = "  // future pillar terms"
TEST_MARKER = "// ---- segmentText ----"
FILES = ("src/map.ts", "test/hub-links.test.ts", "dist/map.js", "dist/map.d.ts")


def run(cmd, cwd):
    r = subprocess.run(cmd, cwd=str(cwd), capture_output=True, text=True)
    return r.returncode, (r.stdout + r.stderr)


def pattern_for(term):
    words = [re.escape(w) for w in term.lower().split()]
    words[-1] += "s?"
    return r"\s+".join(words)


def existing_patterns(src):
    return [m.group(1) for m in re.finditer(r"pattern:\s*/(.+?)/i,", src)]


def edit(hub, term, owner, site_url, path):
    """Return the new (map.ts, test) text, or None when the term is already registered."""
    m, t = hub / "src/map.ts", hub / "test/hub-links.test.ts"
    src, test = m.read_text(), t.read_text()
    for pat in existing_patterns(src):
        try:
            if re.fullmatch(pat, term, re.I):
                return None
        except re.error:
            continue
    if MARKER not in src:
        raise ship.Refusal(f"{m} has no '{MARKER.strip()}' marker; add the entry by hand")
    sites = re.search(r"export const SITES = \{(.*?)\} as const", src, re.S)
    if not sites:
        raise ship.Refusal(f"{m} has no SITES object")
    if not re.search(rf"^\s*{re.escape(owner)}:", sites.group(1), re.M):
        src = src.replace(sites.group(0), sites.group(0).replace(
            "} as const", f"  {owner}: '{site_url}',\n}} as const"), 1)
    entry = f"  {{\n    pattern: /{pattern_for(term)}/i,\n    owner: '{owner}',\n    path: '{path}',\n  }},\n"
    src = src.replace(MARKER, entry + MARKER, 1)
    other = "stigviewer" if owner != "stigviewer" else "frontierfounder"
    case = (f"test('{term} links to {path}', () => {{\n"
            f"  const segs = segmentText('See the {term}.', new Set(), '{owner}')\n"
            f"  const link = segs!.find((s) => s.type === 'link') as any\n"
            f"  assert.equal(link.href, '{path}')\n"
            f"  const cross = segmentText('See the {term}.', new Set(), '{other}')!.find((s) => s.type === 'link') as any\n"
            f"  assert.equal(cross.href, '{site_url.rstrip('/')}{path}')\n"
            f"}})\n\n")
    test = test.replace(TEST_MARKER, case + TEST_MARKER, 1) if TEST_MARKER in test else test + "\n" + case
    return src, test


def register(hub, term, owner, site_url, path):
    hub = Path(hub)
    new = edit(hub, term, owner, site_url, path)
    if new is None:
        return "already registered"
    before = {f: (hub / f).read_text() for f in FILES if (hub / f).exists()}
    (hub / "src/map.ts").write_text(new[0])
    (hub / "test/hub-links.test.ts").write_text(new[1])
    steps = ([["npm", "install", "--include=dev", "--no-audit", "--no-fund"]]
             if not (hub / "node_modules").exists() else []) + [["npm", "run", "build"], ["npm", "test"]]
    for cmd in steps:
        rc, out = run(cmd, hub)
        if rc:
            for f, text in before.items():
                (hub / f).write_text(text)
            raise ship.Refusal(f"{' '.join(cmd)} failed; files restored, nothing committed:\n{out[-800:]}")
    ship.git(hub, "add", *[f for f in FILES if (hub / f).exists()])
    ship.git(hub, "commit", "-m", f"Add {owner} hub term: {term}",
             "-m", f"Links '{term}' to {path} on {owner}. Registered by hub_term.py (BP-001).")
    sha = ship.push(hub, ship.git(hub, "rev-parse", "--abbrev-ref", "HEAD"))
    return f"registered at {sha}"


def pin(repo, site, file):
    repo = Path(repo)
    if (repo / "pnpm-lock.yaml").exists():
        cmd = ["pnpm", "update", "@moxywolf/hub-links", "--lockfile-only"]
    elif (repo / "package-lock.json").exists():
        cmd = ["npm", "update", "@moxywolf/hub-links", "--package-lock-only"]
    else:
        raise ship.Refusal(f"{repo} has no pnpm-lock.yaml or package-lock.json to pin hub-links in")
    rc, out = run(cmd, repo)
    if rc:
        raise ship.Refusal(f"{' '.join(cmd)} failed:\n{out[-800:]}")
    text = (repo / file).read_text()
    found = re.findall(r"site:\s*['\"]([\w-]+)['\"]", text)
    if site not in found:
        raise ship.Refusal(f"{file} passes site {found or 'none'}, but the target's hub_links_site_slug is "
                           f"'{site}'. Fix the renderer; hub_term.py doesn't rewrite it.")
    return f"pinned with {' '.join(cmd[:2])}; {file} passes site '{site}'"


def main(argv=None):
    ap = argparse.ArgumentParser(description="BP-001 hub-links term and pin")
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("register")
    for f in ("--hub-links", "--term", "--owner", "--site-url", "--path"):
        r.add_argument(f, required=True)
    p = sub.add_parser("pin")
    for f in ("--repo", "--site", "--file"):
        p.add_argument(f, required=True)
    a = ap.parse_args(argv)
    try:
        print(register(a.hub_links, a.term, a.owner, a.site_url, a.path) if a.cmd == "register"
              else pin(a.repo, a.site, a.file))
    except ship.Refusal as e:
        print(f"refused: {e}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
