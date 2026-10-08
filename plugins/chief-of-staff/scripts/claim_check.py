#!/usr/bin/env python3
"""CS-006: every line that reaches Dorian is a quotation found in its source, or a labeled line.

    claim_check.py --doc memo.md --source Sales=sales.md --source Finance=finance.md --source Ask=ask.md

A line is structural (blank, a heading, a rule, a short bold title, inside a fenced block), labeled,
or failed. A heading or bold title that begins with a label is judged as that labeled line. Labeled
means one of:

    <Name>: "quotation"      every quotation is 3+ words and is in that source's file, word for word
    Me: I ...                one sentence, first person: what the writer did or didn't do
    Open: ...?               one question, from its question word to its question mark
    My inference: ...        (or Inference:) the writer's own reasoning
    Proposal: ...            what the writer proposes
    Skill: ... / Source: ... records

None of those may retell what a source said ("finance says ...", "according to Sales"). A source's
words are quoted under its own label. And none of them may say that nobody did something or that
nothing was done ("nobody has reviewed"): one run can't know that. A `Me:` line can say what the
writer did, and an `Open:` line can ask it outright ("Has nobody checked?"). Quote marks inside such
a line don't exempt it: only a line that starts with a source's name is checked as a quotation.

Exit 0: no line failed and at least one labeled line was examined. Exit 1: a line failed, or nothing
was labeled (a check that examined nothing hasn't passed). Exit 2: it couldn't run. There is no
option that lets a line through unchecked.

What this does not check, on purpose: whether an inference is sound, whether a `Me:` line is true,
whether a quotation is fair to its context, or who wrote a source file. It checks form and that a
quotation exists where the line says it does.

ponytail: stdlib and regexes over lines. A quotation can't contain a double quote of its own, and a
`Me:` line is checked for its first word and for one sentence, not for what the sentence says. An
`Open:` line is checked for its first word, one sentence and its question mark, so a clause after
the question word can still carry a premise. A sentence ends at a period, so "e.g. this" reads as two.
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
NOBODY = re.compile(rf"\b(nobody|no[ -]one|nothing)(?:\s+(?:has|had|have|was|ever)|'s)?(?:\s+(?:been|ever|yet|actually|really|even))?\s+(?:{DID})\b", re.I)
# the one way a line may carry that shape: an Open: line that asks it outright, "Has nobody checked the address?"
ASKS_IT = re.compile(r"(?:has|have|had|did|does|do|was|were|is|are)\s+", re.I)
# an Open: line starts with the question: a question word, an auxiliary, or a preposition and a question word ("On what date")
QUESTION = re.compile(r"(?:(?:on|at|by|for|in|to|from|with|under|of|about|after|before|until|since)\s+)?"
                      r"(?:(?:who|whom|whose|what|when|where|which|why|how)(?:'s|'re|'d|'ll)?|"
                      r"(?:is|are|was|were|am|do|does|did|has|have|had|could|would|should|might|must)(?:n't)?|"
                      r"can(?:'t|not)?|will|won't|shall|may)\b", re.I)
HEADING = re.compile(r"#{1,6}(?:\s+(.*))?$")
SECOND = re.compile(r"[.!?]\s+\S")                # a second sentence. ponytail: an abbreviation's period counts too


def norm(text):
    """Quote marks straightened, emphasis marks dropped, whitespace collapsed.
    An asterisk, underscore or backtick is emphasis at the edge of a word and part of the word inside one:
    `_note_` and `**note**` lose theirs, `pipeline__review` and `5*4` keep theirs.
    ponytail: `__init__` reads as a bold init, the way Markdown renders it."""
    text = text.replace("“", '"').replace("”", '"').replace("‘", "'").replace("’", "'")
    text = re.sub(r"(?<![\w*`])[*_`]+|[*_`]+(?![\w*`])", "", text)
    return re.sub(r"\s+", " ", text).strip()


def labeled(text, labels):
    m = LABEL.match(text.strip())
    return bool(m) and m.group(1).strip().lower() in labels


def structural(line, labels):
    """"" for a line that has to be judged, else what kind of structure it is.
    A heading or a bold title that begins with a label is a labeled line set as a title, and it's judged."""
    s = line.strip()
    if not s or re.fullmatch(r"[-*_]{3,}", s):
        return "blank"
    h = HEADING.match(s)
    if h:
        return "" if labeled(h.group(1) or "", labels) else "title"
    s = MARKER.sub("", s).strip()
    if not s:
        return "blank"
    title = re.fullmatch(r"\*\*(.+?)\*\*[.:]?", s)
    if not title or "**" in title.group(1) or len(title.group(1)) > TITLE_MAX:
        return ""
    return "" if labeled(title.group(1), labels) else "title"


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
    body = re.sub(r"^#{1,6}\s+", "", MARKER.sub("", line.strip()).strip())
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
    second = SECOND.search(rest.rstrip(".!?"))
    if label in FREE:
        if not rest:
            return False, f"empty: nothing follows {m.group(1)}:", 0
    elif label == "open":
        if not rest.endswith("?"):
            return False, "Open: is for a question, and this doesn't end with one", 0
        if second:
            return False, "Open: takes one question, so a statement can't ride along with it. Put the statement on its own line", 0
        if not QUESTION.match(rest):
            return False, ("Open: starts with the question word (is, does, should, what, which), so a statement can't lead into it. "
                           "Put the statement on its own line"), 0
    else:
        if not re.match(r"I\b", rest):
            return False, "Me: is first person, and this doesn't start with I", 0
        if second:
            return False, "Me: takes one sentence, so a second claim can't ride on the first", 0
    for hit in NOBODY.finditer(rest):           # every one of them: a second claim can't hide behind a first that's asked
        if not (label == "open" and ASKS_IT.fullmatch(rest[:hit.start()])):
            return False, (f"says what nobody did ({hit.group(0)!r}): one run can't know that. Say what you did yourself in a Me: line, "
                           "quote the source, or ask it outright in an Open: line"), 0
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
    out = run(raw.decode("utf-8-sig", "replace"), sources)   # -sig: a byte-order mark isn't part of the first line
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
