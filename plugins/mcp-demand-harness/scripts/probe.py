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
import subprocess
import hashlib
from pathlib import Path
import probe_checks as pc
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
            item["checks"] = {k: p[k] for k in ("must_contain", "must_not_match", "absence_acceptable", "json_any_of") if k in p}
        if calls:
            item["rest_calls"] = calls
            item["rest_checks"] = {k: q["rest"][k] for k in ("must_contain", "must_not_match", "absence_acceptable", "json_any_of") if k in q["rest"]}
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
    empty = not text.strip()
    try:empty = empty or json.loads(text) in (None, {}, [], "")
    except ValueError:pass
    if empty:
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
        self.server_info = None
        self.last_rpc_text = None

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
        self.last_rpc_text = text
        self.session = self.session or headers.get("mcp-session-id") or headers.get("Mcp-Session-Id")
        return status, text

    def initialize(self) -> int:
        """Same handshake verify-eval.ts does, so stateful servers accept the calls."""
        status, text = self._rpc("initialize", {"protocolVersion": "2025-06-18", "capabilities": {}, "clientInfo": {"name": dl.PLUGIN_NAME + "-probe", "version": dl.PLUGIN_VERSION}})
        result = pc.decode_rpc(text, self._id)
        if '_probe_error' in result: return 502
        info=result.get('serverInfo')
        self.server_info = {k:str(info[k])[:512] for k in ('name','version') if k in info} if isinstance(info,dict) else None
        if 200 <= status < 300:
            self._rpc("notifications/initialized", None, notify=True)
        return status

    def tools_call(self, tool: str, arguments: dict):
        status, text = self._rpc("tools/call", {"name": tool, "arguments": arguments})
        return status, pc.decode_rpc(text, self._id)

    def rest(self, call: dict):
        url = self.rest_base + call["path"]
        if call.get("query"):
            url += "?" + urllib.parse.urlencode(call["query"], doseq=True)
        status, _h, text = self._req(call.get("method", "GET"), url, call.get("body"))
        return status, text


def revision(path):
    r=subprocess.run(['git','-C',str(path),'rev-parse','HEAD'],capture_output=True,text=True)
    return r.stdout.strip() if r.returncode==0 else None


def layer_record(kind,status,checks,response,contract,token):
    strength='structured' if contract.get('json_any_of') else ('content' if contract.get('must_contain') else ('negative_only' if contract.get('must_not_match') else 'liveness'))
    safe_checks=json.loads(pc.receipt(checks,[token],limit=262144)['sanitized_text'])
    return {'layer':kind,'http_status':status,'checks':safe_checks,
            'passed':all(c['passed'] for c in checks),'assertion_strength':strength,
            'response_evidence':pc.receipt(response,[token])}


def run(a) -> int:
    plan_raw=Path(a.plan).read_bytes();profile_raw=Path(a.profile).read_bytes()
    plan=json.loads(plan_raw);profile=json.loads(profile_raw)
    plan_hash='sha256:'+hashlib.sha256(plan_raw).hexdigest();profile_hash='sha256:'+hashlib.sha256(profile_raw).hexdigest()
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
    selected = [i for i in plan['items'] if not a.only or i['bank_id'] in a.only]
    if os.path.lexists(a.out) or a.only == [] or not selected or any(not i.get('mcp_call') and not i.get('rest_calls') for i in selected):
        print('REFUSED existing output or empty executable selection; choose a new output path',file=sys.stderr)
        return 3
    try:
        for item in selected:
            for key in ('checks','rest_checks'):
                if 'json_any_of' in item.get(key,{}):pc.validate_contract(item[key]['json_any_of'])
    except ValueError as e:
        print('REFUSED '+str(e),file=sys.stderr);return 3
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
    source_hashes={n:dl.sha256_file(Path(__file__).with_name(n)) for n in ('probe.py','probe_checks.py','demandlib.py')}
    revisions={'harness':revision(Path(__file__).parent),'working_repo':revision(Path.cwd())}

    if any(i.get("mcp_call") for i in selected):
        st = client.initialize()
        if not 200 <= st < 300:
            print(f"ERROR MCP initialize returned HTTP {st} from {target['mcp_url']}", file=sys.stderr)
            return 2

    results = []
    for item in selected:
        r = {"bank_id": item["bank_id"], "layers": []}
        if item.get("mcp_call"):
            status, result = client.tools_call(item["mcp_call"]["tool"], item["mcp_call"]["arguments"])
            checks = pc.transport_checks(status,result)
            data = pc.payload(result)
            if pc.application_error(result,item['checks']):
                checks.append({'check':'no application error payload or unapproved failure envelope','passed':False,'detail':''})
            checks += grade(flatten(result), item['checks'], markers)
            if 'json_any_of' in item['checks']:checks.append(pc.structured_check(data,item['checks']['json_any_of']))
            r['layers'].append(layer_record('mcp_payload',status,checks,client.last_rpc_text,item['checks'],token))
        for call in item.get("rest_calls") or []:
            status, text = client.rest(call)
            rc = item.get("rest_checks", {})
            checks = grade(text, rc, markers)
            ok = 200 <= status < 300 or (status == 404 and rc.get("absence_acceptable") and any(m in text for m in markers))
            checks.insert(0, {"check": f"HTTP {call.get('method', 'GET')} {call['path']}", "passed": bool(ok), "detail": str(status)})
            checks.append({'check':'nonempty JSON body without application error','passed':pc.body_ok(text),'detail':''})
            if 'json_any_of' in rc:
                try:data=json.loads(text)
                except ValueError:data=None
                checks.append(pc.structured_check(data,rc['json_any_of']))
            r['layers'].append(layer_record('rest',status,checks,text,rc,token))
        r["passed"] = all(layer["passed"] for layer in r["layers"])
        results.append(r)
        print(f"{'PASS' if r['passed'] else 'FAIL'} {item['bank_id']}")

    out = {
        "tool": "probe",
        "plan_hash": plan_hash,
        "bank_hash": plan.get('bank_hash'),
        "bank_hash_source": "plan_declaration",
        "harness_source_hashes": source_hashes,
        "profile_hash": profile_hash,
        "server_info": json.loads(pc.receipt(client.server_info,[token],limit=16384)['sanitized_text']) if client.server_info is not None else None,
        "client_revisions": revisions,
        "target": a.target,
        "approved_by": a.approver,
        "ran_at": _dt.datetime.now(_dt.timezone.utc).isoformat(timespec="seconds"),
        "results": results,
    }
    Path(a.out).parent.mkdir(parents=True,exist_ok=True)
    try:
        with open(a.out,'x') as f:json.dump(out,f,indent=2);f.write('\n')
    except FileExistsError:
        print('REFUSED output appeared during run; baseline preserved',file=sys.stderr);return 3
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
