#!/usr/bin/env python3
"""Read a repo and write its capability map: what the MCP server and REST
gateway can actually do today.

Read-only. Static extraction driven by a product profile, so it works on any
repo whose MCP registrations and route files can be described by a pattern.
It does not run the server; `export` can later diff this map against a live
`tools/list` when a token is available.

    python inventory.py --repo ~/GitHub/stigviewer --profile profiles/stigviewer.json \
        --out <bank_dir>/capability-map.json [--commit <sha>]
"""

from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import demandlib as dl  # noqa: E402

HTTP_METHODS = ("GET", "POST", "PUT", "PATCH", "DELETE")
_METHOD_RX = re.compile(r"^export\s+(?:async\s+function|const)\s+(GET|POST|PUT|PATCH|DELETE)\b", re.M)


def _read(path: str) -> str:
    with open(path, "r", encoding="utf-8") as fh:
        return fh.read()


def _git_commit(repo: str) -> str | None:
    try:
        out = subprocess.run(["git", "-C", repo, "rev-parse", "HEAD"], capture_output=True, text=True, timeout=10)
        return out.stdout.strip() or None if out.returncode == 0 else None
    except (OSError, subprocess.SubprocessError):
        return None


def _first_string(block: str, key: str) -> str | None:
    m = re.search(key + r"\s*:\s*'((?:[^'\\]|\\.)*)'", block)
    if m:
        return m.group(1).replace("\\'", "'")
    m = re.search(key + r"\s*:\s*\[\s*\n?\s*'((?:[^'\\]|\\.)*)'", block)
    if m:
        return m.group(1).replace("\\'", "'")
    m = re.search(key + r'\s*:\s*"((?:[^"\\]|\\.)*)"', block)
    return m.group(1) if m else None


def _input_keys(block: str) -> list[str]:
    m = re.search(r"inputSchema\s*:\s*z\.object\(\{", block)
    if not m:
        return []
    # Walk to the matching close brace of the object literal.
    i = m.end()
    depth = 1
    start = i
    while i < len(block) and depth:
        ch = block[i]
        if ch in "{([":
            depth += 1
        elif ch in "})]":
            depth -= 1
        i += 1
    body = block[start : i - 1]
    keys = []
    depth = 0
    for line in body.splitlines():
        if depth == 0:
            km = re.match(r"\s*([A-Za-z_][A-Za-z0-9_]*)\s*:", line)
            if km:
                keys.append(km.group(1))
            elif re.match(r"\s*\.\.\.([A-Z_]+)", line):
                keys.append(re.match(r"\s*\.\.\.([A-Z_]+)", line).group(1))
        depth += line.count("(") + line.count("{") + line.count("[") - line.count(")") - line.count("}") - line.count("]")
        depth = max(depth, 0)
    return keys


def _norm_path(path: str) -> str:
    """Route templates from either side reduced to a comparable shape."""
    p = re.sub(r"\$\{[^}]+\}", "{}", path)
    p = re.sub(r"\[[^\]]+\]", "{}", p)
    p = re.sub(r"\{[^}]*\}", "{}", p)
    return p.rstrip("/")


def _endpoints_in(block: str, functions: dict[str, str]) -> list[dict]:
    """Every `/api/...` path a tool block calls, with the HTTP method its helper uses.

    Handles string literals, template literals, and a bare identifier bound
    earlier in the same block (`const base = `/api/v1/nodes/${c}/${id}``).
    """
    consts = {m.group(1): m.group(2) for m in re.finditer(r"const\s+([A-Za-z_]\w*)\s*=\s*[`']([^`']*/api/[^`']*)[`']", block)}
    found: dict[str, str] = {}
    for fn, method in functions.items():
        rx = re.compile(re.escape(fn) + r"\(\s*ctx\s*,\s*(?:'([^']+)'|`([^`]+)`|([A-Za-z_]\w*)\s*[,)])")
        for m in rx.finditer(block):
            path = m.group(1) or m.group(2) or consts.get(m.group(3) or "", "")
            if not path:
                continue
            for name, val in consts.items():
                path = path.replace("${" + name + "}", val)
            found[path] = method
    return [{"method": found[p], "path": p} for p in sorted(found)]


