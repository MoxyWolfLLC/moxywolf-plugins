#!/usr/bin/env python3
"""A small, refusing client for the GTM API MCP server (https://mcp.gtm-api.com/mcp).

It speaks JSON-RPC to the server's three meta-tools (list_toolsets, get_toolset_tools, call_tool)
and holds three rules no caller can switch off:

1. Read tools run freely. The list lives in tool_policy.json, built from the verbose catalog.
2. An outward tool runs only as `execute --ledger FILE --item ID`, for an item the Release Owner
   approved in today's batch, with exactly the approved arguments. It goes preview first, checks
   the preview names the same arguments, then confirms with the preview's commit_token.
3. A rate limit, quota hit, block or checkpoint is an answer, not an error. The client reports it,
   stops that bucket (or the whole day) in the ledger, and never loops or retries.

Every tool not on either list is refused, including mass actions, profile edits, smart-limit
changes, webhooks, browser operations and the custom-request escape hatch.

Credentials: GTM_API_KEY in the environment is sent as `Authorization: Bearer ...`. Under a proxy
that injects auth (for example `pplx credentials run custom-cred:...`), pass --proxy-auth or set
GTM_AUTH_VIA_PROXY=1 and the client sends no header. The key is never printed.

Usage:
  gtm_mcp.py toolsets
  gtm_mcp.py tools linkedin.messaging [--verbose]
  gtm_mcp.py read search_linkedin_account_smart_limits --args '{"filter": {...}}'
  gtm_mcp.py execute --ledger ledger/2026-11-10.json --item 20261110-003

Exit codes: 0 ok, 1 failure, 2 refused by this client, 3 stopped (limit, block, checkpoint),
4 send outcome uncertain (check before anything else, never resend under a new key).
"""
import argparse
import itertools
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import batch_ledger as bl  # noqa: E402

DEFAULT_ENDPOINT = "https://mcp.gtm-api.com/mcp"
TIMEOUT = 120
EXIT_OK, EXIT_FAIL, EXIT_REFUSED, EXIT_STOPPED, EXIT_UNCERTAIN = 0, 1, 2, 3, 4


class Refused(Exception):
    """This client won't make the call. Nothing was sent."""


class CallResult:
    def __init__(self, ok, data=None, error=None, text="", raw=None):
        self.ok, self.data, self.error, self.text, self.raw = ok, data, error, text, raw

    @property
    def is_preview(self):
        return bool(self.ok and isinstance(self.data, dict) and self.data.get("preview") is True
                    and self.data.get("commit_token"))

    @property
    def code(self):
        return (self.error or {}).get("code")

    @property
    def context(self):
        return (self.error or {}).get("context") or {}


def _parse_body(body, content_type=""):
    """JSON or a text/event-stream body; returns the JSON-RPC message carrying a result or error."""
    body = body.strip()
    if "event-stream" in content_type or body.startswith("event:") or body.startswith("data:"):
        last = None
        for line in body.splitlines():
            if line.startswith("data:"):
                chunk = line[5:].strip()
                if chunk:
                    msg = json.loads(chunk)
                    if "result" in msg or "error" in msg:
                        last = msg
        if last is None:
            raise ValueError("event stream carried no JSON-RPC result")
        return last
    return json.loads(body)


