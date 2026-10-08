#!/usr/bin/env python3
"""CS-006: every line that reaches Dorian is a quotation found in its source, or a labeled line.

    claim_check.py --doc memo.md --source Sales=sales.md --source Finance=finance.md --source Ask=ask.md

A line is structural (blank, a heading, a rule, a short bold title, inside a fenced block), labeled,
or failed. Labeled means one of:

    <Name>: "quotation"      every quotation is 3+ words and is in that source's file, word for word
    Me: I ...                one sentence, first person: what the writer did or didn't do
    Open: ...?               a question
    My inference: ...        (or Inference:) the writer's own reasoning
    Proposal: ...            what the writer proposes
    Skill: ... / Source: ... records

None of those may retell what a source said ("finance says ...", "according to Sales"). A source's
words are quoted under its own label. And an inference or a proposal may not say that nobody
did something or that nothing was done ("nobody has reviewed"): one run can't know that, and a `Me:`
line can say what the writer did. Quote marks inside such a line don't exempt it: only a line that
starts with a source's name is checked as a quotation.

Exit 0: no line failed and at least one labeled line was examined. Exit 1: a line failed, or nothing
was labeled (a check that examined nothing hasn't passed). Exit 2: it couldn't run. There is no
option that lets a line through unchecked.

What this does not check, on purpose: whether an inference is sound, whether a `Me:` line is true,
whether a quotation is fair to its context, or who wrote a source file. It checks form and that a
quotation exists where the line says it does.

ponytail: stdlib and regexes over lines. A quotation can't contain a double quote of its own, and a
`Me:` line is checked for its first word and for one sentence, not for what the sentence says.
Headings, bold titles of 80 characters or fewer and fenced blocks aren't examined, so the receipt
counts them: a claim hidden in one shows up as a number that's too big for the document.
"""
import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

FREE = {"my inference", "inference", "proposal", "skill", "source"}
RESERVED = FREE | {"me", "open"}
LABEL = re.compile(r"^\**([A-Za-z][A-Za-z -]{0,30}?)\**\s*:\**\s*(.*)$")
MARKER = re.compile(r"^(?:>\s*)*(?:[-*+]\s+|\d+[.)]\s+)?")
FENCE = re.compile(r"^(`{3,}|~{3,})(.*)$")
QUOTE = re.compile(r'"([^"]*)"')
# quotations and nothing else: one or more, joined by a single "and" or "then"
SEQUENCE = re.compile(r'^"[^"]*"(?:[.,;]?\s+(?:and|then)\s+"[^"]*")*[.,;:]?$')
SAYING = (r"says?|said|reports?|reported|states?|stated|claims?|claimed|confirms?|confirmed|agrees?|agreed|proposes?|proposed|"
          r"recommends?|recommended|wants?|wanted|thinks?|notes?|noted|finds?|found|shows?|showed")
TITLE_MAX = 80
DID = (r"read|checked|reviewed|verified|confirmed|asked|looked|written|wrote|sent|tested|evidenced|done|did|seen|saw|"
       r"approved|answered|contacted|measured|recorded|logged|told|said")
# ponytail: "nobody has reviewed", "which nobody read", "nothing's been checked". A shape, not the bare words:
# "doing nothing is option B" and "Nobody else." are honest lines, and a replay over run 17 showed the bare words fail them.
NOBODY = re.compile(rf"\b(nobody|no[ -]one|nothing)(?:\s+(?:has|had|have|was|ever)|'s)?(?:\s+(?:been|ever|yet))?\s+(?:{DID})\b", re.I)


def norm(text):
    """Quote marks straightened, emphasis marks dropped, whitespace collapsed.
    An underscore is emphasis at the edge of a word and part of the word inside one: `_note_` loses it, `pipeline_review` keeps it."""
    text = text.replace("“", '"').replace("”", '"').replace("‘", "'").replace("’", "'")
    text = re.sub(r"(?<![A-Za-z0-9])_+|_+(?![A-Za-z0-9])", "", re.sub(r"[*`]", "", text))
    return re.sub(r"\s+", " ", text).strip()


def structural(line, labels):
    """"" for a line that has to be judged, else what kind of structure it is."""
    s = line.strip()
    if not s or re.fullmatch(r"[-*_]{3,}", s):
        return "blank"
    if s.startswith("#"):
        return "title"
    s = MARKER.sub("", s).strip()
    if not s:
        return "blank"
    title = re.fullmatch(r"\*\*(.+?)\*\*[.:]?", s)
    if not title or "**" in title.group(1) or len(title.group(1)) > TITLE_MAX:
        return ""
    # `**Inference:**` is an empty labeled line dressed as a title, not a title
    return "" if title.group(1).rstrip(":").strip().lower() in labels and title.group(1).rstrip().endswith(":") else "title"


def retold(rest, sources):
    """The source a non-quotation line credits with saying something, or None.
    ponytail: a list of saying verbs after a source's name. It catches the common shapes, not every paraphrase."""
    names = "|".join(re.escape(n) for n in sorted(sources, key=len, reverse=True))
    if not names:
        return None
    who = rf"\b(?:the\s+)?({names})(?:-department)?(?:'s)?(?:\s+(?:result|review|answer))?"
    m = (re.search(rf"{who}\s+(?:also\s+|only\s+)?(?:{SAYING})\b", rest, re.I)
         or re.search(rf"\baccording to (?:the )?({names})\b", rest, re.I))
    return m.group(1) if m else None