def extract_tools(repo: str, mcp: dict) -> list[dict]:
    tools: list[dict] = []
    reg_rx = [re.compile(p) for p in mcp.get("register_patterns", [])]
    functions = mcp.get("endpoint_call_functions", {})
    for rel in mcp.get("tools_files", []):
        text = _read(os.path.join(repo, rel))
        hits = sorted({(m.start(), m.group(1)) for rx in reg_rx for m in rx.finditer(text)})
        for idx, (pos, name) in enumerate(hits):
            end = hits[idx + 1][0] if idx + 1 < len(hits) else len(text)
            block = text[pos:end]
            tools.append(
                {
                    "name": name,
                    "title": _first_string(block, "title"),
                    "summary": _first_string(block, "description"),
                    "input_keys": _input_keys(block),
                    "read_only": "READ_ONLY" in block or "readOnlyHint: true" in block,
                    "endpoints": _endpoints_in(block, functions),
                    "defined_in": f"{rel}:{text.count(chr(10), 0, pos) + 1}",
                }
            )
    return tools


def extract_prompts(repo: str, mcp: dict) -> list[dict]:
    out = []
    rx = re.compile(r"registerPrompt\(\s*'([a-z0-9_\-]+)'")
    for rel in mcp.get("prompts_files", []):
        path = os.path.join(repo, rel)
        if not os.path.exists(path):
            continue
        text = _read(path)
        for m in rx.finditer(text):
            block = text[m.start() : m.start() + 1500]
            out.append({"name": m.group(1), "title": _first_string(block, "title"), "defined_in": f"{rel}:{text.count(chr(10), 0, m.start()) + 1}"})
    return out


def extract_routes(repo: str, rest: dict) -> list[dict]:
    routes = []
    prefix = rest.get("url_prefix", "")
    for root in rest.get("route_roots", []):
        base = os.path.join(repo, root)
        for dirpath, _dirs, files in os.walk(base):
            if "route.ts" not in files:
                continue
            rel_dir = os.path.relpath(dirpath, base)
            path = prefix + ("" if rel_dir == "." else "/" + rel_dir.replace(os.sep, "/"))
            text = _read(os.path.join(dirpath, "route.ts"))
            methods = sorted(set(_METHOD_RX.findall(text)), key=HTTP_METHODS.index)
            routes.append(
                {
                    "path": re.sub(r"\[([^\]]+)\]", r"{\1}", path),
                    "methods": methods,
                    "auth": "withApiAuth" in text,
                    "defined_in": os.path.relpath(os.path.join(dirpath, "route.ts"), repo),
                }
            )
    return sorted(routes, key=lambda r: r["path"])


def build_map(repo: str, profile: dict, commit: str | None) -> dict:
    mcp = profile.get("mcp", {})
    rest = profile.get("rest", {})
    tools = extract_tools(repo, mcp)
    prompts = extract_prompts(repo, mcp)
    routes = extract_routes(repo, rest)

    by_norm: dict[str, list[str]] = {}
    for t in tools:
        for ep in t["endpoints"]:
            by_norm.setdefault(_norm_path(ep["path"]), []).append(t["name"])
    for r in routes:
        r["reached_by_tools"] = sorted(set(by_norm.get(_norm_path(r["path"]), [])))

    unmatched = sorted({ep["path"] for t in tools for ep in t["endpoints"] if _norm_path(ep["path"]) not in {_norm_path(r["path"]) for r in routes}})
    return {
        "product": profile.get("product"),
        "generated_by": f"{dl.PLUGIN_NAME} {dl.PLUGIN_VERSION}",
        "source": {"repo": profile.get("repo_hint") or os.path.basename(os.path.abspath(repo)), "commit": commit or _git_commit(repo)},
        "mcp": {
            "server_name": mcp.get("server_name"),
            "tool_names": [t["name"] for t in tools],
            "tools": tools,
            "prompts": prompts,
        },
        "rest": {
            "routes": routes,
            "rest_only_routes": [r["path"] for r in routes if not r["reached_by_tools"]],
            "tool_endpoints_without_route": unmatched,
        },
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--repo", required=True)
    ap.add_argument("--profile", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--commit", help="Commit the repo snapshot was taken at, when it is not a git checkout")
    a = ap.parse_args(argv)

    profile = dl.load_profile(a.profile)
    cmap = build_map(a.repo, profile, a.commit)
    if not cmap["mcp"]["tools"]:
        print("ERROR no MCP tools found; check mcp.tools_files and mcp.register_patterns in the profile", file=sys.stderr)
        return 2
    dl.dump_json(cmap, a.out)
    r = cmap["rest"]
    print(f"tools={len(cmap['mcp']['tools'])} prompts={len(cmap['mcp']['prompts'])} routes={len(r['routes'])} rest_only={len(r['rest_only_routes'])}")
    if r["tool_endpoints_without_route"]:
        print("WARNING tool endpoints with no matching route file: " + ", ".join(r["tool_endpoints_without_route"]))
    print(f"wrote {a.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
