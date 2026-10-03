"""python3 -m pilotmod.slug "<text>": prints the text as a URL slug."""
import sys


def slug(text):
    # Letters and digits by explicit predicate: \w would also keep numerics like ¼ and the underscore.
    return "-".join("".join(c if c.isalpha() or c.isdigit() else " " for c in text.lower()).split())


if __name__ == "__main__":
    print(slug(" ".join(sys.argv[1:])))
