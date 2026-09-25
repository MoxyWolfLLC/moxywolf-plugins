#!/usr/bin/env python3
"""SM-003: validate a project's mistake ledger. Stdlib only.

The ledger is a markdown table in MoxyWolf Vault/Projects/<project>/11-Knowledge/mistake-ledger.md:

| id | date | what | caught_by | evidence | disposition | target | repeats |

A mistake is kept only if it became something that acts at the point of action: a check, or a
rule in a file loaded when the mistake would recur. A repeat means the earlier remedy failed, so a
repeat can be neither one_off nor the same rule again (criterion 5).

    mistake_ledger.py <ledger.md>                       validate; exit 0 clean, 1 with every failure named
    mistake_ledger.py <ledger.md> --append <rows.md>    validate ledger + new rows together, and write
                                                        the ledger only if the combination is clean
    exit 3 from --append: the rows file holds no rows. A missing ledger is created with its header
    row (criterion 8), no row is written, and nothing passed: a session that found no mistakes
    proceeds to its handoff and says so there.
"""
import json
import sys
from pathlib import Path

COLUMNS = ["id", "date", "what", "caught_by", "evidence", "disposition", "target", "repeats"]
REQUIRED = ["id", "date", "what", "caught_by", "evidence", "disposition"]
# The vocabulary has one home (XE-011), in gstack-execution. Installed plugins sit side by side,
# as they do in this repository, so the sibling path holds in both places.
VOCAB = Path(__file__).resolve().parents[2] / "gstack-execution" / "skills" / "gstack-execution" / "references" / "vocabulary.json"


def vocab_ids(group, vocab_path=VOCAB):
    concepts = json.loads(Path(vocab_path).read_text())["concepts"]
    return {c["id"] for c in concepts if c["group"] == group}


def parse(text):
    """Every table row after the COLUMNS header, anywhere in the file. Cells are stripped; `x` backticks removed."""
    rows, header = [], None
    for line in text.splitlines():
        line = line.strip()
        if not line.startswith("|"):
            continue  # a blank line or prose between rows must not end the scan (review F2)
        cells = [c.strip().strip("`").strip() for c in line.strip("|").split("|")]
        if [c.lower() for c in cells] == COLUMNS:
            header = COLUMNS
            continue
        if header is None or set("".join(cells)) <= set("-: "):
            continue
        rows.append(dict(zip(header, cells + [""] * (len(header) - len(cells)))))
    return rows


def validate(rows, caught_by, dispositions):
    failures, by_id = [], {}
    if not rows:
        return ["no rows: a ledger that examined nothing is not a clean ledger (EV-001)"]
    for r in rows:
        rid = r.get("id") or "?"
        for f in REQUIRED:
            if not r.get(f):
                failures.append(f"{rid}: missing {f}")
        if r.get("caught_by") and r["caught_by"] not in caught_by:
            failures.append(f"{rid}: caught_by {r['caught_by']!r} is not one of {sorted(caught_by)}")
        if r.get("disposition") and r["disposition"] not in dispositions:
            failures.append(f"{rid}: disposition {r['disposition']!r} is not one of {sorted(dispositions)}")
        if r.get("disposition") in ("became_check", "became_rule") and not r.get("target"):
            failures.append(f"{rid}: {r['disposition']} names no target")
        if rid in by_id:
            failures.append(f"{rid}: duplicate id")
        by_id[rid] = r
    for r in rows:
        rep = r.get("repeats")
        if not rep:
            continue
        rid, earlier = r.get("id") or "?", by_id.get(rep)
        if earlier is None:
            failures.append(f"{rid}: repeats {rep}, which is not in the ledger")
            continue
        if r.get("disposition") == "one_off":
            failures.append(f"{rid}: repeats {rep} and cannot be one_off; the earlier remedy did not hold")
        if r.get("disposition") == "became_rule" and r.get("target") == earlier.get("target"):
            failures.append(f"{rid}: repeats {rep} with the same rule target {r['target']!r}; "
                            "a rule that did not prevent the recurrence escalates to a check or another point of action")
    return failures


HEADER = "| " + " | ".join(COLUMNS) + " |\n|" + "---|" * len(COLUMNS) + "\n"


def main(argv):
    if len(argv) not in (1, 3) or (len(argv) == 3 and argv[1] != "--append"):
        print(__doc__.strip())
        return 2
    ledger = Path(argv[0])
    text = ledger.read_text() if ledger.exists() else HEADER
    if len(argv) == 3:
        new = [l for l in Path(argv[2]).read_text().splitlines() if l.strip().startswith("|")
               and [c.strip().lower() for c in l.strip().strip("|").split("|")] != COLUMNS
               and not set(l.replace("|", "")) <= set("-: ")]
        if not new:
            made = not ledger.exists()
            if made:
                ledger.write_text(HEADER)
            print(f"mistake ledger: nothing to append from {argv[2]}; "
                  + (f"created {ledger} with its header only" if made else f"{ledger} left unchanged")
                  + ". 0 rows examined, and this is not a pass")
            return 3
        text = text.rstrip("\n") + "\n" + "\n".join(new) + "\n"
    rows = parse(text)
    failures = validate(rows, vocab_ids("caught_by"), vocab_ids("mistake_disposition"))
    print(f"mistake ledger: examined {len(rows)} row(s), {len(failures)} failure(s)")
    for f in failures:
        print("  FAIL " + f)
    if failures:
        if len(argv) == 3:
            print("  ledger left unchanged")
        return 1
    if len(argv) == 3:
        ledger.write_text(text)
        print(f"  wrote {ledger}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
