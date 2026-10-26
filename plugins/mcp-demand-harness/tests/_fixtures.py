"""Shared fixtures for the mcp-demand-harness tests. Stdlib only.

A tiny fake product ("widgets") with three MCP tools, one prompt and five
REST routes, two of them reachable only over REST. Small enough to read in
one sitting, shaped like the real STIGViewer layout the profile describes.
"""
from __future__ import annotations

import copy
import json
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPTS = os.path.join(os.path.dirname(HERE), "scripts")
sys.path.insert(0, SCRIPTS)

import demandlib as dl  # noqa: E402

TOOLS_TS = """
import { z } from 'zod'
registerMeasuredTool(server, 'widgets_search', {
  title: 'Search widgets',
  description: 'Find widgets by phrase.',
  inputSchema: z.object({
    q: z.string(),
    limit: z.number().optional(),
  }),
  annotations: READ_ONLY,
}, async (args, ctx) => callApiV1(ctx, '/api/v1/search', { q: args.q }))

registerMeasuredTool(server, 'widgets_get', {
  title: 'Get one widget',
  description: 'Read a widget by id.',
  inputSchema: z.object({ id: z.string() }),
}, async (args, ctx) => {
  const base = `/api/v1/items/${args.id}`
  return callApiV1(ctx, base)
})

server.registerTool('widgets_plan', {
  title: 'Plan work',
  description: 'Plan work for findings.',
  inputSchema: z.object({
    findings: z.array(z.object({ id: z.string() })),
    output: z.enum(['roles', 'rasci']).optional(),
  }),
}, async (args, ctx) => postApiV1(ctx, '/api/v1/plan', args))
"""

PROMPTS_TS = """
server.registerPrompt('triage', { title: 'Triage a scan' }, async () => ({}))
"""

ROUTES = {
    "search": "export async function GET(req) { return withApiAuth(req) }\n",
    "items/[id]": "export async function GET(req) { return withApiAuth(req) }\n",
    "items/[id]/download": "export async function GET(req) { return withApiAuth(req) }\n",
    "plan": "export async function POST(req) { return withApiAuth(req) }\n",
    "batch": "export const POST = withApiAuth(async (req) => null)\n",
}

PROFILE = {
    "product": "widgets",
    "repo_hint": "Example/widgets",
    "bank_dir": "eval/demand",
    "mcp": {
        "server_name": "widgets",
        "tools_files": ["lib/mcp/tools.ts"],
        "prompts_files": ["lib/mcp/prompts.ts"],
        "register_patterns": [
            "registerMeasuredTool\\(\\s*server,\\s*'([a-z0-9_]+)'",
            "server\\.registerTool\\(\\s*'([a-z0-9_]+)'",
        ],
        "endpoint_call_functions": {"callApiV1": "GET", "postApiV1": "POST"},
    },
    "rest": {"route_roots": ["app/api/v1"], "url_prefix": "/api/v1"},
    "targets": {
        "staging": {"mcp_url": "http://127.0.0.1:9/api/mcp", "rest_base": "http://127.0.0.1:9"},
        "production": {"mcp_url": "https://widgets.example/api/mcp", "rest_base": "https://widgets.example", "requires_named_approval": True},
    },
    "auth": {"token_env": "WIDGETS_TOKEN", "header": "Authorization", "scheme": "Bearer"},
    "models": {"mcpjam": "anthropic/claude-sonnet-5", "mcp_eval_provider": "anthropic", "mcp_eval_model": "claude-sonnet-5"},
    "evidence_exclusions": {"org_names": ["Widgets Test Org"]},
    "explained_markers": ["not_held", "outside what"],
}


def make_repo(root: str) -> str:
    os.makedirs(os.path.join(root, "lib", "mcp"), exist_ok=True)
    with open(os.path.join(root, "lib", "mcp", "tools.ts"), "w") as fh:
        fh.write(TOOLS_TS)
    with open(os.path.join(root, "lib", "mcp", "prompts.ts"), "w") as fh:
        fh.write(PROMPTS_TS)
    for rel, body in ROUTES.items():
        d = os.path.join(root, "app", "api", "v1", *rel.split("/"))
        os.makedirs(d, exist_ok=True)
        with open(os.path.join(d, "route.ts"), "w") as fh:
            fh.write(body)
    return root


