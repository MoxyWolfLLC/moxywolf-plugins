#!/usr/bin/env python3
"""
smart_quotes.py — apply typographer's quotes to a markdown post body, preserving
YAML frontmatter and JSON-LD script blocks exactly.

Why this is a script and not ad-hoc code:
The /blog-publish skill writes the post into the publishing repo. If we ad-hoc Python
each publish, we hit the same YAML-breaking bug we hit before — curly-quoting
the YAML frontmatter and breaking the static-site-generator build. This script
encodes the exact split logic so the bug doesn't return.

Usage:
    python3 smart_quotes.py --in <source-md> --out <dest-md>
    python3 smart_quotes.py --in <source-md> --in-place

Behavior:
- YAML frontmatter (delimited by leading `---\n...\n---\n`): curly quotes are
  normalized back to straight ASCII. YAML parsers don't recognize curly
  quotes as string delimiters — they're treated as literal characters in a
  plain scalar. If a value contains a colon-space, that splits the key and
  produces invalid YAML. Forcing straight quotes in the frontmatter keeps
  the build green.
- <script type="application/ld+json">...</script> blocks in the body: same
  treatment as YAML — curly quotes normalized to straight, because JSON
  requires straight double quotes.
- Markdown body text outside those blocks: typographer's (curly) quotes
  applied. Existing curly quotes in the body are left as-is.
- Em-dashes / en-dashes: not touched (this script is quotes-only).

Quote transform rules for body text (single pass per text region):
- `"` after start/whitespace/punctuation → left double `“` ("LEFT DOUBLE QUOTATION MARK")
- `"` after a letter or digit → right double `”`
- `'` after a letter or digit (apostrophe in contractions, possessives) → right single `’`
- `'` after start/whitespace/punctuation followed by non-space → left single `‘`
- Any remaining straight `"` defaults to left double; remaining `'` defaults to right single.

Quote rules for YAML frontmatter and JSON-LD script blocks:
- All curly quotes (left/right double, left/right single) → straight ASCII.

Exit codes:
- 0: success, file written.
- 2: input file not found.
- 3: malformed frontmatter (unmatched `---` delimiters).
"""

import argparse
import re
import sys
from pathlib import Path

LDQUO = "“"  # "  LEFT DOUBLE QUOTATION MARK
RDQUO = "”"  # "  RIGHT DOUBLE QUOTATION MARK
LSQUO = "‘"  # '  LEFT SINGLE QUOTATION MARK
RSQUO = "’"  # '  RIGHT SINGLE QUOTATION MARK


def force_straight_quotes(text):
    """
    Convert any curly quotes back to straight ASCII (the dumb version).
    Use this on regions where naive replacement is safe — generally JSON
    blocks, where content is machine-generated and already has straight
    string delimiters.

    For YAML, prefer normalize_yaml_quotes (below). Naive curly→straight
    in YAML produces invalid scalars when the original used curly singles
    as the wrapping AND the content contains apostrophes (e.g.,
    `excerpt: ‘We wrote about AI's polish bias.'` → after naive replace,
    `excerpt: 'We wrote about AI's polish bias.'` which YAML can't parse).
    """
    return (
        text
        .replace(LDQUO, '"')
        .replace(RDQUO, '"')
        .replace(LSQUO, "'")
        .replace(RSQUO, "'")
    )


# Regex matching a YAML mapping line where the value is wrapped in curly
# quotes: e.g.  `title: "..."`  or  `excerpt: '...'` (with curly quotes).
# Groups: 1=prefix (key + colon + spaces), 2=opening curly quote,
# 3=content between curly quotes, 4=closing curly quote, 5=trailing space.
_YAML_CURLY_WRAPPED_VALUE = re.compile(
    r'^(\s*[\w-]+\s*:\s*)([“”‘’])(.*)([“”‘’])(\s*)$'
)

_DOUBLE_CURLY = (LDQUO, RDQUO)


def normalize_yaml_quotes(text):
    """
    Convert curly quotes in a YAML frontmatter region to straight ASCII
    such that the result is still parseable YAML.

    Per-line strategy:

    - If the line is a mapping entry whose value is wrapped in curly
      quotes, pick the wrapping character (straight single or double)
      that doesn't collide with any straight-equivalent quote inside
      the content.
    - If the line isn't a wrapped scalar (no quotes, or block scalars,
      or whatever), just do the dumb curly→straight replacement.

    This handles the common authoring patterns where a writer typed
    "curly-styled" values:
        title: "Eating our own dogfood: how..."
        excerpt: 'We wrote about AI's polish bias.'  ← apostrophe inside

    For the apostrophe-inside case, the wrapping flips to straight
    double quotes so the YAML stays valid.
    """
    out_lines = []
    for line in text.split("\n"):
        m = _YAML_CURLY_WRAPPED_VALUE.match(line)
        if m is None:
            # Not a curly-wrapped scalar. Dumb-convert any stray curly
            # quotes anyway (rare but harmless).
            out_lines.append(force_straight_quotes(line))
            continue

        prefix, _open_q, content, _close_q, suffix = m.groups()
        # Convert curly quotes INSIDE the content to straight equivalents.
        content_straight = force_straight_quotes(content)
        has_single_inside = "'" in content_straight
        has_double_inside = '"' in content_straight

        # Pick a wrapping that doesn't collide with content.
        if not has_double_inside:
            wrapped = f'"{content_straight}"'
        elif not has_single_inside:
            wrapped = f"'{content_straight}'"
        else:
            # Content has both. Escape inner doubles with backslash and
            # use double-quote wrapping (YAML double-quoted scalar style).
            escaped = content_straight.replace("\\", "\\\\").replace('"', '\\"')
            wrapped = f'"{escaped}"'

        out_lines.append(f"{prefix}{wrapped}{suffix}")

    return "\n".join(out_lines)


