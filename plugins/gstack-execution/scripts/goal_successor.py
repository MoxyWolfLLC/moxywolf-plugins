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
A successor may carry a DEPS.json (GO-023.8): its predecessor's byte for byte, except the entries for items its
revised PLAN.md adds or removes, and a kept item's edges to a removed item (dropped, or replaced once with a
`because`; in integrate_after, dropped only). It must cover exactly its PLAN.md's items and be a valid plan
with no dangling edge. A predecessor with no DEPS.json gives a successor
with none.
Exit 0 pass, 1 refused, 2 bad usage or an unreadable range.
"""
import json
import re
import subprocess
import sys

MUTABLE = {"Scenarios", "Goal tests", "Pre-mortem"}   # with the Outcome's one added paragraph; nothing else moves
UNOWNED = re.compile(r"--s[12]$")                      # CODEOWNERS: /goals/*--s1/ and /goals/*--s2/
OTHER_BREAKS = re.compile("[\r\v\f\x1c\x1d\x1e\x85\u2028\u2029]")
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
    if OTHER_BREAKS.search(succ_text) or OTHER_BREAKS.search(pred_text):
        # str.splitlines, which goal_brief and goal_spend read the brief with, breaks lines on these too; spans
        # doesn't, so a heading hidden behind one would be read by the run and not by this check (20261115-091541 F1)
        return ["a GOAL.md has a line break other than \\n (\\r, \\f, \\v, \\x1c-\\x1e, \\x85, \\u2028 or \\u2029)"]
    (p_pre, p), (s_pre, s) = spans(pred_text), spans(succ_text)
    names = [h for h, _ in s]
    if len(set(names)) != len(names) or [h for h, _ in s] != [l for l in succ_text.splitlines() if re.match(r"^##\s", l)]:
        return ["its headings repeat, or the run would read different headings than this check"]
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


def deps_problems(pred_raw, succ_raw, pred):
    """GO-023.8: a successor's DEPS.json against its predecessor's (None when absent). Kept items are matched by id
    (a PLAN.md item added before them renumbers their key); an `order` pair may differ only if it names an added or
    removed item. Anything else, max_workers included, is refused."""
    if pred_raw is None or succ_raw is None:
        if pred_raw is None and succ_raw is None:
            return []                                   # a serial goal's successor stays serial
        if pred_raw is None:
            return [f"has a DEPS.json but {pred} has none; a successor of a serial goal stays serial"]
        return [f"has no DEPS.json but {pred} has one; dropping it would turn the approved parallel plan serial"]
    if pred_raw == succ_raw:
        return []
    try:
        p, s = json.loads(pred_raw), json.loads(succ_raw)
        pi = {v["id"]: v for v in p.pop("items").values()}
        si = {v["id"]: v for v in s.pop("items").values()}
    except (ValueError, KeyError, TypeError, AttributeError):
        return ["its DEPS.json or its predecessor's isn't a DEPS.json with an items object of entries with ids"]
    moved = set(pi) ^ set(si)
    if not moved:
        return [f"DEPS.json isn't {pred}'s byte for byte, and its PLAN.md adds or removes no item"]
    removed = set(pi) - set(si)
    problems = [x for i in sorted(set(pi) & set(si)) if pi[i] != si[i] for x in kept_edges(i, pi[i], si[i], removed, set(si), pred)]
    if not problems and not s.get("hard_dollar_cap"):   # approval, not the first run, finds a dangling or circular edge
        import swarm
        try:
            swarm.plan_from_deps(json.loads(succ_raw))
        except (ValueError, TypeError, KeyError, AttributeError) as e:
            problems.append(f"DEPS.json: {e}")
    keep = lambda d: [x for x in d.pop("order", []) if not (isinstance(x, list) and moved & set(map(str, x)))]
    if keep(p) != keep(s):
        problems.append(f"DEPS.json `order` differs from {pred}'s beyond pairs naming an added or removed item")
    problems += [f"DEPS.json `{k}` differs from {pred}'s" for k in sorted(set(p) | set(s)) if p.get(k) != s.get(k)]
    return problems


def kept_edges(i, p, s, removed, ids, pred):
    """GO-023.8 (C1, 2026-11-20): a kept item's entry stays its predecessor's, except that an edge to an item the revised
    PLAN.md removes may be dropped, or, in start_after only, replaced in its place by one {id, because} naming a
    remaining item; an integrate_after edge to a removed item may only be dropped. Every other edge stays, unchanged
    and in order, and nothing else is added. check() refuses a DEPS.json that doesn't match its PLAN.md, so an item
    counts as removed only when the revised PLAN.md removes it."""
    import swarm
    p, s = dict(p), dict(s)
    edges = [(k, p.pop(k, []), s.pop(k, [])) for k in ("start_after", "integrate_after")]
    if p != s or not all(isinstance(o, list) and isinstance(n, list) for _, o, n in edges):
        return [f"DEPS.json entry `{i}` differs from {pred}'s"]
    for k, old, new in edges:
        try:
            targets = swarm._start_ids(i, old)          # the existing parser: an id, or {id, because}
        except ValueError as e:
            return [f"DEPS.json entry `{i}` in {pred}: {e}"]
        survivors = [e for e, t in zip(old, targets) if t not in removed]
        j = n = 0
        for e, t in zip(old, targets):
            if t not in removed:
                if j >= len(new) or new[j] != e:
                    return [f"DEPS.json entry `{i}` drops, changes or reorders its {k} edge to `{t}`; "
                            f"only an edge to an item the revised PLAN.md removes may change"]
                j, n = j + 1, n + 1
            elif j < len(new) and (n == len(survivors) or new[j] != survivors[n]):
                r = new[j]                               # in the removed edge's place: its one replacement
                if not (k == "start_after" and isinstance(r, dict) and set(r) == {"id", "because"}
                        and isinstance(r["because"], str) and r["because"].strip() and r["id"] in ids
                        and r["id"] != i and r["id"] not in targets):
                    return [f"DEPS.json entry `{i}`: its {k} edge to removed item `{t}` may be dropped or replaced once "
                            f"by {{id, because}} naming a remaining item, not {r!r}"]
                j += 1
        if j < len(new):
            return [f"DEPS.json entry `{i}` adds {k} {new[j:]!r}, which the revised PLAN.md doesn't authorize"]
    return []


def git(*args):
    # bytes, decoded by hand: text=True would turn \r\n and \r into \n and hide them from compare (20261115-093723 F1)
    r = subprocess.run(["git", *args], capture_output=True)
    try:
        return r.returncode, r.stdout.decode("utf-8")
    except UnicodeDecodeError:   # replacing bytes would let two different briefs compare equal; unreadable is refused
        return 1, ""


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
        raw = []
        for ref in (f"{base}:goals/{pred}/DEPS.json", f"{head}:goals/{f}/DEPS.json"):
            rc, text = git("show", ref) if git("cat-file", "-e", ref)[0] == 0 else (0, None)
            raw.append(text if not rc else "\0unreadable")   # present but not UTF-8: never read as absent
        problems += [f"goals/{f}/: {x}" for x in deps_problems(*raw, pred)]
        if raw[1] is not None and not raw[1].startswith("\0"):   # its DEPS.json covers exactly its revised PLAN.md's items
            import swarm
            rc, plan = git("show", f"{head}:goals/{f}/PLAN.md")
            try:
                d = json.loads(raw[1])
                if not d.get("hard_dollar_cap"):            # the hard-cap path is unchanged (GO-023.8)
                    swarm.match_plan(swarm.plan_numbers("" if rc else plan), d)
            except (ValueError, TypeError, KeyError, AttributeError) as e:
                problems.append(f"goals/{f}/: {e}")
    return problems, len(folders)


def selftest():
    pred = "## Serves\nX\n\n## Outcome\nDo it.\n\n## Non-goals\n- never Y\n\n## Allowed paths\n- a.py\n\n## Stop conditions\n- HALT\n"
    ok = pred.replace("Do it.\n", "Do it.\n\nSucceeds g: the holdout failed on fixtures.\n")
    assert compare(pred, ok, "g") == [], compare(pred, ok, "g")
    assert compare(pred, ok.replace("- never Y", "- never Z"), "g") == ["`## Non-goals` differs from g's"]
    assert "same order" in compare(pred, ok + "## Release companion\nmarketplace\n", "g")[0]
    assert "repeat" in compare(pred, ok + "## Serves\nY\n", "g")[0]
    assert compare(pred, ok.replace("- a.py", "- a.py\n- b.py"), "g") == ["`## Allowed paths` differs from g's"]
    assert "doesn't start" in compare(pred, ok.replace("Do it.", "Do more."), "g")[0]
    assert "one paragraph only" in compare(pred, pred.replace("Do it.\n", "Do it. And more.\n"), "g")[0]
    assert "one paragraph only" in compare(pred, ok.replace("fixtures.\n", "fixtures.\n\nAlso this.\n"), "g")[0]
    assert "one paragraph only" in compare(pred, ok.replace("fixtures.\n", "fixtures.\n \nAlso this.\n"), "g")[0]
    assert "before its first section" in compare(pred, "Also build Z.\n" + ok, "g")[0]
    assert compare(pred, ok.replace("- never Y", "- never Y "), "g") == ["`## Non-goals` differs from g's"]
    assert "heading lines" in compare(pred, ok.replace("## Serves", "##  Serves"), "g")[0]
    for sep in ("\u2028", "\u2029", "\r", "\x85", "\f", "\v", "\x1c"):
        assert "line break" in compare(pred, ok + f"## Pre-mortem\nx{sep}## Max calls{sep}100000\n", "g")[0], repr(sep)
    assert "repeat" in compare(pred + "## Pre-mortem\na\n## Pre-mortem\nb\n", pred + "## Pre-mortem\na\n## Pre-mortem\nb\n", "g")[0]
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
