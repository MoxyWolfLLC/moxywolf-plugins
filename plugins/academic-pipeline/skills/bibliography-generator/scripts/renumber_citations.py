#!/usr/bin/env python3
"""Renumber Vancouver citations by first appearance and reorder the reference list.

    python3 renumber_citations.py paper.md            # report only, writes nothing
    python3 renumber_citations.py paper.md --write    # rewrite in place
    python3 renumber_citations.py paper.md --check    # exit 1 if out of order (CI / gate)

Why: Academia.edu requires numbered-by-appearance references. The pipeline numbers
once at Stage 7; any citation inserted by hand afterwards ripples through every
number after it. This pass recomputes the numbering from the body text and
reorders the list to match, so an edit costs one new key, not a manual renumber.

Rules: citation markers are [n], [n,m], [n-m] / [n–m] (any mix). The reference
list starts at the first '## References' heading and its entries are lines
matching '^N. '. Markers after that heading are not renumbered. Ranges are
expanded, remapped, and re-compressed only when the new numbers are contiguous.
Nothing is invented: an in-text number with no list entry, or an entry never
cited, is reported and the file is left untouched.
"""
import re, sys
from pathlib import Path

MARK = re.compile(r"\[(\d+(?:\s*[,–-]\s*\d+)*)\]")
ENTRY = re.compile(r"^(\d+)\. (.*)$", re.M)
HEAD = "## References"

def expand(group):
    out = []
    for part in re.split(r"\s*,\s*", group):
        m = re.fullmatch(r"(\d+)\s*[–-]\s*(\d+)", part)
        if m:
            a, b = int(m[1]), int(m[2]); out += list(range(a, b + 1))
        else:
            out.append(int(part))
    return out

def compress(nums):
    nums = sorted(set(nums)); runs = []; i = 0
    while i < len(nums):
        j = i
        while j + 1 < len(nums) and nums[j + 1] == nums[j] + 1: j += 1
        runs.append(f"{nums[i]}–{nums[j]}" if j - i >= 2 else ",".join(map(str, nums[i:j + 1])))
        i = j + 1
    return ",".join(runs)

def main():
    args = sys.argv[1:]
    if not args: sys.exit(__doc__)
    path = Path(args[0]); write = "--write" in args; check = "--check" in args
    text = path.read_text(encoding="utf-8")
    if HEAD not in text: sys.exit(f"no '{HEAD}' heading in {path}")
    body, refs = text.split(HEAD, 1)

    order = []
    for m in MARK.finditer(body):
        for n in expand(m[1]):
            if n not in order: order.append(n)
    entries = {int(m[1]): m[2] for m in ENTRY.finditer(refs)}

    missing = [n for n in order if n not in entries]
    uncited = [n for n in entries if n not in order]
    if missing or uncited:
        print(f"REFUSING: cited but no entry {missing}; entries never cited {uncited}")
        sys.exit(2)

    mp = {old: new for new, old in enumerate(order, 1)}
    changes = [(o, n) for o, n in mp.items() if o != n]
    print(f"{path.name}: {len(order)} citations, {len(changes)} renumbered")
    for o, n in changes: print(f"  [{o}] -> [{n}]")
    if check: sys.exit(1 if changes else 0)
    if not changes or not write:
        if changes: print("dry run; pass --write to apply")
        return

    new_body = MARK.sub(lambda m: "[" + compress(mp[n] for n in expand(m[1])) + "]", body)
    # Rebuild the list: keep whatever precedes the first entry and follows the last.
    first = ENTRY.search(refs); last = list(ENTRY.finditer(refs))[-1]
    pre, post = refs[:first.start()], refs[last.end():]
    new_list = "\n\n".join(f"{mp[old]}. {entries[old].strip()}" for old in sorted(entries, key=lambda o: mp[o]))
    out = new_body + HEAD + pre + new_list + post

    # Verify before writing: order must now be 1..N and every entry present.
    seen = []
    for m in MARK.finditer(out.split(HEAD, 1)[0]):
        for n in expand(m[1]):
            if n not in seen: seen.append(n)
    got = sorted(int(m[1]) for m in ENTRY.finditer(out.split(HEAD, 1)[1]))
    assert seen == list(range(1, len(order) + 1)) == got, "post-check failed; nothing written"
    path.write_text(out, encoding="utf-8")
    print(f"wrote {path}")

if __name__ == "__main__":
    main()
