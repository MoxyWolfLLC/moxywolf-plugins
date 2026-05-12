# BibTeX Parser Script

Use this Python script to parse existing .bib files. Run it via the Bash tool.

## Parser Script

```python
#!/usr/bin/env python3
"""
Parse a BibTeX file and output JSON with entry metadata.
Usage: python3 parse_bibtex.py input.bib
"""
import sys
import re
import json

def parse_bibtex(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    entries = []
    # Match BibTeX entries: @type{key, ... }
    # Use a state machine approach for proper brace matching
    pattern = re.compile(r'@(\w+)\s*\{', re.IGNORECASE)

    for match in pattern.finditer(content):
        entry_type = match.group(1).lower()
        if entry_type == 'comment' or entry_type == 'string' or entry_type == 'preamble':
            continue

        start = match.end()
        brace_depth = 1
        pos = start
        while pos < len(content) and brace_depth > 0:
            if content[pos] == '{':
                brace_depth += 1
            elif content[pos] == '}':
                brace_depth -= 1
            pos += 1

        entry_body = content[start:pos - 1]

        # Extract citation key (everything before the first comma)
        key_match = re.match(r'\s*([^,\s]+)\s*,', entry_body)
        if not key_match:
            continue
        citation_key = key_match.group(1)

        # Extract fields
        fields = {}
        field_body = entry_body[key_match.end():]

        # Match field = {value} or field = "value" or field = number
        field_pattern = re.compile(
            r'(\w+)\s*=\s*(?:\{((?:[^{}]|\{[^{}]*\})*)\}|"([^"]*)"|(\d+))',
            re.DOTALL
        )
        for field_match in field_pattern.finditer(field_body):
            field_name = field_match.group(1).lower()
            field_value = (
                field_match.group(2) or
                field_match.group(3) or
                field_match.group(4) or
                ''
            )
            # Clean up whitespace
            field_value = re.sub(r'\s+', ' ', field_value).strip()
            fields[field_name] = field_value

        entries.append({
            'type': entry_type,
            'key': citation_key,
            'fields': fields,
            'has_abstract': 'abstract' in fields and len(fields.get('abstract', '')) > 10,
            'has_url': 'url' in fields and len(fields.get('url', '')) > 0
        })

    return entries

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python3 parse_bibtex.py input.bib", file=sys.stderr)
        sys.exit(1)

    entries = parse_bibtex(sys.argv[1])
    print(json.dumps(entries, indent=2))
```

## Usage

```bash
# Save the parser script
cat > /tmp/parse_bibtex.py << 'PYEOF'
# (paste the script above)
PYEOF

# Run it on a .bib file
python3 /tmp/parse_bibtex.py /path/to/bibliography.bib
```

## Output Format

The script outputs a JSON array of entries:

```json
[
  {
    "type": "article",
    "key": "smith_resilience_2024",
    "fields": {
      "author": "Smith, John and Doe, Jane",
      "title": "Building Cyber Resilience",
      "year": "2024",
      "url": "https://example.com/article"
    },
    "has_abstract": false,
    "has_url": true
  }
]
```

Use `has_abstract` to identify entries needing abstract generation.
Use `has_url` to identify entries where content can be fetched.

## Reassembly

After enriching entries with abstracts, reassemble the .bib file by:

1. Reading the original file
2. For each entry that was enriched, inserting the `abstract` field before the closing brace
3. Preserving all original formatting and fields for entries that were not modified
4. Writing the complete output to the destination file

Alternatively, rebuild the entire file from parsed data using the formatting rules in `bibtex-format.md`.
