#!/usr/bin/env python3
"""CI-002: a change ships to installs only if its version moves.

`github-repo-analyzer` shipped RR-001 and RR-002 and stayed on 0.11.0 for most
of a day. The marketplace gates updates on a version, so nobody installed would
have received any of it. `test_manifest_consistency.py` cannot catch this class:
it asserts `plugin.json` and `marketplace.json` agree, and they agreed perfectly
at the unmoved number. DR-100.

The version has three homes, not two, and DR-013 says which one the client
reads:

  * a plugin's own `.claude-plugin/plugin.json`
  * its entry in the top-level `marketplace.json`
  * the top-level `marketplace.json` version itself

The plugin manager gates "is there an update?" on the last one. Bumping the
first two leaves the client never re-pulling the marketplace, so it never sees
them. That is why this check asserts BOTH: a changed plugin moved its own
version, AND the top-level version moved. Per-plugin alone passes a change no
client can see, which is the failure this check exists to catch.

EV-001 applies. The result names the range it resolved, the changed-file count,
and every plugin it examined. A range it cannot resolve FAILS rather than
reporting a clean tree it never diffed.

ponytail: stdlib only, git as a subprocess, per DR-101. The CI runner is a bare
setup-python and `actions/checkout` brings git with it, so a check that needs an
install is a check that stops running.
"""
import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
PASS, FAIL = "pass", "fail"
MARKETPLACE = ".claude-plugin/marketplace.json"
MANIFEST = ".claude-plugin/plugin.json"


class Unresolvable(Exception):
    """A ref or a file the check needs is not in this checkout."""


def _git(root, *args):
    r = subprocess.run(["git", "-C", str(root), *args],
                       capture_output=True, text=True)
    if r.returncode != 0:
        raise Unresolvable(f"git {' '.join(args)}: {r.stderr.strip() or 'failed'}")
    return r.stdout


def resolve(root, ref):
    """A commit-ish, or Unresolvable. A shallow checkout has no base and must say so."""
    try:
        return _git(root, "rev-parse", "--verify", f"{ref}^{{commit}}").strip()
    except Unresolvable:
        raise Unresolvable(
            f"cannot resolve {ref!r} in {root}. A shallow checkout has no base commit; "
            f"actions/checkout needs fetch-depth greater than 1 (CI-002.7).")


def _version_at(root, ref, path):
    """The `version` in a JSON file at a ref, or None when the file is not there."""
    try:
        blob = _git(root, "show", f"{ref}:{path}")
    except Unresolvable:
        return None
    try:
        return json.loads(blob).get("version")
    except json.JSONDecodeError as e:
        raise Unresolvable(f"{path} at {ref} is not readable JSON: {e}")


def _roster(root, ref):
    """Plugin names the marketplace serves. That file is what ships, so it is the roster."""
    blob = _git(root, "show", f"{ref}:{MARKETPLACE}")
    try:
        entries = json.loads(blob).get("plugins", [])
    except json.JSONDecodeError as e:
        raise Unresolvable(f"{MARKETPLACE} at {ref} is not readable JSON: {e}")
    names = set()
    for e in entries:
        src = e.get("source", "")
        if isinstance(src, str) and src.startswith("./plugins/"):
            names.add(src[len("./plugins/"):].strip("/"))
        elif e.get("name"):
            names.add(e["name"])
    return names


def run(root, base, head="HEAD"):
    """Resolve the range and examine every plugin whose files changed inside it."""
    root = Path(root)
    b, h = resolve(root, base), resolve(root, head)

    changed = [ln for ln in _git(root, "diff", "--name-only", b, h).splitlines() if ln]
    plugins = sorted({ln.split("/")[1] for ln in changed
                      if ln.startswith("plugins/") and len(ln.split("/")) > 2})

    roster = _roster(root, h)
    checks = []
    for name in plugins:
        manifest = f"plugins/{name}/{MANIFEST}"
        was, now = _version_at(root, b, manifest), _version_at(root, h, manifest)

        if now is None:
            # Removed inside the range, or never carried a manifest. Nothing ships either way.
            checks.append({"plugin": name, "status": PASS, "base": was, "head": None,
                           "detail": "no manifest at head; not shipped from this range"})
        elif name not in roster:
            # CI-002.3: reported by name, never silently skipped.
            checks.append({"plugin": name, "status": FAIL, "base": was, "head": now,
                           "detail": f"changed but absent from {MARKETPLACE}; the marketplace "
                                     f"does not serve it, so nothing here reaches a client"})
        elif was is None:
            # CI-002.4: new inside the range, so there is no base version to differ from.
            checks.append({"plugin": name, "status": PASS, "base": None, "head": now,
                           "detail": f"new in this range at {now}; no base version to move"})
        elif was == now:
            checks.append({"plugin": name, "status": FAIL, "base": was, "head": now,
                           "detail": f"files changed and version stayed at {now}; "
                                     f"the marketplace gates updates on this number"})
        else:
            checks.append({"plugin": name, "status": PASS, "base": was, "head": now,
                           "detail": f"{was} -> {now}"})

    # CI-002.2: the number the client actually gates on. Only asked when a plugin changed.
    top_was, top_now = _version_at(root, b, MARKETPLACE), _version_at(root, h, MARKETPLACE)
    if not plugins:
        top = {"status": PASS, "base": top_was, "head": top_now,
               "detail": "no plugin changed in this range; no top-level bump required"}
    elif top_was == top_now:
        top = {"status": FAIL, "base": top_was, "head": top_now,
               "detail": f"{len(plugins)} plugin(s) changed and the top-level version stayed at "
                         f"{top_now}; the client never re-pulls the marketplace, so it never sees them"}
    else:
        top = {"status": PASS, "base": top_was, "head": top_now, "detail": f"{top_was} -> {top_now}"}

    return {"base": b, "head": h, "range": f"{base}..{head}",
            "changed_files": len(changed), "examined": len(checks),
            "checks": checks, "top_level": top}


