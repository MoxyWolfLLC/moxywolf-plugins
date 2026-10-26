#!/usr/bin/env python3
"""Payload and REST probes: the deterministic layer under the model harnesses.

    probe.py plan --bank B --capability-map M --out <dir>/<product>-probe-plan.json
    probe.py run  --plan PLAN --profile P --target staging --out results.json
                  [--approver "Full Name"]   # required for any target marked requires_named_approval

`plan` is pure: it lists, per question, the direct MCP `tools/call` to make
(from `payload`), any explicit REST calls (from `rest.calls`), and which
/api routes that question exercises according to the capability map.

`run` makes real HTTP requests with the token named in the profile. It is the
only step in this plugin that sends traffic, so it refuses production-marked
targets without a named approver and records who approved what.

Grading mirrors the in-repo harness (verify-eval.ts layer 1): a needle that
is missing is excused only when absence is acceptable AND the payload explains
itself (profile.explained_markers), never for a bare empty result.
"""

from __future__ import annotations

import argparse
import datetime as _dt
import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import demandlib as dl  # noqa: E402

DEFAULT_EXPLAINED = ['"absence"', '"refused"', '"denial"', '"inputRequired"', '"limits"']


# --------------------------------------------------------------------- plan


def build_plan(bank: dict, cmap: dict, include_drafts: bool = False) -> dict:
    endpoints = {t["name"]: t["endpoints"] for t in cmap["mcp"]["tools"]}
    items = []
    for q in dl.active_questions(bank):
        ok, why = dl.runnable(q, include_drafts=include_drafts)
        if not ok:
            continue
        p = q.get("payload")
        calls = (q.get("rest") or {}).get("calls") or []
        if not p and not calls:
            continue
        item = {"bank_id": q["id"], "text": q["text"], "checks": {}}
        if p:
            item["mcp_call"] = {"tool": p["tool"], "arguments": p.get("args", {})}
            item["exercises_routes"] = [f"{e['method']} {e['path']}" for e in endpoints.get(p["tool"], [])]
            item["checks"] = {k: p[k] for k in ("must_contain", "must_not_match", "absence_acceptable") if k in p}
        if calls:
            item["rest_calls"] = calls
            item["rest_checks"] = {k: q["rest"][k] for k in ("must_contain", "must_not_match", "absence_acceptable") if k in q["rest"]}
        if q.get("review_status") == "draft":
            item["draft"] = True
        items.append(item)
    return {"generated_by": f"{dl.PLUGIN_NAME} {dl.PLUGIN_VERSION}", "bank_hash": None, "items": items}


# ---------------------------------------------------------------------- run


def flatten(result) -> str:
    if not result:
        return ""
    parts = [json.dumps(result)]
    for block in (result.get("content") or []) if isinstance(result, dict) else []:
        if isinstance(block, dict) and block.get("text"):
            parts.append(block["text"])
    return "\n".join(parts)


def grade(text: str, checks: dict, explained_markers: list[str]) -> list[dict]:
    out = []
    if not text:
        return [{"check": "returns something", "passed": False, "detail": "empty result"}]
    explained = any(m in text for m in explained_markers)
    for needle in checks.get("must_contain") or []:
        found = needle.lower() in text.lower()
        excused = bool(checks.get("absence_acceptable")) and explained
        out.append({"check": f"contains {needle!r}", "passed": found or excused, "detail": "excused: explained absence" if (not found and excused) else ""})
    for entry in checks.get("must_not_match") or []:
        pat, cs = dl.pattern_parts(entry)
        hit = re.search(pat, text, 0 if cs else re.I)
        out.append({"check": f"does not match /{pat}/", "passed": hit is None, "detail": hit.group(0)[:80] if hit else ""})
    if not out:
        out.append({"check": "returns something", "passed": True, "detail": ""})
    return out


