#!/usr/bin/env python3
"""GA-005: act on GitHub as the moxywolf-agent app, never under a person's login.

  agent_token.py exec [--repo owner/name] -- <command...>   run a command holding an installation token
  agent_token.py api METHOD PATH [--data JSON|-] [--repo owner/name]  one REST call; response JSON on stdout
  agent_token.py --selftest

Settings come from the file GSTACK_AGENT_APP_ENV names (github-app.env in the vault):
GITHUB_APP_ID, GITHUB_APP_INSTALLATION_ID and GITHUB_APP_KEY_FILE, the key's path relative to that
file. A token is minted per invocation and lasts an hour. It never reaches argv, stdout, stderr or a
file: git gets it through GIT_CONFIG_* environment entries, other programs through GITHUB_TOKEN.

Minting needs GitHub's /app endpoints. The Cowork cloud proxy refuses them (403, 2026-09-20); the
device shell reaches them, so this runs there. There is no fallback credential. If minting fails the
script names the endpoint and the status and stops, because a quiet fallback to a person's token is
the defect GA-005 exists to remove.

GA-006: the app has one installation per account, so the installation is resolved from the repository
being acted on rather than pinned in configuration. The repository comes from --repo, else the
{owner}/{repo} in an api path beginning repos/, else origin's URL in the working directory. The id in
github-app.env is a fallback for when none of those answers. A repository the app cannot reach is a
named refusal listing the accounts it IS installed on, never a bare 404: GitHub answers 404 both to a
repository that does not exist and to one an installation cannot see, and that ambiguity cost most of
a session on 2026-09-20.

ponytail: signs the JWT with the openssl CLI rather than a crypto library, so it runs on any host
with python and openssl and CI needs no install. Nothing caches the resolved id, because an
installation can be removed between runs and a cached id would fail as a 404 long after the cause.
"""
import base64
import json
import os
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path

API = os.environ.get("GSTACK_GITHUB_API", "https://api.github.com").rstrip("/")


def b64(raw):
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode()


def settings():
    envfile = os.environ.get("GSTACK_AGENT_APP_ENV")
    if not envfile:
        sys.exit("GSTACK_AGENT_APP_ENV is not set. Point it at the vault's github-app.env "
                 "(_Shared Knowledge/Agents and Plugins). There is no default and no fallback credential.")
    path = Path(envfile).expanduser()
    if not path.is_file():
        sys.exit(f"GSTACK_AGENT_APP_ENV names {path}, which does not exist. No other credential is tried.")
    conf = {}
    for line in path.read_text().splitlines():
        if "=" in line and not line.lstrip().startswith("#"):
            k, v = line.split("=", 1)
            conf[k.strip()] = v.strip().strip("'\"")
    missing = [k for k in ("GITHUB_APP_ID", "GITHUB_APP_INSTALLATION_ID", "GITHUB_APP_KEY_FILE") if not conf.get(k)]
    if missing:
        sys.exit(f"{path} is missing {', '.join(missing)}")
    return conf["GITHUB_APP_ID"], conf["GITHUB_APP_INSTALLATION_ID"], path.parent / conf["GITHUB_APP_KEY_FILE"]


def jwt(app_id, key):
    now = int(time.time())
    signing = (b64(json.dumps({"alg": "RS256", "typ": "JWT"}).encode()) + "." +
               b64(json.dumps({"iat": now - 60, "exp": now + 540, "iss": str(app_id)}).encode()))
    r = subprocess.run(["openssl", "dgst", "-sha256", "-sign", str(key)], input=signing.encode(), capture_output=True)
    if r.returncode:
        sys.exit(f"could not sign with {key}: {r.stderr.decode(errors='replace').strip()}")
    return signing + "." + b64(r.stdout)