def verdict(result):
    failed = [c for c in result["checks"] if c["status"] == FAIL]
    return FAIL if (failed or result["top_level"]["status"] == FAIL) else PASS


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--root", default=str(ROOT))
    ap.add_argument("--base", help="base ref of the range (e.g. origin/main, HEAD~1)")
    ap.add_argument("--head", default="HEAD")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args(argv)

    if a.selftest:
        return _selftest()
    if not a.base:
        ap.error("--base is required unless --selftest")

    try:
        result = run(a.root, a.base, a.head)
    except Unresolvable as e:
        # CI-002.5: never a clean tree it did not diff.
        print(f"FAIL  {e}")
        print("version bump: FAIL, examined 0 plugin(s), range unresolved")
        return 1

    v = verdict(result)
    if a.json:
        print(json.dumps({**result, "gate": v.upper()}, indent=2))
    else:
        for c in result["checks"]:
            if c["status"] == FAIL:
                print(f"FAIL  {c['plugin']}: {c['detail']}")
        if result["top_level"]["status"] == FAIL:
            print(f"FAIL  [top-level]: {result['top_level']['detail']}")
        names = ", ".join(c["plugin"] for c in result["checks"]) or "none"
        print(f"version bump: {v.upper()}, range {result['range']} "
              f"({result['base'][:7]}..{result['head'][:7]}), "
              f"{result['changed_files']} changed file(s), "
              f"examined {result['examined']} plugin(s): {names}")
    return 1 if v == FAIL else 0


