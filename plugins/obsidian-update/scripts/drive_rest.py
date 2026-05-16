#!/usr/bin/env python3
"""
Google Drive REST helper for the obsidian-update plugin.

Read and write files in the MoxyWolf Vault (a Shared/Team Drive) directly via the
Google Drive v3 REST API, without going through any third-party MCP intermediary.

This exists for the **scheduled-task VM** path, where the vault is NOT mounted as
a workspace folder and the only way to update files is the REST API. In an
interactive Cowork session, the vault is mounted under
`/sessions/.../mnt/MoxyWolf Vault/` and you should use the file tools (Read /
Write / Edit) instead of this helper.

## Authentication

This helper uses a **Google service account** stored as a JSON key file. The
service account must be granted at least Editor access to the Shared Drive that
contains the MoxyWolf Vault.

One-time setup:

1. In Google Cloud Console, create a project (or reuse an existing one).
2. Enable the Drive API on the project.
3. Create a service account; download its JSON key.
4. In Google Drive, open the Shared Drive (or its parent folder), click
   "Manage members," and add the service account email as "Content manager"
   or "Manager".
5. Save the JSON key on the Mac that will run scheduled tasks at:
       ~/.config/moxywolf/drive-service-account.json
   (or set the env var DRIVE_SERVICE_ACCOUNT_JSON to a different path).

## Usage

    # Download a file by file ID:
    python3 drive_rest.py download --file-id <id> --out /tmp/file.md

    # Upload/replace a file's content by file ID:
    python3 drive_rest.py upload --file-id <id> --in /tmp/new.md --mime text/plain

    # Search for files by name within a folder:
    python3 drive_rest.py search \\
        --folder-id <folder_id> --name "KANBAN_VIEW.md"

    # List children of a folder:
    python3 drive_rest.py ls --folder-id <folder_id>

All commands honor `supportsAllDrives=true` and `supportsTeamDrives=true`
so Team Drive operations don't 404.

The script is pure stdlib for HTTP — uses `urllib`. Token signing requires
the `cryptography` and `PyJWT` packages (both standard in modern Pythons).
If unavailable in the sandbox, install with:
    pip3 install --break-system-packages cryptography PyJWT
"""
from __future__ import annotations

import argparse
import base64
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path


DEFAULT_SA_PATH = "~/.config/moxywolf/drive-service-account.json"
DRIVE_API = "https://www.googleapis.com/drive/v3"
UPLOAD_API = "https://www.googleapis.com/upload/drive/v3"
SCOPE = "https://www.googleapis.com/auth/drive"
TOKEN_URL = "https://oauth2.googleapis.com/token"

# Tiny in-memory token cache for the script's lifetime.
_TOKEN: dict = {"access_token": None, "expires_at": 0}


def _service_account_path() -> Path:
    raw = os.environ.get("DRIVE_SERVICE_ACCOUNT_JSON", DEFAULT_SA_PATH)
    return Path(raw).expanduser()


def _load_service_account() -> dict:
    p = _service_account_path()
    if not p.exists():
        sys.exit(
            f"ERROR: Drive service account JSON not found at {p}\n"
            f"Set DRIVE_SERVICE_ACCOUNT_JSON or place the file at the default path.\n"
            f"See the docstring at the top of this script for setup instructions."
        )
    return json.loads(p.read_text())


def _b64url(b: bytes) -> str:
    return base64.urlsafe_b64encode(b).rstrip(b"=").decode("ascii")


def _get_access_token() -> str:
    """Exchange the service account JWT for an OAuth access token."""
    if _TOKEN["access_token"] and _TOKEN["expires_at"] > time.time() + 60:
        return _TOKEN["access_token"]

    try:
        import jwt  # PyJWT
    except ImportError:
        sys.exit(
            "ERROR: PyJWT is required. Install with:\n"
            "  pip3 install --break-system-packages PyJWT cryptography"
        )

    sa = _load_service_account()
    now = int(time.time())
    payload = {
        "iss": sa["client_email"],
        "scope": SCOPE,
        "aud": TOKEN_URL,
        "iat": now,
        "exp": now + 3600,
    }
    assertion = jwt.encode(payload, sa["private_key"], algorithm="RS256")

    data = urllib.parse.urlencode({
        "grant_type": "urn:ietf:params:oauth:grant-type:jwt-bearer",
        "assertion": assertion,
    }).encode("utf-8")
    req = urllib.request.Request(TOKEN_URL, data=data, method="POST")
    req.add_header("Content-Type", "application/x-www-form-urlencoded")
    with urllib.request.urlopen(req, timeout=30) as resp:
        body = json.loads(resp.read().decode("utf-8"))
    _TOKEN["access_token"] = body["access_token"]
    _TOKEN["expires_at"] = time.time() + int(body.get("expires_in", 3600))
    return _TOKEN["access_token"]


