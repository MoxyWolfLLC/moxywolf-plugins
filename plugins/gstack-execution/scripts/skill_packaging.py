#!/usr/bin/env python3
"""CI-001: every SKILL.md in this repository is one a loader can read.

A skill whose frontmatter will not parse, or whose description the loader
truncates, is broken at the only moment that matters -- when someone installs
the plugin. Nothing in this repository noticed: the suites test the scripts,
not the catalog they ship inside. An outside compatibility assessment found ten
such packages here, which is ten more than a green build implied.

This asserts exactly what that assessment asserted, and nothing it did not:

  * the frontmatter block parses
  * `description` is present
  * it is not empty
  * it is at most 1024 characters

It does NOT judge wording, tone or usefulness. A check that grows opinions is a
check people start overriding.

EV-001 applies as everywhere else: the result says how many packages were
examined, and a run that examined none FAILS rather than passing over a catalog
it never found.

ponytail: stdlib only, no PyYAML. The CI runner is a bare setup-python and the
rest of this repository's checks are stdlib by design, so a check that needs an
install is a check that stops running. The reader below covers the frontmatter
subset this catalog actually uses -- a flat mapping of plain, quoted, flow,
folded and literal scalars -- and reports anything outside it as unreadable,
which is the honest answer for a block a simple loader also could not read. Its
agreement with PyYAML over all 150 real packages is recorded in DESIGN.md.
"""
import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
LIMIT = 1024
PASS, FAIL = "pass", "fail"

KEY = re.compile(r"^([A-Za-z0-9_.\-]+):(?:[ \t]+(.*))?$")
BLOCK = re.compile(r"^([|>])([+-]?)(\d?)$")


class Unreadable(Exception):
    """The frontmatter block is not something a loader can parse."""


def _indent(line):
    return len(line) - len(line.lstrip(" "))


def _fold(lines):
    """YAML folding: a paragraph's lines join with a space, a blank line is a break.

    Lines are joined as they stand. Trailing whitespace inside a folded block survives
    folding, so stripping it here would report a length the loader does not see."""
    paras, cur = [], []
    for l in lines:
        if l.strip():
            cur.append(l)
        else:
            paras.append(cur)
            cur = []
    paras.append(cur)
    return "\n".join(" ".join(p) for p in paras)


def frontmatter(text):
    """The leading `---` block, as {key: value}. Raises Unreadable.

    Deliberately strict. Silently accepting a block a real parser rejects would
    turn this check into the false pass it exists to catch.
    """
    if not text.startswith("---"):
        raise Unreadable("no frontmatter block: the file does not open with ---")
    lines = text.splitlines()
    end = next((i for i, l in enumerate(lines[1:], 1) if l.rstrip() in ("---", "...")), None)
    if end is None:
        raise Unreadable("frontmatter block is never closed by a --- line")

    body, out, i = lines[1:end], {}, 0
    while i < len(body):
        line = body[i]
        if not line.strip() or line.lstrip().startswith("#"):
            i += 1
            continue
        if _indent(line):
            raise Unreadable(f"line {i + 2}: indented line with no key above it")
        m = KEY.match(line)
        if not m:
            raise Unreadable(f"line {i + 2}: not `key: value` -- {line.strip()[:60]!r}")
        key, raw = m.group(1), (m.group(2) or "").strip()

        cont = []
        j = i + 1
        while j < len(body) and (not body[j].strip() or _indent(body[j]) > 0):
            cont.append(body[j])
            j += 1

        b = BLOCK.match(raw)
        if b:
            keep = [l for l in cont]
            while keep and not keep[-1].strip():
                keep.pop()
            pad = min((_indent(l) for l in keep if l.strip()), default=0)
            stripped = [l[pad:] if l.strip() else "" for l in keep]
            if b.group(1) == "|":
                value = "\n".join(stripped)
            else:
                value = _fold(stripped)
            # YAML's default (clip) chomping keeps one trailing newline, and that one
            # character decides a description sitting exactly on the limit.
            if value and b.group(2) != "-":
                value += "\n"
        elif raw[:1] in ("'", '"'):
            q = raw[0]
            if len(raw) < 2 or raw[-1] != q:
                raise Unreadable(f"line {i + 2}: quoted value for `{key}` is not closed on its line")
            value = raw[1:-1].replace("\\n", "\n").replace('\\"', '"')
        elif raw[:1] in ("[", "{"):
            value = " ".join([raw] + [l.strip() for l in cont if l.strip()])
        else:
            parts = [raw] + [l.strip() for l in cont if l.strip()]
            for n, p in enumerate(parts):
                # The one construct that makes these files unparseable in practice:
                # an unquoted colon inside a plain scalar starts a nested mapping.
                if ": " in p or p.endswith(":"):
                    raise Unreadable(
                        f"line {i + 2 + n}: unquoted ':' in the plain value of `{key}` -- "
                        f"YAML reads it as a nested key. Quote the value or use a `>` block")
            value = " ".join(p for p in parts if p)

        if key in out:
            raise Unreadable(f"line {i + 2}: duplicate key `{key}`")
        out[key] = value
        i = j
    return out


def check(path):
    """(status, detail) for one package."""
    try:
        fm = frontmatter(path.read_text(encoding="utf-8", errors="replace"))
    except Unreadable as e:
        return FAIL, f"malformed frontmatter: {e}"
    if "description" not in fm:
        return FAIL, "no description in frontmatter"
    desc = fm["description"]
    if not desc.strip():
        return FAIL, "description is empty"
    if len(desc) > LIMIT:
        return FAIL, f"description is {len(desc)} chars, over {LIMIT}"
    return PASS, f"description is {len(desc)} chars"