def split_frontmatter(text):
    """
    Split text into (frontmatter, body) where frontmatter includes the
    leading `---\\n`, the YAML, and the trailing `---\\n`. If the text has no
    frontmatter, returns ('', text).
    """
    if not text.startswith("---\n"):
        return "", text
    # Find the closing `---` line
    m = re.search(r"\n---\n", text[4:])
    if m is None:
        # Malformed frontmatter
        return None, None
    end = 4 + m.start() + len("\n---\n")
    return text[:end], text[end:]


def split_around_jsonld(body):
    """
    Split body into a list of (kind, content) tuples where kind is either
    'text' or 'jsonld'. JSON-LD blocks are <script type="application/ld+json">
    ... </script>. The split preserves the script blocks verbatim.
    """
    pattern = re.compile(
        r'(<script\s+type="application/ld\+json"[^>]*>.*?</script>)',
        re.DOTALL | re.IGNORECASE,
    )
    parts = pattern.split(body)
    result = []
    for part in parts:
        if pattern.fullmatch(part):
            result.append(("jsonld", part))
        else:
            result.append(("text", part))
    return result


def apply_smart_quotes(text):
    """
    Apply typographer's quote rules to a chunk of markdown body text.
    The order matters: single quotes first (apostrophes are common and easy
    to disambiguate), then double quotes.
    """
    # --- Single quotes ---
    # Contractions and possessives: ' after a letter or digit → right single
    text = re.sub(r"(?<=[A-Za-z0-9])'", RSQUO, text)
    # Opening single quote: ' at start of string or after whitespace/opening
    # punctuation, followed by a non-space character → left single
    text = re.sub(r"(^|[\s\(\[\{<])'(?=\S)", lambda m: m.group(1) + LSQUO, text)
    # Any remaining straight ' → right single (closing quote default)
    text = text.replace("'", RSQUO)

    # --- Double quotes ---
    # Opening double quote: " at start of string or after whitespace/opening
    # punctuation, followed by a non-space character → left double
    text = re.sub(r'(^|[\s\(\[\{<])"(?=\S)', lambda m: m.group(1) + LDQUO, text)
    # Closing double quote: " after a letter, digit, or closing punctuation
    # → right double
    text = re.sub(r'(?<=[A-Za-z0-9\.\,\!\?\;\:\)\]\}])"', RDQUO, text)
    # Any remaining straight " → left double (opening default)
    text = text.replace('"', LDQUO)

    return text


def transform(text):
    """
    Top-level transform.

    1. Split off YAML frontmatter. Force any curly quotes in the
       frontmatter back to straight ASCII (YAML parsers need straight
       quotes as string delimiters; curly quotes break parsing).
    2. Split the body around JSON-LD <script> blocks.
    3. For each text chunk between JSON-LD blocks: apply smart quotes
       (straight → curly).
    4. For each JSON-LD block: force straight quotes (JSON requires
       straight, and a curly quote inside a JSON value breaks parsers).
    5. Reassemble.
    """
    frontmatter, body = split_frontmatter(text)
    if frontmatter is None:
        raise ValueError("Malformed frontmatter: opening --- without closing ---")

    # YAML frontmatter MUST have straight quotes — and the wrapping
    # quote character has to be picked so it doesn't collide with quotes
    # inside the value (e.g., apostrophes in a single-quoted scalar).
    frontmatter = normalize_yaml_quotes(frontmatter)

    chunks = split_around_jsonld(body)
    transformed_chunks = []
    for kind, content in chunks:
        if kind == "text":
            transformed_chunks.append(apply_smart_quotes(content))
        else:
            # JSON-LD block — force straight quotes (JSON requires it).
            transformed_chunks.append(force_straight_quotes(content))

    return frontmatter + "".join(transformed_chunks)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--in", dest="input", required=True, help="Source markdown file")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--out", dest="output", help="Destination markdown file")
    group.add_argument("--in-place", action="store_true", help="Rewrite the input file in place")
    args = parser.parse_args(argv)

    src = Path(args.input)
    if not src.exists():
        print(f"smart_quotes: input file not found: {src}", file=sys.stderr)
        return 2

    raw = src.read_text(encoding="utf-8")
    try:
        result = transform(raw)
    except ValueError as e:
        print(f"smart_quotes: {e}", file=sys.stderr)
        return 3

    dst = src if args.in_place else Path(args.output)
    dst.write_text(result, encoding="utf-8")
    print(f"smart_quotes: wrote {dst}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