def urllib_transport(endpoint, payload, headers, timeout=TIMEOUT):
    req = urllib.request.Request(endpoint, data=json.dumps(payload).encode("utf-8"),
                                 headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status, resp.headers.get("Content-Type", ""), resp.read().decode("utf-8")
    except urllib.error.HTTPError as e:
        return e.code, e.headers.get("Content-Type", "") if e.headers else "", e.read().decode("utf-8", "replace")


def curl_transport(endpoint, payload, headers, timeout=TIMEOUT):
    """POST through curl. Used when HTTPS_PROXY is an https:// proxy, which urllib cannot tunnel
    through (it speaks plain HTTP to the proxy and hangs). Headers go through a 0600 temp file so
    an Authorization header never shows up in the process list."""
    import subprocess
    import tempfile
    fd, hpath = tempfile.mkstemp(prefix="gtm-h-")
    try:
        with os.fdopen(fd, "w") as f:
            for k, v in headers.items():
                f.write(f"{k}: {v}\n")
        cmd = ["curl", "-sS", "-m", str(int(timeout)), "-X", "POST", endpoint,
               "-H", f"@{hpath}", "--data-binary", "@-",
               "-w", "\n%{http_code} %{content_type}", "-o", "-"]
        out = subprocess.run(cmd, input=json.dumps(payload).encode("utf-8"),
                             capture_output=True, timeout=timeout + 10)
    finally:
        os.unlink(hpath)
    if out.returncode != 0:
        raise urllib.error.URLError(f"curl exit {out.returncode}: {out.stderr.decode('utf-8', 'replace')[:200]}")
    text = out.stdout.decode("utf-8", "replace")
    body, _, tail = text.rpartition("\n")
    code, _, ctype = tail.partition(" ")
    return int(code), ctype, body


def default_transport():
    """urllib unless the environment routes HTTPS through an https:// proxy (the Perplexity
    credential proxy does), in which case curl, which can speak TLS to the proxy."""
    proxy = os.environ.get("HTTPS_PROXY") or os.environ.get("https_proxy") or ""
    import shutil
    if proxy.lower().startswith("https://") and shutil.which("curl"):
        return curl_transport
    return urllib_transport


def load_policy():
    return json.loads((HERE / "tool_policy.json").read_text(encoding="utf-8"))


def classify(name, policy=None):
    """'read', 'gated' or 'refused'."""
    policy = policy or load_policy()
    if name in policy["never"]:
        return "refused"
    if name in policy["read_tools"]:
        return "read"
    if name in {k["tool"] for k in policy["gated_kinds"].values()}:
        return "gated"
    return "refused"


class GtmClient:
    def __init__(self, endpoint=None, api_key=None, proxy_auth=None, transport=None, policy=None):
        self.endpoint = endpoint or os.environ.get("GTM_MCP_URL") or DEFAULT_ENDPOINT
        self.api_key = api_key if api_key is not None else os.environ.get("GTM_API_KEY")
        if proxy_auth is None:
            proxy_auth = os.environ.get("GTM_AUTH_VIA_PROXY") == "1"
        self.proxy_auth = proxy_auth
        self.transport = transport or default_transport()
        self.policy = policy or load_policy()
        self._ids = itertools.count(1)
        if not self.api_key and not self.proxy_auth:
            raise Refused("no credential: set GTM_API_KEY, or run under a proxy that injects auth "
                          "and pass --proxy-auth (see references/connection.md)")

    def _headers(self):
        h = {"Content-Type": "application/json", "Accept": "application/json, text/event-stream"}
        if self.api_key and not self.proxy_auth:
            h["Authorization"] = f"Bearer {self.api_key}"
        return h

    def rpc(self, method, params=None):
        payload = {"jsonrpc": "2.0", "id": next(self._ids), "method": method}
        if params is not None:
            payload["params"] = params
        status, ctype, body = self.transport(self.endpoint, payload, self._headers())
        if status == 401:
            return {"error": {"code": "unauthorized", "message": "the server rejected the credential (401)"}}
        if status >= 400 and not body.strip().startswith(("{", "data:", "event:")):
            return {"error": {"code": f"http_{status}", "message": body[:300]}}
        return _parse_body(body, ctype)

    def _meta_call(self, tool, arguments):
        msg = self.rpc("tools/call", {"name": tool, "arguments": arguments})
        return self._result(msg)

    @staticmethod
    def _result(msg):
        if "error" in msg and "result" not in msg:
            err = msg["error"]
            return CallResult(False, error={"code": err.get("code"), "message": err.get("message")}, raw=msg)
        res = msg.get("result") or {}
        text = "".join(c.get("text", "") for c in res.get("content", []) if c.get("type") == "text")
        data = res.get("structuredContent")
        if data is None:
            try:
                data = json.loads(text) if text.strip() else None
            except ValueError:
                data = None
        if res.get("isError") or (isinstance(data, dict) and data.get("success") is False):
            err = (data or {}).get("error") if isinstance(data, dict) else None
            err = err or {"code": "tool_error", "message": text[:500]}
            return CallResult(False, data=data, error=err, text=text, raw=msg)
        return CallResult(True, data=data, text=text, raw=msg)

    # -- the three meta-tools -------------------------------------------------------------------
    def list_toolsets(self):
        return self._meta_call("list_toolsets", {})

    def toolset_tools(self, toolset, verbose=False):
        return self._meta_call("get_toolset_tools", {"toolset": toolset, "verbose": bool(verbose)})

    def call_tool(self, name, arguments):
        """Raw call. Use read() or execute_item(); this is the one place a call leaves."""
        return self._meta_call("call_tool", {"name": name, "arguments": arguments})

    # -- guarded entry points -------------------------------------------------------------------
    def read(self, name, arguments=None):
        kind = classify(name, self.policy)
        if kind != "read":
            raise Refused(f"{name} is not a read tool ({kind}); outward tools run only through "
                          "`execute` for an approved batch item")
        if arguments and "commit_token" in arguments:
            raise Refused("a read takes no commit_token")
        return self.call_tool(name, arguments or {})


def interpret_error(res):
    """Map a failed call to a ledger outcome. Never suggests a retry loop."""
    code = (res.code or "").lower()
    ctx = res.context
    msg = ((res.error or {}).get("message") or res.text or "").lower()
    send_outcome = ctx.get("send_outcome")
    if any(w in msg or w in code for w in ("checkpoint", "login_issue", "challenge", "captcha")) \
            or ctx.get("reason") == "login_issue":
        return "checkpoint"
    if code in ("rate_limited", "limit_exceeded") or ctx.get("reason") == "bucket_saturated":
        return "quota_hit" if ctx.get("cause") == "linkedin_quota_hit" else "rate_limited"
    if code == "target_blocked" or "target_blocked" in msg:
        return "blocked"
    if code == "unauthorized":
        return "checkpoint"  # no credential means no outward work today; same stop-all
    if send_outcome in ("unknown", "in_flight", "sent"):
        return "uncertain"
    return "failed"


def _strip(args):
    return {k: v for k, v in (args or {}).items() if k not in ("commit_token", "_meta")}


def execute_item(client, ledger_path, item_id):
    """Preview, check, confirm, record. Returns (exit_code, report dict)."""
    ledger = bl.load(ledger_path)
    try:
        item = bl.verify_for_execution(ledger, item_id)
    except bl.LedgerError as e:
        raise Refused(str(e))
    if classify(item["tool"], client.policy) != "gated":
        raise Refused(f"{item['tool']} is not an outward tool this plugin runs")
    args = dict(item["args"])

    def finish(outcome, code, **details):
        bl.record_execution(ledger, item_id, outcome, **details)
        bl.save(ledger, ledger_path)
        return code, dict(details, item=item_id, tool=item["tool"], outcome=outcome)

    preview = client.call_tool(item["tool"], args)
    if not preview.ok:
        outcome = interpret_error(preview)
        if outcome == "uncertain":
            outcome = "failed"  # nothing can have been sent by a preview
        return finish(outcome, EXIT_STOPPED if outcome in ("rate_limited", "quota_hit", "blocked", "checkpoint") else EXIT_FAIL,
                      stage="preview", error_code=preview.code,
                      retry_after=preview.context.get("retry_after"),
                      message=((preview.error or {}).get("message") or "")[:300])
    if not preview.is_preview:
        # A dangerous tool that answers without a preview means the server's gate is off. We
        # can't take the send back; record it loudly so a person looks.
        return finish("uncertain", EXIT_UNCERTAIN, stage="preview",
                      message="the server answered without a preview; treat as possibly sent and check")
    shown = _strip(preview.data.get("arguments"))
    if shown and shown != _strip(args):
        return finish("failed", EXIT_FAIL, stage="preview",
                      message="the preview names different arguments from the approved item; not confirmed")
    confirm = client.call_tool(item["tool"], dict(args, commit_token=preview.data["commit_token"]))
    if confirm.ok:
        data = confirm.data or {}
        ref = None
        if isinstance(data, dict):
            res = data.get("result") or data.get("item") or data
            if isinstance(res, dict):
                ref = {k: res[k] for k in ("sid", "urn", "url", "comment_urn", "reaction_urn",
                                           "activity_urn", "post_urn") if k in res}
        return finish("executed", EXIT_OK, stage="confirm", validated=preview.data.get("validated"),
                      result_ref=ref or None, pacing=(data.get("pacing") if isinstance(data, dict) else None))
    outcome = interpret_error(confirm)
    code = {"uncertain": EXIT_UNCERTAIN, "failed": EXIT_FAIL}.get(outcome, EXIT_STOPPED)
    return finish(outcome, code, stage="confirm", error_code=confirm.code,
                  send_outcome=confirm.context.get("send_outcome"),
                  activity_log_sid=confirm.context.get("activity_log_sid"),
                  retry_after=confirm.context.get("retry_after"),
                  message=((confirm.error or {}).get("message") or "")[:300])


def _json_arg(value):
    if not value:
        return {}
    if value.startswith("@"):
        return json.loads(Path(value[1:]).read_text(encoding="utf-8"))
    return json.loads(value)


def _emit(obj):
    print(json.dumps(obj, indent=2, ensure_ascii=False, default=str))


def main(argv=None, transport=None):
    ap = argparse.ArgumentParser(description="Refusing GTM API MCP client for linkedin-gtm")
    ap.add_argument("--endpoint")
    ap.add_argument("--proxy-auth", action="store_true", help="a proxy injects auth; send no header")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("toolsets")
    p = sub.add_parser("tools"); p.add_argument("toolset"); p.add_argument("--verbose", action="store_true")
    p = sub.add_parser("read"); p.add_argument("tool"); p.add_argument("--args")
    p = sub.add_parser("execute"); p.add_argument("--ledger", required=True); p.add_argument("--item", required=True)
    p = sub.add_parser("classify"); p.add_argument("tool")
    a = ap.parse_args(argv)

    if a.cmd == "classify":
        print(classify(a.tool))
        return EXIT_OK
    try:
        client = GtmClient(endpoint=a.endpoint, proxy_auth=a.proxy_auth or None, transport=transport)
        if a.cmd == "toolsets":
            r = client.list_toolsets()
        elif a.cmd == "tools":
            r = client.toolset_tools(a.toolset, a.verbose)
        elif a.cmd == "read":
            r = client.read(a.tool, _json_arg(a.args))
        else:
            code, report = execute_item(client, a.ledger, a.item)
            _emit(report)
            return code
    except Refused as e:
        print(f"refused: {e}", file=sys.stderr)
        return EXIT_REFUSED
    if r.ok:
        _emit(r.data if r.data is not None else r.text)
        return EXIT_OK
    outcome = interpret_error(r)
    _emit({"error": r.error, "outcome": outcome,
           "note": "reported, not retried" if outcome != "failed" else None})
    return EXIT_STOPPED if outcome in ("rate_limited", "quota_hit", "blocked", "checkpoint") else EXIT_FAIL


if __name__ == "__main__":
    sys.exit(main())