def run(root):
    """One record per SKILL.md found under root."""
    packages = sorted(p for p in Path(root).rglob("SKILL.md") if ".git" not in p.parts)
    results = []
    for p in packages:
        status, detail = check(p)
        results.append({"package": str(p.relative_to(root)), "status": status, "detail": detail})
    return results


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--root", default=str(ROOT))
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)
    root = Path(a.root).resolve()

    results = run(root)
    failed = [r for r in results if r["status"] == FAIL]
    # EV-001: a catalog that was never found is not a clean catalog.
    verdict = FAIL if (failed or not results) else PASS

    if a.json:
        print(json.dumps({"examined": len(results), "unit": "packages",
                          "checks": results, "failed": [r["package"] for r in failed],
                          "gate": verdict.upper()}, indent=2))
    else:
        for r in failed:
            print(f"FAIL  {r['package']}: {r['detail']}")
        if not results:
            print(f"FAIL  examined 0 packages under {root}; a check that examined nothing "
                  f"cannot pass. Check that skills still ship as SKILL.md.")
        print(f"skill packaging: {verdict.upper()}, examined {len(results)} package(s), "
              f"{len(failed)} failed")
    return 1 if verdict == FAIL else 0


def _selftest():
    import tempfile

    def fm(s):
        return frontmatter(s)

    def unreadable(s, why):
        try:
            fm(s)
        except Unreadable:
            return
        raise AssertionError(f"should have been unreadable: {why}")

    # 1. the ordinary case
    d = fm("---\nname: a\ndescription: hello there\n---\nbody\n")
    assert d["description"] == "hello there", d

    # 2. a folded block, which is how an over-long description gets fixed
    d = fm("---\nname: a\ndescription: >\n  one two\n  three\n---\n")
    assert d["description"] == "one two three\n", d

    # 3b. a blank line inside a folded block is a break, not a space
    d = fm("---\ndescription: >\n  one two\n\n  three\n---\n")
    assert d["description"] == "one two\nthree\n", d

    # 3a. an explicit strip chomp drops it
    assert fm("---\ndescription: >-\n  one two\n---\n")["description"] == "one two"

    # 3. a literal block keeps its newlines
    d = fm("---\ndescription: |\n  one\n  two\n---\n")
    assert d["description"] == "one\ntwo\n", d

    # 4. a folded block may contain colons; that is the whole point of using one
    d = fm("---\ndescription: >\n  Audit vault health: links, orphans.\n---\n")
    assert d["description"] == "Audit vault health: links, orphans.\n", d

    # 5. quoted scalars
    assert fm('---\ndescription: "a: b"\n---\n')["description"] == "a: b"
    assert fm("---\ndescription: ''\n---\n")["description"] == ""

    # 6. flow sequences, used by allowed-tools
    d = fm("---\nallowed-tools: [Read, Write]\ndescription: x\n---\n")
    assert d["allowed-tools"] == "[Read, Write]", d

    # 7. a plain scalar continuing onto indented lines
    d = fm("---\ndescription: one\n  two\n---\n")
    assert d["description"] == "one two", d

    # 8. the two real failure shapes
    unreadable("---\ndescription: it returns: a thing\n---\n", "unquoted colon-space")
    unreadable("---\ndescription: ends with a colon:\n---\n", "trailing colon")
    unreadable("body with no frontmatter\n", "no block")
    unreadable("---\nname: a\n", "unterminated block")
    unreadable("---\n  orphan: 1\n---\n", "indented with no key above")
    unreadable("---\nname: a\nname: b\n---\n", "duplicate key")

    # 9. the check verdicts, over real files on disk
    with tempfile.TemporaryDirectory() as t:
        root = Path(t)
        (root / "ok").mkdir()
        (root / "ok" / "SKILL.md").write_text("---\nname: ok\ndescription: fine\n---\n")
        assert check(root / "ok" / "SKILL.md")[0] == PASS

        (root / "empty").mkdir()
        (root / "empty" / "SKILL.md").write_text('---\nname: e\ndescription: ""\n---\n')
        assert check(root / "empty" / "SKILL.md")[0] == FAIL, "empty description must fail"

        (root / "missing").mkdir()
        (root / "missing" / "SKILL.md").write_text("---\nname: m\n---\n")
        assert check(root / "missing" / "SKILL.md")[0] == FAIL, "absent description must fail"

        (root / "long").mkdir()
        (root / "long" / "SKILL.md").write_text(f"---\nname: l\ndescription: {'x' * (LIMIT + 1)}\n---\n")
        st, detail = check(root / "long" / "SKILL.md")
        assert st == FAIL and str(LIMIT + 1) in detail, (st, detail)

        (root / "edge").mkdir()
        (root / "edge" / "SKILL.md").write_text(f"---\nname: l\ndescription: {'x' * LIMIT}\n---\n")
        assert check(root / "edge" / "SKILL.md")[0] == PASS, "exactly at the limit is allowed"

        assert main(["--root", str(root)]) == 1, "a root with failures must fail"

    # 10. EV-001: an empty tree is a failure, not a clean catalog
    with tempfile.TemporaryDirectory() as t:
        assert run(t) == []
        assert main(["--root", t]) == 1, "examining zero packages must FAIL, not pass"

    print("skill_packaging selftest OK: 12 fixtures, 28 assertions")
    return 0


if __name__ == "__main__":
    sys.exit(_selftest() if "--selftest" in sys.argv else main())