def request(method, path, auth, data=None):
    url = API + "/" + path.lstrip("/")
    req = urllib.request.Request(url, method=method, data=None if data is None else json.dumps(data).encode(),
                                 headers={"Authorization": auth, "Accept": "application/vnd.github+json",
                                          "User-Agent": "moxywolf-agent", "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            return resp.status, json.loads(resp.read() or b"null")
    except urllib.error.HTTPError as e:
        try:
            body = json.loads(e.read() or b"null")
        except ValueError:
            body = None
        return e.code, body
    except (urllib.error.URLError, OSError) as e:
        return None, {"message": str(e)}


def repo_from_path(path):
    """The {owner}/{repo} in an api path that begins repos/."""
    parts = [p for p in path.strip("/").split("/") if p]
    if len(parts) >= 3 and parts[0] == "repos":
        return parts[1] + "/" + parts[2]
    return None


def repo_from_origin():
    """owner/repo from origin's URL in the working directory, https or ssh."""
    r = subprocess.run(["git", "remote", "get-url", "origin"], capture_output=True)
    if r.returncode:
        return None
    url = r.stdout.decode(errors="replace").strip()
    for sep in ("github.com:", "github.com/"):
        if sep in url:
            tail = url.split(sep, 1)[1]
            break
    else:
        return None
    if tail.endswith(".git"):
        tail = tail[:-4]
    parts = [p for p in tail.strip("/").split("/") if p]
    return "/".join(parts[:2]) if len(parts) >= 2 else None


def installation_for(repo, app_id, key):
    """The installation that owns this repository. One lookup, nothing cached."""
    auth = "Bearer " + jwt(app_id, key)
    status, body = request("GET", f"/repos/{repo}/installation", auth)
    if status == 200 and isinstance(body, dict) and body.get("id"):
        return body["id"]
    _, insts = request("GET", "/app/installations", auth)
    names = sorted((i.get("account") or {}).get("login", "?") for i in insts) if isinstance(insts, list) else []
    where = ", ".join(names) if names else "no account"
    owner = repo.split("/")[0]
    sys.exit(f"agent token not minted: the app is not installed on {owner}, so {repo} is out of its reach "
             f"(GET {API}/repos/{repo}/installation returned {status or 'no response'}). GitHub answers 404 both "
             f"to a repository that does not exist and to one an installation cannot see, so this is stated rather "
             f"than left as a 404. Installed on: {where}. The configured installation is not tried, because its "
             f"token returns the same 404.")


def mint(repo=None):
    app_id, inst, key = settings()
    if repo:
        inst = installation_for(repo, app_id, key)
    else:
        print("no repository determined (tried --repo, the api path and origin); minting from the "
              f"configured installation {inst}", file=sys.stderr)
    path = f"/app/installations/{inst}/access_tokens"
    status, body = request("POST", path, "Bearer " + jwt(app_id, key))
    if status != 201 or not isinstance(body, dict) or not body.get("token"):
        msg = (body or {}).get("message", "") if isinstance(body, dict) else ""
        sys.exit(f"agent token not minted: POST {API}{path} returned {status or 'no response'}"
                 f"{': ' + msg if msg else ''}. No other credential is tried.")
    return body["token"]


def token_env(token, base=None):
    env = dict(os.environ if base is None else base)
    n = int(env.get("GIT_CONFIG_COUNT", "0") or 0)
    header = "AUTHORIZATION: basic " + base64.b64encode(f"x-access-token:{token}".encode()).decode()
    env.update({"GIT_CONFIG_COUNT": str(n + 1), f"GIT_CONFIG_KEY_{n}": "http.https://github.com/.extraheader",
                f"GIT_CONFIG_VALUE_{n}": header, "GITHUB_TOKEN": token})
    return env


def cmd_exec(cmd, repo=None):
    if not cmd:
        sys.exit("usage: agent_token.py exec [--repo owner/name] -- <command...>")
    return subprocess.run(cmd, env=token_env(mint(repo or repo_from_origin()))).returncode


def cmd_api(method, path, data, repo=None):
    if data == "-":
        data = sys.stdin.read()
    token = mint(repo or repo_from_path(path))
    status, body = request(method.upper(), path, "token " + token, None if data is None else json.loads(data))
    print(json.dumps(body, indent=2))
    if status is None or status >= 300:
        print(f"{method.upper()} {path} returned {status}", file=sys.stderr)
        return 1
    return 0


def selftest():
    with tempfile.TemporaryDirectory() as t:
        key = Path(t) / "k.pem"
        subprocess.run(["openssl", "genrsa", "-out", str(key), "2048"], capture_output=True, check=True)
        parts = jwt(123, key).split(".")
        assert len(parts) == 3 and all(parts), "JWT has three non-empty segments"
        assert json.loads(base64.urlsafe_b64decode(parts[1] + "==").decode())["iss"] == "123"
        env = token_env("tok", {"GIT_CONFIG_COUNT": "1"})
        assert env["GIT_CONFIG_KEY_1"].endswith("extraheader") and env["GIT_CONFIG_COUNT"] == "2"
        assert "tok" not in env["GIT_CONFIG_VALUE_1"], "the header carries the token encoded, not bare"
    print("agent_token selftest: examined 4 checks, 4 passed")
    return 0


def main(argv):
    if argv[:1] == ["--selftest"]:
        return selftest()
    repo = None
    if "--repo" in argv:
        i = argv.index("--repo")
        sep = argv.index("--") if "--" in argv else len(argv)
        if i < sep and i + 1 < len(argv):
            repo = argv[i + 1]
            argv = argv[:i] + argv[i + 2:]
    if argv[:1] == ["exec"]:
        rest = argv[1:]
        return cmd_exec(rest[1:] if rest[:1] == ["--"] else rest, repo)
    if argv[:1] == ["api"] and len(argv) >= 3:
        data = argv[argv.index("--data") + 1] if "--data" in argv else None
        return cmd_api(argv[1], argv[2], data, repo)
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
