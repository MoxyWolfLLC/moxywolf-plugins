#!/usr/bin/env python3
"""How much of Claude's sampled wording survives to publish?

Anthropic's support page names "heavily edited, paraphrased, translated, or
mixed into other writing" as a case where the mark may not be detectable.
That is a description of the 4D pipeline. This measures whether a given piece
actually lands in that bucket, instead of assuming it.

Not a watermark detector. Detection needs a cryptographic key we do not have.
This measures token-sequence survival, which is the input the mark rides on.

    python3 perturbation.py draft.md published.md
"""
import difflib, re, sys, pathlib

WORD = re.compile(r"\w+(?:'\w+)?")


def survival(draft: str, published: str) -> dict[str, float]:
    """Fraction of the draft's word sequence still contiguous in the published text."""
    a, b = WORD.findall(draft.lower()), WORD.findall(published.lower())
    if not a:
        return {"kept_pct": 0.0, "longest_run": 0, "draft_words": 0, "published_words": len(b)}
    sm = difflib.SequenceMatcher(None, a, b, autojunk=False)
    blocks = [m for m in sm.get_matching_blocks() if m.size]
    return {
        "kept_pct": round(sum(m.size for m in blocks) / len(a) * 100, 1),
        # ponytail: longest run is the crude proxy for "an intact sampled passage".
        # Swap for a per-sentence scan if a single number stops being enough.
        "longest_run": max((m.size for m in blocks), default=0),
        "draft_words": len(a),
        "published_words": len(b),
    }


def _selfcheck() -> None:
    assert survival("a b c", "a b c")["kept_pct"] == 100.0
    assert survival("a b c d", "a b x y")["kept_pct"] == 50.0
    assert survival("a b c", "z z z")["kept_pct"] == 0.0
    assert survival("", "anything")["kept_pct"] == 0.0
    # rewording breaks the run even when words are reused
    r = survival("the cat sat on the mat", "on the mat there sat a cat")
    assert r["longest_run"] < 6, r
    print("ok")


if __name__ == "__main__":
    if len(sys.argv) == 2 and sys.argv[1] == "--selfcheck":
        _selfcheck(); sys.exit(0)
    d, p = (pathlib.Path(x).read_text(encoding="utf-8") for x in sys.argv[1:3])
    r = survival(d, p)
    print(f"kept={r['kept_pct']}%  longest_intact_run={r['longest_run']} words  "
          f"draft={r['draft_words']}w  published={r['published_words']}w")