def write_json(obj, path: str) -> str:
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(obj, fh, indent=1)
    return path


def q(qid: str, **over) -> dict:
    """A valid accepted discovery question; override fields as needed."""
    base = {
        "id": qid,
        "text": f"Question {qid} about widgets?",
        "persona": "planner",
        "intent": "x",
        "mode": "discovery",
        "kind": "live",
        "surfaces": ["mcp"],
        "priority": 2,
        "status": "active",
        "review_status": "accepted",
        "evidence": {"class": "hypothesis", "source": "docs/personas.md"},
        "expect": {},
    }
    for k, v in over.items():
        if k == "evidence":
            base["evidence"] = {**base["evidence"], **v}
        else:
            base[k] = v
    return base


def bank() -> dict:
    return {
        "bank_version": dl.BANK_VERSION,
        "product": "widgets",
        "personas": [
            {"id": "planner", "name": "Planner", "source": "docs/personas.md"},
            {"id": "engineer", "name": "Engineer", "source": "docs/personas.md"},
        ],
        "questions": [
            q("Q-0001", text="What widgets do you hold for RHEL?"),
            q("Q-0002", text="Find the widget for rule V-1.", mode="strict", why="Engineers look rules up daily.",
              expect={"first_tool_any_of": ["widgets_search"]}),
            q("Q-0003", text="Show me widget 42 or search for it.", mode="strict", why="Either path is fine.",
              expect={"first_tool_any_of": ["widgets_search", "widgets_get"], "must_contain": ["widget"]}),
            q("Q-0004", text="Am I compliant?", mode="strict", kind="boundary", why="A verdict would be false.",
              expect={"must_refuse": True, "rubric": "Declines to give a verdict and offers coverage instead.",
                      "must_not_match": [r"\byou are compliant\b"]}),
            q("Q-0005", text="Plan roles for these findings.", mode="strict", why="Staffing.",
              expect={"first_tool_any_of": ["widgets_plan"]},
              payload={"tool": "widgets_plan", "args": {"findings": [{"id": "V-1"}], "output": "roles"}, "must_contain": ["roles"]}),
            q("Q-0006", text="Download widget 42 as JSON.", surfaces=["rest"],
              rest={"calls": [{"method": "GET", "path": "/api/v1/items/42/download"}], "must_contain": ["id"]}),
            q("Q-0007", text="Draft: batch fetch widgets.", review_status="draft", evidence={"authored_by": "claude (draft)"}),
            q("Q-0008", text="Triage my scan.", requires_input=["IN-1 scan export"]),
            q("Q-0009", text="Triage this scan: V-1 open, V-2 open.", evidence={"class": "generated", "parent": "Q-0008", "note": "synthetic"}),
        ],
    }


class Workspace:
    """A temp dir holding the fixture repo, profile, bank and capability map."""

    def __init__(self):
        self._td = tempfile.TemporaryDirectory()
        self.root = self._td.name
        self.repo = make_repo(os.path.join(self.root, "repo"))
        self.profile = write_json(PROFILE, os.path.join(self.root, "profile.json"))
        self.bank = write_json(bank(), os.path.join(self.root, "bank.json"))
        self.cmap = os.path.join(self.root, "capability-map.json")
        rc, out, err = run("inventory.py", "--repo", self.repo, "--profile", self.profile, "--out", self.cmap, "--commit", "abc1234")
        assert rc == 0, err

    def path(self, *parts) -> str:
        return os.path.join(self.root, *parts)

    def load_bank(self) -> dict:
        return dl.load_json(self.bank)

    def save_bank(self, b: dict) -> None:
        write_json(b, self.bank)

    def close(self):
        self._td.cleanup()


def run(script: str, *args, python: str | None = None) -> tuple[int, str, str]:
    r = subprocess.run([python or sys.executable, os.path.join(SCRIPTS, script), *args], capture_output=True, text=True)
    return r.returncode, r.stdout, r.stderr


def clone(obj):
    return copy.deepcopy(obj)