def _selftest():
    """CI-002.9. Temporary repositories, because the thing under test is a real diff range."""
    import tempfile

    def git(d, *a):
        subprocess.run(["git", "-C", str(d), *a], check=True,
                       capture_output=True, text=True)

    def write(d, rel, obj):
        p = Path(d) / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(obj, indent=2) + "\n")

    def fixture(d, top="1.0.0", plugins=(("alpha", "0.1.0"),), rostered=None):
        rostered = [n for n, _ in plugins] if rostered is None else rostered
        git(d, "init", "-q", "-b", "main")
        git(d, "config", "user.email", "t@t"); git(d, "config", "user.name", "t")
        write(d, MARKETPLACE, {"version": top,
                               "plugins": [{"name": n, "source": f"./plugins/{n}"}
                                           for n in rostered]})
        for n, v in plugins:
            write(d, f"plugins/{n}/{MANIFEST}", {"name": n, "version": v})
            (Path(d) / "plugins" / n / "code.py").write_text("x = 1\n")
        git(d, "add", "-A"); git(d, "commit", "-qm", "base")

    def commit(d, msg="change"):
        git(d, "add", "-A"); git(d, "commit", "-qm", msg)

    # 1. a changed plugin at an unmoved version FAILS
    with tempfile.TemporaryDirectory() as d:
        fixture(d)
        (Path(d) / "plugins/alpha/code.py").write_text("x = 2\n")
        write(d, MARKETPLACE, {"version": "1.1.0",
                               "plugins": [{"name": "alpha", "source": "./plugins/alpha"}]})
        commit(d)
        r = run(d, "HEAD~1")
        assert verdict(r) == FAIL, r
        assert r["checks"][0]["plugin"] == "alpha" and r["checks"][0]["status"] == FAIL, r
        assert "0.1.0" in r["checks"][0]["detail"], r

    # 2. the same plugin with a moved version passes
    with tempfile.TemporaryDirectory() as d:
        fixture(d)
        (Path(d) / "plugins/alpha/code.py").write_text("x = 2\n")
        write(d, f"plugins/alpha/{MANIFEST}", {"name": "alpha", "version": "0.2.0"})
        write(d, MARKETPLACE, {"version": "1.1.0",
                               "plugins": [{"name": "alpha", "source": "./plugins/alpha"}]})
        commit(d)
        r = run(d, "HEAD~1")
        assert verdict(r) == PASS, r
        assert r["checks"][0]["detail"] == "0.1.0 -> 0.2.0", r

    # 3. CI-002.2 as a test: the plugin moved, the top-level did not, so it reaches nobody
    with tempfile.TemporaryDirectory() as d:
        fixture(d)
        (Path(d) / "plugins/alpha/code.py").write_text("x = 2\n")
        write(d, f"plugins/alpha/{MANIFEST}", {"name": "alpha", "version": "0.2.0"})
        commit(d)
        r = run(d, "HEAD~1")
        assert verdict(r) == FAIL, r
        assert r["checks"][0]["status"] == PASS, r        # the plugin itself is fine
        assert r["top_level"]["status"] == FAIL, r        # and it still ships to nobody
        assert "never re-pulls" in r["top_level"]["detail"], r

    # 4. CI-002.4: a plugin new within the range passes
    with tempfile.TemporaryDirectory() as d:
        fixture(d)
        write(d, f"plugins/beta/{MANIFEST}", {"name": "beta", "version": "0.1.0"})
        (Path(d) / "plugins/beta/code.py").write_text("y = 1\n")
        write(d, MARKETPLACE, {"version": "1.1.0",
                               "plugins": [{"name": n, "source": f"./plugins/{n}"}
                                           for n in ("alpha", "beta")]})
        commit(d)
        r = run(d, "HEAD~1")
        assert verdict(r) == PASS, r
        assert [c["plugin"] for c in r["checks"]] == ["beta"], r
        assert r["checks"][0]["base"] is None, r

    # 5. a range touching no plugin passes and reports zero examined
    with tempfile.TemporaryDirectory() as d:
        fixture(d)
        (Path(d) / "README.md").write_text("hello\n")
        commit(d)
        r = run(d, "HEAD~1")
        assert verdict(r) == PASS, r
        assert r["examined"] == 0 and r["changed_files"] == 1, r
        assert "no plugin changed" in r["top_level"]["detail"], r

    # 6. CI-002.5: an unresolvable base FAILS rather than reporting a clean tree
    with tempfile.TemporaryDirectory() as d:
        fixture(d)
        try:
            run(d, "origin/main")
        except Unresolvable as e:
            assert "fetch-depth" in str(e), e
        else:
            raise AssertionError("an unresolvable base must not report a clean tree")

    # 7. CI-002.3: a changed plugin the marketplace does not serve is named, not skipped
    with tempfile.TemporaryDirectory() as d:
        fixture(d, plugins=(("alpha", "0.1.0"), ("ghost", "0.1.0")), rostered=["alpha"])
        (Path(d) / "plugins/ghost/code.py").write_text("z = 2\n")
        write(d, MARKETPLACE, {"version": "1.1.0",
                               "plugins": [{"name": "alpha", "source": "./plugins/alpha"}]})
        commit(d)
        r = run(d, "HEAD~1")
        assert verdict(r) == FAIL, r
        assert r["checks"][0]["plugin"] == "ghost", r
        assert "absent from" in r["checks"][0]["detail"], r

    # 8. a plugin removed inside the range is not required to bump
    with tempfile.TemporaryDirectory() as d:
        fixture(d, plugins=(("alpha", "0.1.0"), ("old", "0.1.0")))
        subprocess.run(["rm", "-rf", str(Path(d) / "plugins/old")], check=True)
        write(d, MARKETPLACE, {"version": "1.1.0",
                               "plugins": [{"name": "alpha", "source": "./plugins/alpha"}]})
        commit(d)
        r = run(d, "HEAD~1")
        assert verdict(r) == PASS, r
        assert r["checks"][0]["plugin"] == "old" and r["checks"][0]["head"] is None, r

    # 9. EV-001: the report names the range, the file count, and every plugin by name
    with tempfile.TemporaryDirectory() as d:
        fixture(d, plugins=(("alpha", "0.1.0"), ("beta", "0.1.0")))
        for n in ("alpha", "beta"):
            (Path(d) / f"plugins/{n}/code.py").write_text("x = 9\n")
            write(d, f"plugins/{n}/{MANIFEST}", {"name": n, "version": "0.2.0"})
        write(d, MARKETPLACE, {"version": "1.1.0",
                               "plugins": [{"name": n, "source": f"./plugins/{n}"}
                                           for n in ("alpha", "beta")]})
        commit(d)
        r = run(d, "HEAD~1")
        assert verdict(r) == PASS, r
        assert [c["plugin"] for c in r["checks"]] == ["alpha", "beta"], r
        assert r["changed_files"] == 5, r
        assert len(r["base"]) == 40 and len(r["head"]) == 40, r

    print("version_bump selftest: 9 cases, all pass")
    return 0


if __name__ == "__main__":
    sys.exit(main())