def _drive_request(method: str, url: str, params: dict | None = None,
                   body: bytes | None = None, headers: dict | None = None) -> tuple[int, bytes, dict]:
    """Make an authenticated Drive API request. Returns (status, body_bytes, headers_dict)."""
    if params:
        # Always include shared-drive params.
        params = {**params, "supportsAllDrives": "true", "supportsTeamDrives": "true",
                  "includeItemsFromAllDrives": "true"}
        url = f"{url}?{urllib.parse.urlencode(params)}"
    req = urllib.request.Request(url, data=body, method=method)
    req.add_header("Authorization", f"Bearer {_get_access_token()}")
    if headers:
        for k, v in headers.items():
            req.add_header(k, v)
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            return resp.status, resp.read(), dict(resp.headers)
    except urllib.error.HTTPError as e:
        return e.code, e.read(), dict(e.headers)


def cmd_download(args) -> int:
    url = f"{DRIVE_API}/files/{args.file_id}"
    status, body, _ = _drive_request("GET", url, params={"alt": "media"})
    if status != 200:
        print(f"ERROR {status}: {body.decode('utf-8', errors='replace')[:500]}", file=sys.stderr)
        return 1
    out = Path(args.out).expanduser()
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(body)
    print(f"Downloaded {len(body)} bytes to {out}")
    return 0


def cmd_upload(args) -> int:
    """Replace the content of an existing file. Use create for new files."""
    in_path = Path(args.in_).expanduser()
    if not in_path.exists():
        print(f"ERROR: input file {in_path} does not exist", file=sys.stderr)
        return 2
    payload = in_path.read_bytes()
    url = f"{UPLOAD_API}/files/{args.file_id}"
    status, body, _ = _drive_request(
        "PATCH", url,
        params={"uploadType": "media"},
        body=payload,
        headers={"Content-Type": args.mime},
    )
    if status not in (200, 201):
        print(f"ERROR {status}: {body.decode('utf-8', errors='replace')[:500]}", file=sys.stderr)
        return 1
    meta = json.loads(body)
    print(f"Uploaded {len(payload)} bytes to {meta.get('name')} (id={meta.get('id')})")
    return 0


def cmd_search(args) -> int:
    """Search for files within a folder by name (or anywhere if no folder)."""
    parts = []
    if args.folder_id:
        parts.append(f"'{args.folder_id}' in parents")
    if args.name:
        # Escape single quotes in the name for Drive's query language.
        safe = args.name.replace("'", "\\'")
        parts.append(f"name = '{safe}'")
    parts.append("trashed = false")
    q = " and ".join(parts)
    status, body, _ = _drive_request(
        "GET", f"{DRIVE_API}/files",
        params={"q": q, "fields": "files(id,name,mimeType,modifiedTime,parents)",
                "corpora": "allDrives"},
    )
    if status != 200:
        print(f"ERROR {status}: {body.decode('utf-8', errors='replace')[:500]}", file=sys.stderr)
        return 1
    print(body.decode("utf-8"))
    return 0


def cmd_ls(args) -> int:
    return cmd_search(argparse.Namespace(folder_id=args.folder_id, name=None))


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)

    pd = sub.add_parser("download", help="Download a file by ID")
    pd.add_argument("--file-id", required=True)
    pd.add_argument("--out", required=True)
    pd.set_defaults(func=cmd_download)

    pu = sub.add_parser("upload", help="Replace an existing file's content")
    pu.add_argument("--file-id", required=True)
    pu.add_argument("--in", dest="in_", required=True, help="Local source file")
    pu.add_argument("--mime", default="text/plain")
    pu.set_defaults(func=cmd_upload)

    ps = sub.add_parser("search", help="Search for files within a folder by name")
    ps.add_argument("--folder-id")
    ps.add_argument("--name")
    ps.set_defaults(func=cmd_search)

    pl = sub.add_parser("ls", help="List children of a folder")
    pl.add_argument("--folder-id", required=True)
    pl.set_defaults(func=cmd_ls)

    args = p.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
