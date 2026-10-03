"""python3 -m pilotmod.slug "<text>": prints the text as a URL slug."""
import re
import sys


def slug(text):
    return re.sub(r"[\W_]+", "-", text.lower()).strip("-")


if __name__ == "__main__":
    print(slug(" ".join(sys.argv[1:])))