def judge(line, sources):
    """(ok, reason, quotations verified) for one non-structural line."""
    body = MARKER.sub("", line.strip()).strip()
    m = LABEL.match(body)
    if not m:
        return False, "unlabeled: not a quotation from a source and not a labeled line", 0
    label, rest = m.group(1).strip().lower(), norm(m.group(2))
    if label in sources:
        return quotation(m.group(1), rest, sources[label])
    if label not in RESERVED:
        return False, f"{m.group(1)} is not a known label or a source named on the command line", 0
    # everything below is the writer's own line, quote marks or not
    who = retold(rest, sources)
    if who:
        return False, f"retells what {who} said: a source's words are quoted under its own label, not retold", 0
    if label in FREE:
        if not rest:
            return False, f"empty: nothing follows {m.group(1)}:", 0
        hit = NOBODY.search(rest) if label in ("my inference", "inference", "proposal") else None
        if hit:
            return False, (f"says what nobody did ({hit.group(0)!r}): one run can't know that. Say what you did in a Me: line, "
                           "or quote the source"), 0
        return True, "", 0
    if label == "open":
        return (True, "", 0) if rest.endswith("?") else (False, "Open: is for a question, and this doesn't end with one", 0)
    if not re.match(r"I\b", rest):
        return False, "Me: is first person, and this doesn't start with I", 0
    if re.search(r"[.!?]\s+\S", rest.rstrip(".!?")):
        return False, "Me: takes one sentence, so a second claim can't ride on the first", 0
    return True, "", 0


def quotation(name, rest, source):
    """A source-labeled line: quotations only, each found whole in that source."""
    if "..." in rest or "…" in rest:
        return False, "a quotation can't carry an ellipsis: quote the words as they stand, in two quotations if need be", 0
    quotes = QUOTE.findall(rest)
    if not quotes:
        return False, f"no quotation: a {name}: line quotes that source and says nothing else", 0
    if not SEQUENCE.match(rest):
        return False, "words outside its quotations: the line is quotations joined by and or then, and nothing else", 0
    for q in quotes:
        q = re.sub(r"[.,;:]$", "", q.strip())           # one closing mark, so a period inside the quote marks doesn't matter
        if len(q.split()) < 3:
            return False, f"a quotation is at least three words: {q!r}", 0
        if not re.search(rf"(?<!\w){re.escape(q)}(?!\w)", source):   # whole words: "he call" is not in "the call"
            return False, f"quotation not found in {name}: {q!r}", 0
    return True, "", len(quotes)


def run(doc, sources):
    out = {"examined": 0, "labeled": 0, "quotations_verified": 0, "failed": 0, "titles": 0, "fenced": 0, "failures": []}
    labels, fence = RESERVED | set(sources), None       # fence: the character and length that opened the block we're in
    for n, line in enumerate(doc.splitlines(), 1):
        f = FENCE.match(MARKER.sub("", line.strip()))
        if fence:
            if f and f.group(1)[0] == fence[0] and len(f.group(1)) >= fence[1] and not f.group(2).strip():
                fence = None
            else:
                out["fenced"] += 1
            continue
        if f:
            fence = (f.group(1)[0], len(f.group(1)))
            continue
        kind = structural(line, labels)
        if kind:
            out["titles"] += kind == "title"
            continue
        out["examined"] += 1
        ok, reason, verified = judge(line, sources)
        if ok:
            out["labeled"] += 1
            out["quotations_verified"] += verified
        else:
            out["failed"] += 1
            out["failures"].append({"line": n, "reason": reason, "text": line.strip()})
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--doc", required=True)
    ap.add_argument("--source", action="append", default=[], metavar="NAME=FILE")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()
    try:
        raw = Path(a.doc).read_bytes()
        sources = {}
        for item in a.source:
            name, _, path = item.partition("=")
            if not name or not path:
                raise ValueError(f"--source takes NAME=FILE, got {item!r}")
            if name.strip().lower() in RESERVED:
                raise ValueError(f"a source can't be named {name!r}: that label already means something")
            sources[name.strip().lower()] = norm(Path(path).read_text())
    except (OSError, ValueError) as e:
        print(f"claim-check couldn't run: {e}", file=sys.stderr)
        return 2
    out = run(raw.decode("utf-8", "replace"), sources)
    out["sha256"] = hashlib.sha256(raw).hexdigest()
    if a.json:
        print(json.dumps(out, indent=1))
    else:
        for f in out["failures"]:
            print(f"line {f['line']}: {f['reason']}\n    {f['text']}")
        if not out["labeled"] and not out["failed"]:
            print("nothing labeled was examined, so nothing passed")
        print(f"claim-check: examined {out['examined']} line{'' if out['examined'] == 1 else 's'}, {out['labeled']} labeled, "
              f"{out['quotations_verified']} quotations verified, {out['failed']} failed, "
              f"{out['titles']} titles and {out['fenced']} fenced lines not examined, sha256 {out['sha256']}")
    return 0 if out["labeled"] and not out["failed"] else 1


if __name__ == "__main__":
    sys.exit(main())
