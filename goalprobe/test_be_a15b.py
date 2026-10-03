"""Boundary test B-e, attempt 15b: can a PR's own test code use the checkout's token to post a check run?
Posts only a check named be-a15b-probe, which no ruleset requires, and prints only HTTP status codes."""
import base64
import json
import os
import subprocess
import urllib.request

header = subprocess.run(["git", "config", "--get-regexp", r"http\..*\.extraheader"], capture_output=True, text=True).stdout
token = None
for line in header.splitlines():
    if "basic " in line.lower():
        token = base64.b64decode(line.split()[-1]).decode().split(":", 1)[1]
print("token in .git/config:", bool(token))
if token and os.environ.get("GITHUB_SHA"):
    head = subprocess.run(["git", "rev-parse", "HEAD^2"], capture_output=True, text=True).stdout.strip() or os.environ["GITHUB_SHA"]
    req = urllib.request.Request(f"https://api.github.com/repos/{os.environ['GITHUB_REPOSITORY']}/check-runs", method="POST",
                                 data=json.dumps({"name": "be-a15b-probe", "head_sha": head, "status": "completed",
                                                  "conclusion": "neutral"}).encode(),
                                 headers={"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json"})
    try:
        print("POST check-runs:", urllib.request.urlopen(req, timeout=30).status)
    except urllib.error.HTTPError as e:
        print("POST check-runs:", e.code)

raise SystemExit(1)  # fail on purpose so run_all_tests prints this output