class Client:
    def __init__(self, mcp_url: str, rest_base: str, header: str, value: str, timeout: float = 60):
        self.mcp_url, self.rest_base = mcp_url, rest_base.rstrip("/")
        self.header, self.value, self.timeout = header, value, timeout
        self.session: str | None = None
        self._id = 0

    def _req(self, method: str, url: str, body: dict | None, extra: dict | None = None):
        headers = {"Content-Type": "application/json", "Accept": "application/json, text/event-stream", "User-Agent": "mcp-demand-harness/0.1 (+eval)"}
        if self.header:
            headers[self.header] = self.value
        headers.update(extra or {})
        data = json.dumps(body).encode() if body is not None else None
        req = urllib.request.Request(url, data=data, method=method, headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as res:
                return res.status, dict(res.headers), res.read().decode("utf-8", "replace")
        except urllib.error.HTTPError as e:
            return e.code, dict(e.headers or {}), e.read().decode("utf-8", "replace")

    def _rpc(self, method: str, params: dict | None, notify: bool = False):
        extra = {"mcp-session-id": self.session} if self.session else {}
        body = {"jsonrpc": "2.0", "method": method, **({"params": params} if params is not None else {})}
        if not notify:
            self._id += 1
            body["id"] = self._id
        status, headers, text = self._req("POST", self.mcp_url, body, extra)
        self.session = self.session or headers.get("mcp-session-id") or headers.get("Mcp-Session-Id")
        return status, text

    def initialize(self) -> int:
        """Same handshake verify-eval.ts does, so stateful servers accept the calls."""
        status, _ = self._rpc("initialize", {"protocolVersion": "2025-06-18", "capabilities": {}, "clientInfo": {"name": dl.PLUGIN_NAME + "-probe", "version": dl.PLUGIN_VERSION}})
        if 200 <= status < 300:
            self._rpc("notifications/initialized", None, notify=True)
        return status

    def tools_call(self, tool: str, arguments: dict):
        status, text = self._rpc("tools/call", {"name": tool, "arguments": arguments})
        line = next((ln for ln in text.split("\n") if ln.startswith("data: ")), None)
        try:
            return status, json.loads(line[6:] if line else text).get("result")
        except (ValueError, AttributeError):
            return status, None

    def rest(self, call: dict):
        url = self.rest_base + call["path"]
        if call.get("query"):
            url += "?" + urllib.parse.urlencode(call["query"], doseq=True)
        status, _h, text = self._req(call.get("method", "GET"), url, call.get("body"))
        return status, text


def run(a) -> int:
    plan = dl.load_json(a.plan)
    profile = dl.load_profile(a.profile)
    target = (profile.get("targets") or {}).get(a.target)
    if not target:
        print(f"ERROR profile has no target {a.target!r}", file=sys.stderr)
        return 2
    if target.get("requires_named_approval") and not dl.named_person(a.approver):
        print(f"REFUSED target {a.target} requires --approver with the name of the person who approved sending eval traffic to it", file=sys.stderr)
        return 3
    if target.get("requires_named_approval") and any(i.get("draft") for i in plan["items"]):
        print(f"REFUSED the plan includes draft questions; drafts run on staging only, never on {a.target}", file=sys.stderr)
        return 3
    auth = profile.get("auth") or {}
    token = os.environ.get(auth.get("token_env", "API_TOKEN"), "")
    if a.proxy_auth:
        # A credential proxy (HTTPS_PROXY) adds the header, so the token never enters this process.
        client = Client(target["mcp_url"], target["rest_base"], "", "")
    elif not token:
        print(f"ERROR set {auth.get('token_env')} to a test-org API token", file=sys.stderr)
        return 2
    else:
        client = Client(target["mcp_url"], target["rest_base"], auth.get("header", "Authorization"), f"{auth.get('scheme', 'Bearer')} {token}".strip())
    markers = profile.get("explained_markers") or DEFAULT_EXPLAINED

    if any(i.get("mcp_call") for i in plan["items"]):
        st = client.initialize()
        if not 200 <= st < 300:
            print(f"ERROR MCP initialize returned HTTP {st} from {target['mcp_url']}", file=sys.stderr)
            return 2

    results = []
    for item in plan["items"]:
        if a.only and item["bank_id"] not in a.only:
            continue
        r = {"bank_id": item["bank_id"], "layers": []}
        if item.get("mcp_call"):
            status, result = client.tools_call(item["mcp_call"]["tool"], item["mcp_call"]["arguments"])
            checks = grade(flatten(result), item["checks"], markers)
            r["layers"].append({"layer": "mcp_payload", "http_status": status, "checks": checks, "passed": all(c["passed"] for c in checks)})
        for call in item.get("rest_calls") or []:
            status, text = client.rest(call)
            rc = item.get("rest_checks", {})
            checks = grade(text, rc, markers)
            ok = 200 <= status < 300 or (status == 404 and rc.get("absence_acceptable") and any(m in text for m in markers))
            checks.insert(0, {"check": f"HTTP {call.get('method', 'GET')} {call['path']}", "passed": bool(ok), "detail": str(status)})
            r["layers"].append({"layer": "rest", "http_status": status, "checks": checks, "passed": all(c["passed"] for c in checks)})
        r["passed"] = all(layer["passed"] for layer in r["layers"])
        results.append(r)
        print(f"{'PASS' if r['passed'] else 'FAIL'} {item['bank_id']}")

    out = {
        "tool": "probe",
        "target": a.target,
        "approved_by": a.approver,
        "ran_at": _dt.datetime.now(_dt.timezone.utc).isoformat(timespec="seconds"),
        "results": results,
    }
    dl.dump_json(out, a.out)
    failed = sum(1 for r in results if not r["passed"])
    print(f"{len(results) - failed}/{len(results)} passed; wrote {a.out}")
    return 0 if not failed else 1


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("plan")
    p.add_argument("--bank", required=True)
    p.add_argument("--capability-map", required=True)
    p.add_argument("--out", required=True)
    p.add_argument("--include-drafts", action="store_true", help="plan draft questions too, to check them on staging during review")
    p = sub.add_parser("run")
    p.add_argument("--plan", required=True)
    p.add_argument("--profile", required=True)
    p.add_argument("--target", default="staging")
    p.add_argument("--approver")
    p.add_argument("--out", required=True)
    p.add_argument("--only", nargs="*")
    p.add_argument("--proxy-auth", action="store_true", help="auth is added by an HTTPS credential proxy; send no token header")
    a = ap.parse_args(argv)
    if a.cmd == "plan":
        bank = dl.load_json(a.bank)
        plan = build_plan(bank, dl.load_json(a.capability_map), include_drafts=a.include_drafts)
        plan["bank_hash"] = dl.sha256_file(a.bank)
        dl.dump_json(plan, a.out)
        print(f"items={len(plan['items'])} wrote {a.out}")
        return 0
    return run(a)


if __name__ == "__main__":
    sys.exit(main())
