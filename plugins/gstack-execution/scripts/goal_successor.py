"""GO-011.9: a successor goal approves itself when it keeps its predecessor's brief word for word.

A goal that fails its holdout or its whole-goal review is followed by `goals/<root>--s1/`, then
`goals/<root>--s2/`. CODEOWNERS leaves those two folder names unowned, so Dorian's review isn't asked;
this check, run inside the required `tests` check, is what holds them instead:

  goal_successor.py check --base <sha> --head <sha>

Every `goals/<name>/` path whose name ends `--s1` or `--s2` (what CODEOWNERS leaves unowned) is examined:
the name must be a valid successor id, the folder must be new (an approved goal never changes), the change
must touch nothing outside that folder, the predecessor (`<root>` for --s1, `<root>--s1` for --s2) must
exist at the base, and the successor's GOAL.md must have the predecessor's sections, each once and in the
same order, every one byte for byte except those in MUTABLE, and an Outcome that starts with the
predecessor's and adds only a paragraph that starts `Succeeds <predecessor>:`. A range that touches no
such folder passes and says so. --s3 and beyond match no unowned pattern, so they go to Dorian.
Exit 0 pass, 1 refused, 2 bad usage or an unreadable range.
"""
import re
import subprocess
import sys

MUTABLE = {"Scenarios", "Goal tests", "Pre-mortem"}   # with the Outcome's one added paragraph; nothing else moves
UNOWNED = re.compile(r"--s[12]$")                      # CODEOWNERS: /goals/*--s1/ and /goals/*--s2/
SUCCESSOR = re.compile(r"^(?P<root>[a-z0-9]+(?:-[a-z0-9]+)*)--s(?P<n>[12])$")


def sections(text):
    """GOAL.md's `## ` sections, as goal_brief.sections reads them (kept here so the gate has no unowned import)."""
    out, cur = {}, None
    for line in text.splitlines():
        m = re.match(r"^##\s+(.+?)\s*$", line)
        if m:
            cur = m.group(1)
            out[cur] = []
        elif cur is not None:
            out[cur].append(line)
    return {k: "\n".join(v).strip() for k, v in out.items()}


def predecessor(folder):
    m = SUCCESSOR.match(folder)
    if not m:
        return None
    return m["root"] if m["n"] == "1" else f"{m['root']}--s1"


def spans(text):
    """(preamble, [(heading line, raw body)]): the whole document, nothing dropped or normalised, so a byte
    anywhere outside a mutable body is compared (review 20261115-085458 F1)."""
    parts = re.split(r"(?m)^(?=##\s)", text)
    pre, rest = (parts[0], parts[1:]) if not parts[0].startswith("##") else ("", parts)
    return pre, [tuple(x.split("\n", 1)) if "\n" in x else (x, "") for x in rest]


def compare(pred_text, succ_text, pred):
    """Problems with a successor GOAL.md against its predecessor's, as a list. Every byte is kept but the bodies
    of the MUTABLE sections and one added Outcome paragraph: a single line, after a blank line, starting
    `Succeeds <predecessor>: ` (Release companion and Required checkouts carry merge authority, F2 of
    20261115-080201; a whitespace-only line would start a second paragraph, F2 of 20261115-085458)."""
    (p_pre, p), (s_pre, s) = spans(pred_text), spans(succ_text)
    if p_pre != s_pre:
        return [f"the text before its first section isn't {pred}'s byte for byte"]
    if [h for h, _ in p] != [h for h, _ in s]:
        return [f"its sections aren't {pred}'s, each once and in the same order, with the same heading lines"]
    problems = []
    for (h, pb), (_, sb) in zip(p, s):
        name = re.match(r"^##\s+(.+?)\s*$", h).group(1)
        if name in MUTABLE:
            continue
        if name != "Outcome":
            if pb != sb:
                problems.append(f"`## {name}` differs from {pred}'s")
            continue
        core = pb.rstrip("\n")
        trail = pb[len(core):]
        lead = f"{core}\n\nSucceeds {pred}: "
        if not core or not sb.startswith(core):
            problems.append(f"`## Outcome` doesn't start with {pred}'s Outcome word for word")
        elif not (sb.startswith(lead) and sb.endswith(trail) and len(sb) - len(trail) > len(lead)
                  and "\n" not in sb[len(core) + 2:len(sb) - len(trail)]):
            problems.append(f"`## Outcome` may add one paragraph only, one line starting `Succeeds {pred}: ` after a blank line")
    return problems


def git(*args):
    r = subprocess.run(["git", *args], capture_output=True, text=True)
    return r.returncode, r.stdout


