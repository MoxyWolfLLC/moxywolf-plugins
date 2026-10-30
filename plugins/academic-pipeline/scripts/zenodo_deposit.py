#!/usr/bin/env python3
"""AP-004: deposit one artifact folder on Zenodo as its own record.

  zenodo_deposit.py draft   <folder> [--sandbox] [--token-file F]   create a draft from <folder>/.zenodo.json
  zenodo_deposit.py publish <folder> [--sandbox] [--token-file F]   publish the draft `draft` recorded

A draft can be edited or deleted on Zenodo. A published record can't be deleted, only versioned,
so `publish` is its own subcommand and the agent runs it only on the user's explicit word.
The token comes from ZENODO_TOKEN or a KEY=value file (--token-file). It is never printed.

ponytail: stdlib urllib, one zip in memory. The transport is injectable so the tests never touch
the network. Fine for artifacts of a few hundred MB; stream the upload if one gets bigger.
"""
import argparse
import io
import json
import os
import sys
import urllib.error
import urllib.request
import zipfile

LIVE, SANDBOX = "https://zenodo.org/api", "https://sandbox.zenodo.org/api"
STATE = ".zenodo-deposit.json"
SKIP_DIRS, SKIP_FILES = {"__pycache__", ".git"}, {STATE, ".DS_Store"}


def http(method, url, token, body=None, ctype="application/json"):
    """Default transport: returns (status, parsed JSON or {})."""
    data = json.dumps(body).encode() if isinstance(body, (dict, list)) else body
    req = urllib.request.Request(url, data=data, method=method,
                                 headers={"Authorization": f"Bearer {token}", "Content-Type": ctype})
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            raw = r.read()
            return r.status, (json.loads(raw) if raw else {})
    except urllib.error.HTTPError as e:
        return e.code, {"message": e.read().decode(errors="replace")[:500]}


def read_token(token_file=None):
    if token_file:
        for line in open(token_file, encoding="utf-8"):
            k, _, v = line.strip().partition("=")
            if k.strip() in ("ZENODO_TOKEN", "ZENODO_ACCESS_TOKEN") and v.strip():
                return v.strip().strip('"').strip("'")
        return None
    return (os.environ.get("ZENODO_TOKEN") or "").strip() or None


def zip_folder(folder):
    slug, buf = os.path.basename(os.path.normpath(folder)), io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        for root, dirs, files in os.walk(folder):
            dirs[:] = sorted(d for d in dirs if d not in SKIP_DIRS)
            for f in sorted(files):
                if f in SKIP_FILES or f.endswith(".pyc"):
                    continue
                path = os.path.join(root, f)
                z.write(path, os.path.join(slug, os.path.relpath(path, folder)))
    return slug, buf.getvalue()


def ok(status, out, what):
    if status >= 300:
        raise SystemExit(f"zenodo refused {what}: HTTP {status} {out.get('message', '')}")
    return out


def draft(folder, token, base, transport=http):
    meta = json.load(open(os.path.join(folder, ".zenodo.json"), encoding="utf-8"))
    slug, blob = zip_folder(folder)
    dep = ok(*transport("POST", f"{base}/deposit/depositions", token, {}), "creating the draft")
    ok(*transport("PUT", f"{dep['links']['bucket']}/{slug}.zip", token, blob, "application/octet-stream"), "the upload")
    ok(*transport("PUT", f"{base}/deposit/depositions/{dep['id']}", token, {"metadata": meta}), "the metadata")
    state = {"id": dep["id"], "html": dep["links"]["html"], "base": base,
             "reserved_doi": ((dep.get("metadata") or {}).get("prereserve_doi") or {}).get("doi")}
    json.dump(state, open(os.path.join(folder, STATE), "w"), indent=2)
    return state


def publish(folder, token, base, transport=http):
    path = os.path.join(folder, STATE)
    if not os.path.exists(path):
        raise SystemExit(f"no draft recorded in {path}; run `draft` first")
    state = json.load(open(path))
    if state.get("doi"):
        raise SystemExit(f"already published: https://doi.org/{state['doi']}")
    if state.get("base", base) != base:
        raise SystemExit(f"the draft was made on {state['base']}, not {base}")
    done = ok(*transport("POST", f"{base}/deposit/depositions/{state['id']}/actions/publish", token), "publishing")
    state.update(doi=done["doi"], record=done["links"]["html"])
    json.dump(state, open(path, "w"), indent=2)
    return state


def main(argv=None, transport=http):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("action", choices=("draft", "publish"))
    ap.add_argument("folder")
    ap.add_argument("--sandbox", action="store_true")
    ap.add_argument("--token-file")
    a = ap.parse_args(argv)
    token = read_token(a.token_file)
    if not token:
        print("no Zenodo token: set ZENODO_TOKEN or pass --token-file (scopes deposit:write, deposit:actions)",
              file=sys.stderr)
        return 2
    base = SANDBOX if a.sandbox else LIVE
    try:
        if a.action == "draft":
            s = draft(a.folder, token, base, transport)
            print(f"draft created: {s['html']}  reserved DOI {s['reserved_doi']} (live only once published)")
        else:
            s = publish(a.folder, token, base, transport)
            print(f"published: https://doi.org/{s['doi']}  ({s['record']})")
    except SystemExit as e:
        print(str(e).replace(token, "[token]"), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
