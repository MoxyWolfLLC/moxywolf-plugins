#!/usr/bin/env python3
"""Layer B — perturb the sampled token sequence without losing the voice.

WHAT THIS DOES NOT DO
---------------------
It does not detect or verify removal of a text watermark. Claude's mark is
SynthID-Text-class: carried in the choice among equally valid words, detectable
only with a cryptographic key we do not hold, and only in private preview. Any
tool claiming deterministic removal in pure Python is lying. This one measures
the input the mark rides on and gates on it.

WHAT IT DOES
------------
Anthropic's support page names the conditions under which a mark may stop being
detectable: text "heavily edited, paraphrased, translated, or mixed into other
writing", or too short for a reliable signal. That is a description of what the
4D pipeline already does. This tool makes it measurable and enforced rather than
assumed.

    --brief  raw.md live.md   → per-paragraph rewrite brief, worst survivors first
    --gate   raw.md live.md   → exit 1 unless survival is under the threshold

The rewrite itself is done by the agent against the writer's voice profile.
That direction matters: rewriting toward the voice profile resamples from a
different distribution AND improves the prose. Rewriting toward entropy — what
a generic de-watermarker does — resamples and degrades. Same mechanism, opposite
outcome, which is the whole reason this lives in 4d-blog-engine and not in a
standalone stripper.

Pairs with prose_lint.py: run this for the sequence, that for the register.
"""
import argparse, difflib, re, sys, pathlib

WORD = re.compile(r"\w+(?:'\w+)?")

# ponytail: 50% is a placeholder, NOT a calibrated figure. Detection needs a key
# nobody outside the preview has, so this threshold cannot be validated against
# ground truth by us or by anyone else here. Treat it as a dial, not a fact —
# raise it if rewrites are costing more voice than they are worth.
DEFAULT_THRESHOLD = 50.0
SHORT_PIECE_WORDS = 300   # support page: "very short" passages carry little signal


def survival(draft: str, published: str) -> dict:
    a, b = WORD.findall(draft.lower()), WORD.findall(published.lower())
    if not a:
        return {"kept_pct": 0.0, "longest_run": 0, "draft_words": 0, "published_words": len(b)}
    sm = difflib.SequenceMatcher(None, a, b, autojunk=False)
    blocks = [m for m in sm.get_matching_blocks() if m.size]
    return {
        "kept_pct": round(sum(m.size for m in blocks) / len(a) * 100, 1),
        "longest_run": max((m.size for m in blocks), default=0),
        "draft_words": len(a),
        "published_words": len(b),
    }


def paragraphs(text: str) -> list[str]:
    return [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]


def per_paragraph(raw: str, live: str) -> list[dict]:
    """Match each raw paragraph to its closest live counterpart and score it.

    ponytail: greedy nearest-match, O(n*m) on paragraph counts. Fine at blog
    scale (tens). Switch to an alignment pass if a piece ever has hundreds.
    """
    lps = paragraphs(live)
    out = []
    for i, rp in enumerate(paragraphs(raw)):
        best = max(
            (survival(rp, lp) | {"live": lp} for lp in lps),
            key=lambda r: r["kept_pct"],
            default={"kept_pct": 0.0, "longest_run": 0, "draft_words": len(WORD.findall(rp)), "live": ""},
        )
        out.append({"idx": i + 1, "raw": rp, **best})
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description="Measure and gate token-sequence survival.")
    ap.add_argument("raw", type=pathlib.Path, help="Pre-edit draft (draft.raw.md).")
    ap.add_argument("live", type=pathlib.Path, help="Current text.")
    ap.add_argument("--brief", action="store_true", help="Emit a per-paragraph rewrite brief.")
    ap.add_argument("--gate", action="store_true", help="Exit 1 if survival exceeds threshold.")
    ap.add_argument("--threshold", type=float, default=DEFAULT_THRESHOLD)
    ap.add_argument("--top", type=int, default=8, help="Paragraphs to list in the brief.")
    a = ap.parse_args()

    raw, live = a.raw.read_text(encoding="utf-8"), a.live.read_text(encoding="utf-8")
    whole = survival(raw, live)

    if whole["published_words"] < SHORT_PIECE_WORDS:
        print(f"NOTE piece is {whole['published_words']}w — under {SHORT_PIECE_WORDS}w, "
              f"which the vendor doc calls too short for a reliable signal.")

    print(f"SURVIVAL kept={whole['kept_pct']}% longest_run={whole['longest_run']}w "
          f"raw={whole['draft_words']}w live={whole['published_words']}w "
          f"threshold={a.threshold}%")

    if a.brief:
        rows = sorted(per_paragraph(raw, live), key=lambda r: -r["kept_pct"])[: a.top]
        print("\nParagraphs still carrying the most original wording — rewrite these first,")
        print("toward the voice profile, not away from it:\n")
        for r in rows:
            head = " ".join(r["raw"].split()[:12])
            print(f"  ¶{r['idx']:>3}  kept={r['kept_pct']:>5}%  run={r['longest_run']:>3}w  {head}…")

    if a.gate and whole["kept_pct"] > a.threshold:
        print(f"\nGATE FAIL survival {whole['kept_pct']}% > {a.threshold}%. "
              f"Rewrite further, or lower the bar deliberately with --threshold.")
        return 1
    if a.gate:
        print(f"\nGATE PASS survival {whole['kept_pct']}% <= {a.threshold}%.")
    return 0


def _selfcheck() -> None:
    assert survival("a b c", "a b c")["kept_pct"] == 100.0
    assert survival("a b c d", "a b x y")["kept_pct"] == 50.0
    assert survival("", "x")["kept_pct"] == 0.0
    r = survival("the cat sat on the mat", "on the mat there sat a cat")
    assert r["longest_run"] < 6, r
    pp = per_paragraph("one two three\n\nfour five six", "one two three\n\nzzz yyy xxx")
    assert pp[0]["kept_pct"] == 100.0 and pp[1]["kept_pct"] == 0.0, pp
    assert len(paragraphs("a\n\n\nb\n\n")) == 2
    print("ok")


if __name__ == "__main__":
    if len(sys.argv) == 2 and sys.argv[1] == "--selfcheck":
        _selfcheck(); sys.exit(0)
    sys.exit(main())