def check(base, head):
    """(problems, successor folders examined); raises SystemExit(2) when the range can't be read."""
    rc, out = git("diff", "--name-status", "-z", "--no-renames", f"{base}...{head}")
    if rc:
        print(f"can't read the range {base}...{head}", file=sys.stderr)
        raise SystemExit(2)
    fields = out.split("\0")
    changes = list(zip(fields[0::2], fields[1::2]))
    folders = sorted({p.split("/")[1] for _, p in changes if p.startswith("goals/") and p.count("/") >= 2
                      and UNOWNED.search(p.split("/")[1])})
    problems = []
    for f in folders:
        pred = predecessor(f)
        if pred is None:   # unowned by CODEOWNERS but not a successor id: refused, never skipped (review F1)
            problems.append(f"goals/{f}/: not a successor id (`<lowercase-id>--s1` or `--s2`), yet CODEOWNERS leaves it unowned")
            continue
        if git("cat-file", "-e", f"{base}:goals/{f}")[0] == 0 or any(st != "A" for st, p in changes if p.startswith(f"goals/{f}/")):
            problems.append(f"goals/{f}/: a successor folder is only ever added; an approved goal never changes")
        outside = [p for _, p in changes if not p.startswith(f"goals/{f}/")]
        if outside:
            problems.append(f"goals/{f}/: its change touches {len(outside)} path(s) outside the folder, e.g. {outside[0]}")
        rc_p, pred_text = git("show", f"{base}:goals/{pred}/GOAL.md")
        rc_s, succ_text = git("show", f"{head}:goals/{f}/GOAL.md")
        if rc_p:
            problems.append(f"goals/{f}/: its predecessor goals/{pred}/GOAL.md isn't on the base")
        elif rc_s:
            problems.append(f"goals/{f}/: no GOAL.md at the head")
        else:
            problems += [f"goals/{f}/: {x}" for x in compare(pred_text, succ_text, pred)]
    return problems, len(folders)


def selftest():
    pred = "## Serves\nX\n\n## Outcome\nDo it.\n\n## Non-goals\n- never Y\n\n## Allowed paths\n- a.py\n\n## Stop conditions\n- HALT\n"
    ok = pred.replace("Do it.\n", "Do it.\n\nSucceeds g: the holdout failed on fixtures.\n")
    assert compare(pred, ok, "g") == [], compare(pred, ok, "g")
    assert compare(pred, ok.replace("- never Y", "- never Z"), "g") == ["`## Non-goals` differs from g's"]
    assert "same order" in compare(pred, ok + "## Release companion\nmarketplace\n", "g")[0]
    assert "same order" in compare(pred, ok + "## Serves\nY\n", "g")[0]
    assert compare(pred, ok.replace("- a.py", "- a.py\n- b.py"), "g") == ["`## Allowed paths` differs from g's"]
    assert "doesn't start" in compare(pred, ok.replace("Do it.", "Do more."), "g")[0]
    assert "one paragraph only" in compare(pred, pred.replace("Do it.\n", "Do it. And more.\n"), "g")[0]
    assert "one paragraph only" in compare(pred, ok.replace("fixtures.\n", "fixtures.\n\nAlso this.\n"), "g")[0]
    assert "one paragraph only" in compare(pred, ok.replace("fixtures.\n", "fixtures.\n \nAlso this.\n"), "g")[0]
    assert "before its first section" in compare(pred, "Also build Z.\n" + ok, "g")[0]
    assert compare(pred, ok.replace("- never Y", "- never Y "), "g") == ["`## Non-goals` differs from g's"]
    assert "heading lines" in compare(pred, ok.replace("## Serves", "##  Serves"), "g")[0]
    assert predecessor("g--s1") == "g" and predecessor("g--s2") == "g--s1"
    assert predecessor("g--s3") is None and predecessor("g") is None and predecessor("G--s1") is None
    print("goal_successor selftest ok")


def main(argv):
    if argv == ["--selftest"]:
        selftest()
        return 0
    args = dict(zip(argv[1::2], argv[2::2]))
    if argv[:1] != ["check"] or set(args) != {"--base", "--head"}:
        print("usage: goal_successor.py check --base <sha> --head <sha> | --selftest", file=sys.stderr)
        return 2
    problems, examined = check(args["--base"], args["--head"])
    if not examined:
        print("examined 0 successor goal folders: the range adds none, nothing to hold")
        return 0
    print(f"examined {examined} successor goal folder(s)")
    for p in problems:
        print("FAIL:", p)
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
