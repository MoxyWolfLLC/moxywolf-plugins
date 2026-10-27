# drafted-by: gpt/gpt-6-astra
"""Black-box delivery acceptance tests.

Existing entry points exercised:
  task_graph.py run
  peer_review.py open, round, disposition, record-release
  check_ledger.py run

The new delivery entry points have this subprocess contract:
  goal_delivery.py reserve-review --delivery FILE --change-id ID --review-id ID
      Persist the reservation; print {"reserved": true, "attempts_used": N}.
      Exhaustion exits nonzero without incrementing the persisted count.
  goal_delivery.py sync-checkout --checkout FILE --merge SHA
      Print {"status": "synced" | "sync_pending", ...}.
      A pending result identifies the checkout and explains the reason.
  goal_delivery.py status --delivery FILE
      Print {"delivery_status": STATUS, ...}.
  goal_run.py resume GOAL --repo OWNER/REPO
      Resume the delivery in GSTACK_GOAL_RUN_DIR/GOAL/state.json, observe
      GitHub through GSTACK_GITHUB_API, execute authorized delivery steps,
      and print a JSON object containing delivery_status.

Delivery documents below are literal fixtures for the new persisted contract.
Only external boundaries are substituted: GitHub and the reviewer executable.
Git repositories, receipts, dispatcher runs, synchronization and release
recording are exercised through candidate programs.

Verification: existing interfaces and the frozen context schema were inspected.
These drafted tests were not executed in the read-only authoring session.
"""

import copy
import hashlib
import http.server
import json
import os
from pathlib import Path
import shutil
import socket
import stat
import subprocess
import sys
import tempfile
import threading
import unittest
from urllib.parse import urlsplit


SCRIPTS = "plugins/gstack-execution/scripts"
OWNER = "dorianatmoxywolf"
REPOSITORY = "fixture/app"
REMOTE_URL = "https://github.com/fixture/app.git"
CRITERION = "app.py returns the declared value"
STAMP = "2026-10-26T10:00:00Z"

BRIEF = """## Serves
Delivery fixture

## Outcome
Deliver the approved change, record its release, and synchronize required copies.

## Goal tests
- `tests/test_fixture.py::Fixture.test_delivered` (outcome)

## Allowed paths
- app.py

## Spend cap
$50

## Provider budgets
- openrouter: $50

## Max calls
20

## Max items
3

## Max review rounds per item
3

## Stop conditions
- an unreadable authority or budget record
"""

REVIEWER_SOURCE = r"""
import json
import os
from pathlib import Path
import sys

args = sys.argv[1:]
root = Path(args[args.index("-C") + 1])
for path in sorted(root.rglob("*")):
    if path.is_file():
        path.read_bytes()
reply = Path(os.environ["FIXTURE_REVIEW_REPLY"]).read_text()
Path(args[args.index("--output-last-message") + 1]).write_text(reply)
with open(os.environ["FIXTURE_REVIEW_CALLS"], "a") as stream:
    stream.write(json.dumps({"cwd": str(root), "argv": args}) + "\n")
print("model: gpt-6-astra", file=sys.stderr)
"""

GIT_SOURCE = r"""
import json
import os
import subprocess
import sys

args = sys.argv[1:]
with open(os.environ["FIXTURE_GIT_CALLS"], "a") as stream:
    stream.write(json.dumps(args) + "\n")
prefix = []
if any(word in args for word in ("fetch", "push", "ls-remote")):
    for remote, local in json.loads(os.environ["FIXTURE_ORIGINS"]).items():
        prefix += ["-c", "url." + local + ".insteadOf=" + remote]
raise SystemExit(subprocess.call([os.environ["FIXTURE_REAL_GIT"], *prefix, *args]))
"""

GH_SOURCE = r"""
import json
import os
import sys

with open(os.environ["FIXTURE_GH_CALLS"], "a") as stream:
    stream.write(json.dumps(sys.argv[1:]) + "\n")
print("fixture: use the configured GSTACK_GITHUB_API endpoint", file=sys.stderr)
raise SystemExit(97)
"""

WORKER_SOURCE = r"""
import json
from pathlib import Path
import sys

payload = json.loads(Path(sys.argv[-1]).read_text())
node = payload["node"]
with open(node["dispatch_log"], "a") as stream:
    stream.write(node["id"] + "\n")
print(json.dumps({
    "complete": True,
    "coverage": node["checks"],
    "evidence": ["consumer.json:1"],
    "findings": [],
    "summary": "Read the selected consumer."
}))
"""


def write_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")
    return path


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def json_lines(path):
    path = Path(path)
    if not path.exists():
        return []
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def digest(data):
    return hashlib.sha256(data).hexdigest()


class GitHubFixture:
    """A local API boundary that records every request, including refused writes."""

    def __init__(self, root, head, base, accept_merge=None):
        self.root = Path(root)
        self.requests = []
        self.accepted = threading.Event()
        self.release_response = threading.Event()
        self.pause_after_accept = False
        self.accept_merge = accept_merge
        self.approval = {
            "id": 700,
            "state": "APPROVED",
            "commit_id": base,
            "user": {"login": OWNER, "type": "User"},
            "submitted_at": "2026-10-25T10:00:00Z",
            "html_url": "https://github.com/fixture/app/pull/7#pullrequestreview-700",
        }
        self.pr = {
            "number": 42,
            "state": "open",
            "merged": False,
            "merge_commit_sha": None,
            "merged_at": None,
            "merged_by": None,
            "mergeable": True,
            "mergeable_state": "clean",
            "head": {
                "ref": "goal/delivery",
                "sha": head,
                "repo": {"full_name": REPOSITORY},
            },
            "base": {
                "ref": "main",
                "sha": base,
                "repo": {"full_name": REPOSITORY},
            },
            "html_url": "https://github.com/fixture/app/pull/42",
        }
        fixture = self

        class Handler(http.server.BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass

            def do_GET(self):
                self.respond()

            def do_POST(self):
                self.respond()

            def do_PUT(self):
                self.respond()

            def do_PATCH(self):
                self.respond()

            def do_DELETE(self):
                self.respond()

            def respond(self):
                length = int(self.headers.get("Content-Length", "0"))
                raw = self.rfile.read(length)
                try:
                    body = json.loads(raw) if raw else None
                except ValueError:
                    body = raw.decode("utf-8", "replace")
                path = urlsplit(self.path).path
                request = {"method": self.command, "path": path, "body": body}
                fixture.requests.append(request)
                with open(fixture.root / "requests.jsonl", "a", encoding="utf-8") as stream:
                    stream.write(json.dumps(request) + "\n")
                code, reply = fixture.route(self.command, path, body)
                encoded = json.dumps(reply).encode()
                try:
                    self.send_response(code)
                    self.send_header("Content-Type", "application/json")
                    self.send_header("Content-Length", str(len(encoded)))
                    self.end_headers()
                    self.wfile.write(encoded)
                except (BrokenPipeError, ConnectionResetError):
                    pass

        self.server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.url = "http://127.0.0.1:%d" % self.server.server_address[1]
        self.persist()

    def persist(self):
        write_json(self.root / "github-state.json", self.pr)

    def mark_merged(self, sha):
        self.pr.update(
            state="closed",
            merged=True,
            merge_commit_sha=sha,
            merged_at=STAMP,
            merged_by={"login": "moxywolf-agent[bot]", "type": "Bot"},
        )
        self.persist()

    def route(self, method, path, body):
        prefix = "/repos/" + REPOSITORY
        if method == "PUT" and path == prefix + "/pulls/42/merge":
            if self.pr["merged"]:
                return 409, {"message": "duplicate merge request"}
            if not isinstance(body, dict) or body.get("sha") != self.pr["head"]["sha"]:
                return 409, {"message": "merge must name the exact approved head"}
            if self.accept_merge is None:
                return 403, {"message": "this fixture permits reads only"}
            self.accept_merge()
            self.mark_merged(self.pr["head"]["sha"])
            self.accepted.set()
            if self.pause_after_accept:
                self.release_response.wait(30)
            return 200, {"merged": True, "sha": self.pr["merge_commit_sha"]}
        if method != "GET":
            return 405, {"message": "unexpected write"}
        if path == prefix + "/pulls/42":
            return 200, copy.deepcopy(self.pr)
        if path == prefix + "/pulls/7/reviews/700":
            return 200, self.approval
        if path == prefix + "/pulls/7/reviews":
            return 200, [self.approval]
        if path == prefix + "/pulls/7":
            return 200, {
                "number": 7,
                "state": "closed",
                "merged": True,
                "head": {"sha": self.approval["commit_id"], "ref": "approve-delivery"},
                "base": {"ref": "main", "repo": {"full_name": REPOSITORY}},
            }
        if path == prefix + "/pulls/42/reviews":
            return 200, [
                dict(self.approval, commit_id=self.pr["head"]["sha"])
            ]
        if path == prefix + "/issues/42/comments":
            return 200, []
        if path == prefix + "/pulls/42/files":
            return 200, [{"filename": "app.py", "status": "modified"}]
        if path == prefix + "/environments":
            return 200, {"environments": [{"name": "goal-holdout"}]}
        if path == prefix + "/deployments":
            return 200, []
        if path == prefix + "/commits/" + self.pr["head"]["sha"] + "/check-runs":
            binding = (
                "pr=42;base_ref=main;base=" + self.pr["base"]["sha"]
            )
            return 200, {
                "check_runs": [
                    {
                        "id": number,
                        "name": name,
                        "head_sha": self.pr["head"]["sha"],
                        "status": "completed",
                        "conclusion": "success",
                        "external_id": binding,
                    }
                    for number, name in enumerate(
                        ("tests", "goal-envelope", "goal-tests", "goal-holdout"), 1
                    )
                ]
            }
        return 404, {"message": "fixture has no response for " + path}

    def close(self):
        self.release_response.set()
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=5)


class Delivery(unittest.TestCase):
    def setUp(self):
        self.candidate = Path(os.environ["GOAL_CANDIDATE"]).absolute()
        temporary = tempfile.TemporaryDirectory(prefix="delivery-goal-")
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.bin = self.root / "bin"
        self.bin.mkdir()
        self.reviews = self.root / "reviews"
        self.reviews.mkdir()
        self.runs = self.root / "runs"
        self.runs.mkdir()
        self.real_git = shutil.which("git")
        self.assertIsNotNone(self.real_git, "Git is required to exercise real checkouts")
        self.env = {
            "PATH": str(self.bin) + os.pathsep + os.defpath,
            "HOME": str(self.root / "home"),
            "TMPDIR": str(self.root),
            "TMP": str(self.root),
            "TEMP": str(self.root),
            "LC_ALL": "C",
            "PYTHONDONTWRITEBYTECODE": "1",
            "PYTHONNOUSERSITE": "1",
            "GIT_CONFIG_NOSYSTEM": "1",
            "GIT_CONFIG_GLOBAL": os.devnull,
            "GIT_OPTIONAL_LOCKS": "0",
            "GIT_TERMINAL_PROMPT": "0",
            "GIT_ALLOW_PROTOCOL": "file",
            "GSTACK_PEER_REVIEW_DIR": str(self.reviews),
            "GSTACK_GOAL_RUN_DIR": str(self.runs),
            "GSTACK_REVIEWER": "codex",
            "FIXTURE_REAL_GIT": self.real_git,
            "FIXTURE_ORIGINS": "{}",
            "FIXTURE_GIT_CALLS": str(self.root / "git-calls.jsonl"),
            "FIXTURE_GH_CALLS": str(self.root / "gh-calls.jsonl"),
            "FIXTURE_REVIEW_CALLS": str(self.root / "review-calls.jsonl"),
            "FIXTURE_REVIEW_REPLY": str(self.root / "review-reply.json"),
            "HTTP_PROXY": "http://127.0.0.1:9",
            "HTTPS_PROXY": "http://127.0.0.1:9",
            "NO_PROXY": "127.0.0.1,localhost",
        }
        Path(self.env["HOME"]).mkdir()
        for name, source in (
            ("git", GIT_SOURCE),
            ("gh", GH_SOURCE),
            ("codex", REVIEWER_SOURCE),
        ):
            path = self.bin / name
            path.write_text("#!" + sys.executable + "\n" + source, encoding="utf-8")
            path.chmod(0o755)

    def _command(self, script, *arguments):
        return [
            sys.executable,
            "-B",
            str(self.candidate / SCRIPTS / script),
            *map(str, arguments),
        ]

    def _call(self, script, *arguments, cwd=None):
        return subprocess.run(
            self._command(script, *arguments),
            cwd=str(cwd or self.candidate),
            env=self.env,
            stdin=subprocess.DEVNULL,
            capture_output=True,
            text=True,
            timeout=120,
        )

    def _ok(self, result):
        self.assertEqual(
            result.returncode,
            0,
            "stdout:\n%s\nstderr:\n%s" % (result.stdout, result.stderr),
        )
        return result

    def _object(self, result):
        self._ok(result)
        try:
            value = json.loads(result.stdout)
        except ValueError:
            self.fail("Expected JSON, received:\n" + result.stdout + result.stderr)
        self.assertIsInstance(value, dict)
        return value

    def _git(self, repo, *arguments):
        result = subprocess.run(
            [self.real_git, "-C", str(repo), *map(str, arguments)],
            env=self.env,
            stdin=subprocess.DEVNULL,
            capture_output=True,
            text=True,
            timeout=30,
        )
        self._ok(result)
        return result.stdout.strip()

    def _repo(self, name):
        repo = self.root / name
        repo.mkdir()
        self._git(repo, "init", "-q", "-b", "main")
        self._git(repo, "config", "user.name", "Delivery Fixture")
        self._git(repo, "config", "user.email", "delivery@example.invalid")
        self._git(repo, "config", "core.hooksPath", os.devnull)
        base = self._commit(repo, {"app.py": "VALUE = 1\n"}, "base")
        return repo, base

    def _commit(self, repo, files, message):
        for name, contents in files.items():
            path = repo / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(contents, encoding="utf-8")
        self._git(repo, "add", "--all")
        self._git(repo, "commit", "-qm", message)
        return self._git(repo, "rev-parse", "HEAD")

    def _policy(self, commands=()):
        return {
            "owner": OWNER,
            "classification": "internal",
            "allow_repository": True,
            "allow_history": True,
            "allowed_tools": ["claude", "codex"],
            "allowed_commands": list(commands),
            "output_roots": [str(self.root)],
            "destinations": [],
        }

    def _packet(self, repo, base, head):
        return {
            "outcome": "app.py returns the declared value",
            "acceptance_criteria": [CRITERION],
            "repos": [{
                "path": str(repo),
                "base": base,
                "head": head,
                "review_base": base,
            }],
            "changed_behavior": "The declared value changes.",
            "exclusions": [],
            "tests": {},
            "release_owner": OWNER,
            "prior_findings": [],
            "data_use": self._policy(),
        }

    def _reply(self, blocking=False, fixed=False):
        return {
            "verdict": "blocking_findings" if blocking else "no_blocking_findings",
            "acceptance": [{
                "criterion": CRITERION,
                "met": not blocking,
                "evidence": "app.py:1",
            }],
            "findings": [{
                "id": "F1",
                "severity": "blocking",
                "file": "app.py",
                "line": 1,
                "what": "The declared value needs correction.",
                "evidence": "app.py:1",
                "criterion": CRITERION,
                "fix": "Correct the value.",
                "category": "general",
            }] if blocking else [],
            "blocker_resolutions": [{
                "id": "F1",
                "resolved": True,
                "evidence": "app.py:1",
            }] if fixed else [],
            "regressions_from_fixes": [],
            "unknowns": [],
        }

    def _ledger(self, repo):
        self._ok(self._call(
            "check_ledger.py", "run", "--repo", repo, "--",
            sys.executable, "-c", "print('delivery fixture check passed')",
            cwd=repo,
        ))
        rows = []
        for path in (self.reviews / "ledger").rglob("*.jsonl"):
            for row in json_lines(path):
                if row["repo"] in (
                    "local:" + str(repo.resolve()),
                    REMOTE_URL,
                    "https://github.com/foreign/app.git",
                ):
                    rows.append((row["ended"], row, path))
        self.assertTrue(rows, "check_ledger produced no external receipt")
        _, row, path = max(rows, key=lambda item: item[0])
        receipt = path.with_name(path.stem + ".receipts") / (row["id"] + ".log")
        self.assertTrue(receipt.is_file())
        self.assertEqual(digest(receipt.read_bytes()), row["receipt"]["sha256"])
        return row, path, receipt

    def _fix_fixture(self, name):
        repo, base = self._repo(name)
        self._git(repo, "switch", "-qc", "build/value")
        first_head = self._commit(repo, {"app.py": "VALUE = 2\n"}, "initial change")
        old_run, ledger, receipt = self._ledger(repo)
        packet = self._packet(repo, base, first_head)
        packet["tests"]["ledger_runs"] = [{"repo": str(repo), "run_id": old_run["id"]}]
        packet_file = write_json(self.root / (name + "-packet.json"), packet)
        opened = self._object(self._call(
            "peer_review.py", "open", "--builder", "claude",
            "--packet", packet_file, "--timeout", "20",
        ))
        review_id = opened["review_id"]
        write_json(self.env["FIXTURE_REVIEW_REPLY"], self._reply(blocking=True))
        first = self._call("peer_review.py", "round", review_id)
        self.assertNotEqual(first.returncode, 0)
        directory = self.reviews / review_id
        self.assertEqual(read_json(directory / "state.json")["outcome"], "blocking_findings")
        self.assertTrue((directory / "round-1.json").is_file())
        self._ok(self._call("peer_review.py", "disposition", review_id, "F1=fixed"))
        retained = {
            name: (directory / name).read_bytes()
            for name in ("packet.json", "round-1.json")
        }
        second_head = self._commit(repo, {"app.py": "VALUE = 3\n"}, "fix")
        write_json(self.env["FIXTURE_REVIEW_REPLY"], self._reply(fixed=True))
        return repo, review_id, directory, second_head, old_run, ledger, receipt, retained

    def _seed_review(self, repo, base, head, review_id, model_selection=False):
        packet = self._packet(repo, base, head)
        if model_selection:
            packet["items"] = ["delivery/1"]
            packet["model_selection"] = {
                "status": "checked",
                "mode": "shadow",
                "tier": "floor",
                "rule": "fixture",
                "routing": "advice",
            }
        directory = self.reviews / review_id
        write_json(directory / "packet.json", packet)
        write_json(directory / "state.json", {
            "review_id": review_id,
            "builder": "claude",
            "reviewer": "codex",
            "release_owner": OWNER,
            "outcome": "no_blocking_findings",
            "rounds_used": 1,
            "max_rounds": 3,
            "timeout": 20,
            "coverage_checked": True,
            "coverage_status": "covered",
            "coverage_overridden": False,
            "ledger_status": "clear",
            "heads": [[head]],
            "release_lane": {"lane": "contained", "matched": []},
        })
        write_json(directory / "round-1.json", {
            "round": 1,
            "repos": packet["repos"],
            "raw": json.dumps(self._reply()),
            "outcome": "no_blocking_findings",
            "findings": [],
            "unknowns_raised": [],
        })
        write_json(directory / "release.json", {
            "repos": packet["repos"],
            "release_owner": OWNER,
            "target": "main",
            "requested_at": "2026-10-25T12:00:00Z",
        })
        return directory

    def _api(self, head, base, accept_merge=None):
        api_root = self.root / ("api-" + str(len(list(self.root.glob("api-*")))))
        api_root.mkdir()
        api = GitHubFixture(api_root, head, base, accept_merge)
        self.addCleanup(api.close)
        self.env["GSTACK_GITHUB_API"] = api.url
        self.env["GITHUB_TOKEN"] = "fixture-only-token"
        self.env["GSTACK_GOAL_RUN_TOKEN"] = "1"
        return api

    def _sync_fixture(self, name):
        source, base = self._repo(name + "-source")
        bare = self.root / (name + "-origin.git")
        self._git(self.root, "init", "--bare", "-q", "--initial-branch=main", bare)
        self._git(source, "push", "-q", bare, "main")
        checkout = self.root / (name + "-checkout")
        self._git(self.root, "clone", "-q", bare, checkout)
        self._git(checkout, "config", "user.name", "Delivery Fixture")
        self._git(checkout, "config", "user.email", "delivery@example.invalid")
        self._git(checkout, "config", "core.hooksPath", os.devnull)
        self._git(checkout, "remote", "set-url", "origin", REMOTE_URL)
        self._git(source, "remote", "add", "origin", REMOTE_URL)
        mappings = json.loads(self.env["FIXTURE_ORIGINS"])
        mappings[REMOTE_URL] = bare.as_uri()
        self.env["FIXTURE_ORIGINS"] = json.dumps(mappings)
        head = self._commit(source, {"app.py": "VALUE = 2\n"}, "approved change")
        specification = {
            "name": name,
            "path": str(checkout),
            "host": socket.gethostname(),
            "repo": REPOSITORY,
            "remote": REMOTE_URL,
            "branch": "main",
            "required": True,
        }
        return source, bare, checkout, base, head, specification

    def _delivery_document(self, repo, base, head, review_id, checkouts=()):
        return {
            "schema_version": 1,
            "goal": "delivery",
            "approval": {
                "repo": REPOSITORY,
                "pr": 7,
                "review_id": 700,
                "head": base,
                "owner": OWNER,
                "url": "https://github.com/fixture/app/pull/7#pullrequestreview-700",
            },
            "max_review_rounds": 3,
            "active_seconds": 17,
            "source_bindings": [],
            "changes": {
                "implementation": {
                    "repo": REPOSITORY,
                    "path": str(repo),
                    "base": base,
                    "head": head,
                    "target": "main",
                    "pr": 42,
                    "review_id": review_id,
                    "review_attempts": [],
                    "original_findings": [],
                    "merge": None,
                    "release_record": None,
                },
            },
            "release_companion": None,
            "required_checkouts": list(checkouts),
        }

    def _resume_fixture(self):
        source, bare, checkout, base, head, spec = self._sync_fixture("required-mac")
        self._git(source, "branch", "-m", "goal/delivery")
        review_id = "delivery-review"
        review_dir = self._seed_review(source, base, head, review_id, model_selection=True)
        delivery = self._delivery_document(source, base, head, review_id, [spec])
        directory = self.runs / "delivery"
        goal_workflows = {
            "goal-envelope.yml": "03c4d6e7e6ee8a5aca467cbea7899b22f1a00b1cae72d36b0d65bbfe412823d5",
            "goal-tests.yml": "27bfd7ad9b61ee9cb491ee5abee6b9b8899af7a616ea851da7c92004900460a5",
            "goal-holdout.yml": "76ab3029baef7a5b42911dcd9eb0071992260c79fe71a328ba926a2e1192f21b",
        }
        write_json(directory / "state.json", {
            "goal": "delivery",
            "pr": 7,
            "review_id": 700,
            "approved_head": base,
            "tree": self._git(source, "rev-parse", base + "^{tree}"),
            "builder": "claude/claude-opus-5",
            "drafted_by": ["gpt"],
            "read_by": "gemini",
            "branch": "goal/delivery",
            "main_at_start": base,
            "items": [{"n": 1, "title": "Deliver change", "criteria": [CRITERION]}],
            "max_items": 3,
            "max_rounds": 3,
            "tests": [["tests/test_fixture.py::Fixture.test_delivered", "outcome"]],
            "done": [1],
            "passing": ["tests/test_fixture.py::Fixture.test_delivered"],
            "results": [{
                "head": head,
                "results": {"tests/test_fixture.py::Fixture.test_delivered": "passed"},
                "unsure": "",
            }],
            "outcome": None,
            "reason": None,
            "merge": None,
            "calls": [],
            "messages": [],
            "triggers": digest(json.dumps(
                [{}, ["goal-holdout"], goal_workflows], sort_keys=True
            ).encode()),
            "spent": [],
            "finalize_pr": 41,
            "final_pr": 42,
            "finalized_head": head,
            "delivery": delivery,
        })
        goal = directory / "goal"
        goal.mkdir()
        (goal / "GOAL.md").write_text(BRIEF, encoding="utf-8")
        (goal / "PLAN.md").write_text(
            "1. Deliver change\n   - app.py returns the declared value\n",
            encoding="utf-8",
        )
        (directory / "spend.jsonl").write_text("", encoding="utf-8")
        grants = []
        for klass, resource, scope in (
            ("vcs.push", "goal/delivery", "project"),
            ("vcs.push", "build/*", "project"),
            ("pr.open", "main<-goal/delivery", "once"),
        ):
            grant = {
                "granted_at": "2026-10-25T10:00:00Z",
                "class": klass,
                "resource": resource,
                "scope": scope,
                "granted_by": "Dorian, approving goal delivery in PR #7",
                "excludes": [],
                "session": None,
            }
            grant["id"] = digest(json.dumps(grant, sort_keys=True).encode())[:12]
            grants.append(grant)
        (directory / "ledger.jsonl").write_text(
            "".join(json.dumps(row) + "\n" for row in grants), encoding="utf-8"
        )
        api = self._api(
            head, base,
            lambda: self._git(source, "push", "-q", bare, head + ":refs/heads/main"),
        )
        return api, checkout, head, review_dir, directory

    def _snapshot(self, root):
        root = Path(root)
        if not root.exists():
            return {"exists": False}
        status_output = self._git(root, "status", "--porcelain=v1", "--untracked-files=all")
        entries = {}
        for path in sorted(root.rglob("*")):
            info = path.lstat()
            key = path.relative_to(root).as_posix()
            mode = stat.S_IMODE(info.st_mode)
            if path.is_symlink():
                entries[key] = ("link", mode, os.readlink(path), info.st_mtime_ns)
            elif path.is_file():
                entries[key] = ("file", mode, digest(path.read_bytes()), info.st_mtime_ns)
            elif path.is_dir():
                entries[key] = ("directory", mode, info.st_mtime_ns)
        return {"exists": True, "status": status_output, "entries": entries}

    def test_stale_binding_refuses_before_dispatch(self):
        """Scenario: Given a packet whose selected artifact is fresh but whose attested prerequisite or embedded pointer binding is stale, then the executor refuses before any worker starts and creates no run directory"""
        repo, _ = self._repo("context")
        bank_one = '{"version":1}'
        bank_two = '{"version":2}'
        hash_one = "sha256:" + digest(bank_one.encode())
        hash_two = "sha256:" + digest(bank_two.encode())
        consumer = json.dumps({"bank": {"hash": hash_one}})
        first = self._commit(
            repo, {"bank.json": bank_one, "consumer.json": consumer}, "bound consumer"
        )
        worker = self.root / "worker.py"
        worker.write_text(WORKER_SOURCE, encoding="utf-8")
        command = [sys.executable, str(worker)]
        dispatches = self.root / "dispatches.log"

        def packet(head, bank_revision, bank_content):
            return {
                "owner": OWNER,
                "builder": "codex",
                "repos": [{"path": str(repo), "base": head, "head": head}],
                "data_use": self._policy([command]),
                "context": {
                    "schema_version": 1,
                    "objective": "Read the accepted consumer and its bound prerequisite",
                    "artifacts": [
                        {
                            "id": "bank", "kind": "requirement",
                            "revision": bank_revision, "status": "accepted",
                            "source": "bank.json", "content": bank_content,
                            "reason": "accepted prerequisite", "attest": "sha256",
                        },
                        {
                            "id": "consumer", "kind": "evidence",
                            "revision": head, "status": "accepted",
                            "source": "consumer.json", "content": consumer,
                            "reason": "selected artifact", "attest": "content",
                            "binds": {"bank": {"pointer": "/bank/hash"}},
                        },
                    ],
                    "links": [{
                        "from": "consumer", "relation": "depends_on", "to": "bank"
                    }],
                    "questions": [],
                },
            }

        workflow = write_json(self.root / "workflow.json", {
            "name": "binding-fixture",
            "nodes": [
                {
                    "id": "read", "kind": "worker", "depends_on": [],
                    "inputs": ["packet"], "outputs": ["read.json"],
                    "effects": ["read_only"], "on_failure": "block",
                    "checks": ["consumer"], "command": command,
                    "context_inputs": ["consumer"],
                    "requires_accepted": ["consumer"],
                    "dispatch_log": str(dispatches),
                },
                {
                    "id": "report", "kind": "report", "depends_on": ["read"],
                    "inputs": ["packet", "read"], "outputs": ["report.json"],
                    "effects": ["local_report"], "on_failure": "block",
                    "checks": ["read"],
                },
            ],
        })

        def execute(label, value):
            packet_file = write_json(self.root / (label + ".json"), value)
            run = self.root / (label + "-run")
            result = self._call(
                "task_graph.py", "run", "--workflow", workflow,
                "--packet", packet_file, "--run-dir", run, "--jobs", "1",
            )
            return result, run

        fresh, _ = execute("fresh-control", packet(first, first, hash_one))
        self._ok(fresh)
        self.assertEqual(dispatches.read_text().splitlines(), ["read"])
        second = self._commit(repo, {"bank.json": bank_two}, "prerequisite changed")
        for label, revision, content in (
            ("stale-revision", first, hash_one),
            ("stale-attestation", second, hash_one),
            ("stale-pointer", second, hash_two),
        ):
            with self.subTest(binding=label):
                before = dispatches.read_bytes()
                result, run = execute(label, packet(second, revision, content))
                self.assertNotEqual(result.returncode, 0, result.stdout)
                self.assertRegex((result.stdout + result.stderr).lower(), r"stale|binding")
                self.assertEqual(dispatches.read_bytes(), before, "a worker was dispatched")
                self.assertFalse(run.exists(), "refusal created a run directory")

    def test_fix_round_refreshes_head_bound_ledger(self):
        """Scenario: Given a review fix round that names a ledger run at the new head, then the round's record carries that run with head_matches true and receipt_verified true, and the retained packet and earlier round bytes are unchanged"""
        repo, review_id, directory, head, old_run, _, _, retained = self._fix_fixture("fix")
        current, _, _ = self._ledger(repo)
        self.assertNotEqual(current["id"], old_run["id"])
        self.assertEqual(current["head"], head)
        result = self._call(
            "peer_review.py", "round", review_id,
            "--head", str(repo) + "=" + head,
            "--ledger-run", str(repo) + "=" + current["id"],
        )
        self._ok(result)
        record_file = directory / "round-2.json"
        self.assertTrue(record_file.is_file(), result.stdout + result.stderr)
        record = read_json(record_file)
        evidence = [row for row in record["ledger_runs"] if row["run_id"] == current["id"]]
        self.assertEqual(len(evidence), 1)
        self.assertIs(evidence[0]["head_matches"], True)
        self.assertIs(evidence[0]["receipt_verified"], True)
        self.assertEqual(evidence[0]["exit_code"], 0)
        self.assertEqual(record["repos"][0]["head"], head)
        self.assertEqual(record["outcome"], "fixes_verified")
        for name, contents in retained.items():
            self.assertEqual((directory / name).read_bytes(), contents, name + " was rewritten")

    def test_wrong_head_or_tampered_receipt_cannot_clear_head(self):
        """Scenario: Given a ledger receipt that belongs to an older head or another repository, then it reports head_matches false or receipt_verified false and cannot clear the candidate"""
        for case in ("older-head", "tampered", "another-repository"):
            with self.subTest(receipt=case):
                repo, review_id, directory, head, old, ledger, _, retained = (
                    self._fix_fixture("receipt-" + case)
                )
                selected = old
                if case == "tampered":
                    selected, _, receipt = self._ledger(repo)
                    receipt.write_bytes(receipt.read_bytes() + b"\nforged success\n")
                elif case == "another-repository":
                    other = self.root / "foreign-copy"
                    self._git(self.root, "clone", "-q", repo, other)
                    self._git(other, "remote", "set-url", "origin",
                              "https://github.com/foreign/app.git")
                    selected, _, foreign_receipt = self._ledger(other)
                    self.assertEqual(selected["head"], head)
                    with ledger.open("a", encoding="utf-8") as stream:
                        stream.write(json.dumps(selected) + "\n")
                    copied = ledger.with_name(ledger.stem + ".receipts") / (
                        selected["id"] + ".log"
                    )
                    copied.write_bytes(foreign_receipt.read_bytes())
                result = self._call(
                    "peer_review.py", "round", review_id,
                    "--head", str(repo) + "=" + head,
                    "--ledger-run", str(repo) + "=" + selected["id"],
                )
                self.assertNotEqual(result.returncode, 0, "invalid evidence cleared the fix")
                record_file = directory / "round-2.json"
                self.assertTrue(record_file.is_file(), result.stdout + result.stderr)
                record = read_json(record_file)
                evidence = [
                    row for row in record["ledger_runs"]
                    if row["run_id"] == selected["id"]
                ]
                self.assertEqual(len(evidence), 1)
                if case == "older-head":
                    self.assertIs(evidence[0]["head_matches"], False)
                else:
                    self.assertIs(evidence[0]["receipt_verified"], False)
                self.assertNotIn(
                    read_json(directory / "state.json")["outcome"],
                    ("no_blocking_findings", "fixes_verified"),
                )
                for name, contents in retained.items():
                    self.assertEqual((directory / name).read_bytes(), contents)

    def test_replacement_review_cannot_reset_attempt_limit(self):
        """Scenario: Given a delivery whose change has used its three review passes, then a fourth reservation under a new review ID is refused and a restart preserves the count"""
        repo, base = self._repo("attempts")
        head = self._commit(repo, {"app.py": "VALUE = 2\n"}, "change")
        document = self._delivery_document(repo, base, head, "review-1")
        original = [{"id": "F1", "what": "Original unresolved finding", "file": "app.py"}]
        document["changes"]["implementation"]["original_findings"] = original
        path = write_json(self.root / "attempts.json", document)
        for number in range(1, 4):
            result = self._object(self._call(
                "goal_delivery.py", "reserve-review", "--delivery", path,
                "--change-id", "implementation", "--review-id", "review-" + str(number),
            ))
            self.assertIs(result["reserved"], True)
            self.assertEqual(result["attempts_used"], number)
            saved = read_json(path)
            self.assertEqual(
                len(saved["changes"]["implementation"]["review_attempts"]), number
            )
            self.assertEqual(
                saved["changes"]["implementation"]["original_findings"], original
            )
            self.assertGreaterEqual(saved["active_seconds"], 17)
        for replacement in ("replacement-review", "replacement-after-restart"):
            result = self._call(
                "goal_delivery.py", "reserve-review", "--delivery", path,
                "--change-id", "implementation", "--review-id", replacement,
            )
            self.assertNotEqual(result.returncode, 0, result.stdout)
            self.assertRegex(
                (result.stdout + result.stderr).lower(), r"limit|exhaust|three|3"
            )
            saved = read_json(path)
            self.assertEqual(
                len(saved["changes"]["implementation"]["review_attempts"]), 3
            )
            self.assertEqual(
                saved["changes"]["implementation"]["original_findings"], original
            )
            self.assertEqual(saved["approval"], document["approval"])

    def test_resume_after_accepted_merge_records_once(self):
        """Scenario: Given GitHub has accepted the exact-head merge and the process exits before record-release, then a fresh process discovers that merge, records it once, synchronizes the required clean checkout, and reports complete without issuing a second merge request"""
        api, checkout, head, review_dir, directory = self._resume_fixture()
        api.pause_after_accept = True
        process = subprocess.Popen(
            self._command("goal_run.py", "resume", "delivery", "--repo", REPOSITORY),
            cwd=str(self.candidate),
            env=self.env,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        try:
            accepted = api.accepted.wait(15)
            if not accepted:
                if process.poll() is None:
                    process.kill()
                stdout, stderr = process.communicate(timeout=10)
                self.fail("No exact-head merge was accepted:\n" + stdout + stderr)
            process.kill()
            process.communicate(timeout=10)
        finally:
            if process.poll() is None:
                process.kill()
                process.communicate(timeout=10)
            api.release_response.set()

        release_file = review_dir / "release-fixture-app-42.json"
        self.assertTrue(read_json(api.root / "github-state.json")["merged"])
        self.assertFalse(release_file.exists(), "crash must precede release recording")
        requests_before_resume = len(api.requests)
        resumed = self._call("goal_run.py", "resume", "delivery", "--repo", REPOSITORY)
        self._ok(resumed)
        self.assertIn('"delivery_status": "complete"', resumed.stdout)
        self.assertEqual(self._git(checkout, "rev-parse", "HEAD"), head)
        self.assertEqual(self._git(checkout, "status", "--porcelain"), "")
        self.assertTrue(release_file.is_file())
        release = read_json(release_file)
        self.assertEqual(release["head"], head)
        self.assertEqual(release["merge_commit"], head)
        self.assertEqual(release["source"], "https://github.com/fixture/app/pull/42")
        self.assertTrue(any(
            request["method"] == "GET" and request["path"].endswith("/pulls/42")
            for request in api.requests[requests_before_resume:]
        ))
        self.assertFalse(any(
            request["method"] != "GET"
            for request in api.requests[requests_before_resume:]
        ))
        selection_ledger = self.reviews / "model-selection" / "fixture-app.jsonl"
        rows = [row for row in json_lines(selection_ledger)
                if row["review_id"] == "delivery-review"]
        self.assertEqual(len(rows), 1)
        record_bytes = release_file.read_bytes()
        ledger_bytes = selection_ledger.read_bytes()

        again = self._call("goal_run.py", "resume", "delivery", "--repo", REPOSITORY)
        self._ok(again)
        self.assertIn('"delivery_status": "complete"', again.stdout)
        self.assertEqual(release_file.read_bytes(), record_bytes)
        self.assertEqual(selection_ledger.read_bytes(), ledger_bytes)
        merges = [
            request for request in api.requests
            if request["method"] != "GET" and request["path"].endswith("/merge")
        ]
        self.assertEqual(len(merges), 1)
        self.assertEqual(merges[0]["body"]["sha"], head)
        self.assertEqual(json_lines(self.root / "gh-calls.jsonl"), [])
        saved = read_json(directory / "state.json")
        self.assertFalse([message for message in saved.get("messages", [])
                          if message.get("waits")])
        self.assertNotRegex(
            resumed.stdout + again.stdout,
            r"authorization_required|approval_required|awaiting_approval",
        )

    def test_dirty_required_checkout_preserved_and_pending(self):
        """Scenario: Given a required checkout that is dirty, on an unexpected branch, divergent, on the wrong host, or unavailable, then its tracked and untracked bytes, status and Git metadata are unchanged and the delivery reports sync_pending naming that checkout and reason"""
        cases = {
            "dirty": r"dirty|uncommitted|untracked",
            "unexpected-branch": r"branch",
            "divergent": r"diverg|fast.forward",
            "wrong-host": r"host",
            "unavailable": r"unavailable|missing|not.*exist",
        }
        for case, reason in cases.items():
            with self.subTest(checkout=case):
                source, bare, checkout, _, head, spec = self._sync_fixture(case)
                self._git(source, "push", "-q", bare, head + ":refs/heads/main")
                if case == "dirty":
                    (checkout / "app.py").write_bytes(b"VALUE = 'local'\n")
                    (checkout / "untracked.bin").write_bytes(b"\x00local\xff\n")
                elif case == "unexpected-branch":
                    self._git(checkout, "switch", "-qc", "personal-work")
                elif case == "divergent":
                    self._commit(checkout, {"local.txt": "local commit\n"}, "local divergence")
                elif case == "wrong-host":
                    spec["host"] = "another-machine.invalid"
                elif case == "unavailable":
                    spec["path"] = str(self.root / "missing-checkout")
                    checkout = Path(spec["path"])
                config = write_json(self.root / (case + "-checkout.json"), spec)
                before = self._snapshot(checkout)
                result = self._call(
                    "goal_delivery.py", "sync-checkout",
                    "--checkout", config, "--merge", head,
                )
                self.assertIn(result.returncode, (0, 1, 3), result.stdout + result.stderr)
                try:
                    report = json.loads(result.stdout)
                except ValueError:
                    self.fail("Expected a pending sync report:\n" + result.stdout + result.stderr)
                self.assertEqual(report["status"], "sync_pending")
                self.assertIn(spec["name"], json.dumps(report))
                self.assertRegex(str(report.get("reason", "")).lower(), reason)
                self.assertEqual(self._snapshot(checkout), before)

        source, bare, checkout, _, merged, spec = self._sync_fixture("clean-control")
        advanced = self._commit(source, {"later.txt": "later main change\n"}, "main advanced")
        self._git(source, "push", "-q", bare, advanced + ":refs/heads/main")
        config = write_json(self.root / "clean-checkout.json", spec)
        report = self._object(self._call(
            "goal_delivery.py", "sync-checkout", "--checkout", config, "--merge", merged,
        ))
        self.assertEqual(report["status"], "synced")
        self.assertEqual(self._git(checkout, "rev-parse", "HEAD"), advanced)
        self._git(checkout, "merge-base", "--is-ancestor", merged, "HEAD")
        self.assertEqual(self._git(checkout, "status", "--porcelain"), "")

    def test_release_companion_required_before_complete(self):
        """Scenario: Given a goal whose declared release companion is not merged and recorded, then delivery_status is not complete"""
        repo, base = self._repo("companion")
        head = self._commit(repo, {"app.py": "VALUE = 2\n"}, "implementation")
        document = self._delivery_document(repo, base, head, "implementation-review")
        primary = document["changes"]["implementation"]
        primary["merge"] = {"verified": True, "head": head, "sha": head}
        primary_record = write_json(self.root / "primary-release.json", {
            "review_id": "implementation-review",
            "repo": REPOSITORY,
            "head": head,
            "merge_commit": head,
            "source": "https://github.com/fixture/app/pull/42",
            "outcome": "agent_merge_autonomous",
            "recorded_at": STAMP,
        })
        primary["release_record"] = {"verified": True, "path": str(primary_record)}
        companion_head = self._commit(repo, {"release.txt": "marketplace bump\n"}, "companion")
        companion = {
            "repo": REPOSITORY,
            "path": str(repo),
            "base": head,
            "head": companion_head,
            "target": "main",
            "pr": 43,
            "review_id": "companion-review",
            "review_attempts": [],
            "original_findings": [],
            "merge": None,
            "release_record": None,
        }
        document["changes"]["marketplace"] = companion
        document["release_companion"] = "marketplace"
        path = self.root / "companion-delivery.json"

        write_json(path, document)
        unmerged = self._object(self._call("goal_delivery.py", "status", "--delivery", path))
        self.assertNotEqual(unmerged["delivery_status"], "complete")
        self.assertIn("marketplace", json.dumps(unmerged))

        companion["merge"] = {
            "verified": True, "head": companion_head, "sha": companion_head
        }
        write_json(path, document)
        unrecorded = self._object(self._call(
            "goal_delivery.py", "status", "--delivery", path
        ))
        self.assertNotEqual(unrecorded["delivery_status"], "complete")
        self.assertIn("marketplace", json.dumps(unrecorded))

        companion_record = write_json(self.root / "companion-release.json", {
            "review_id": "companion-review",
            "repo": REPOSITORY,
            "head": companion_head,
            "merge_commit": companion_head,
            "source": "https://github.com/fixture/app/pull/43",
            "outcome": "agent_merge_autonomous",
            "recorded_at": STAMP,
        })
        companion["release_record"] = {"verified": True, "path": str(companion_record)}
        write_json(path, document)
        completed = self._object(self._call(
            "goal_delivery.py", "status", "--delivery", path
        ))
        self.assertEqual(completed["delivery_status"], "complete")

    def test_record_release_never_merges(self):
        """Scenario: record-release performing or requesting a merge must never happen"""
        repo, base = self._repo("record-only")
        self._git(repo, "remote", "add", "origin", REMOTE_URL)
        head = self._commit(repo, {"app.py": "VALUE = 2\n"}, "reviewed change")
        review_id = "record-only-review"
        directory = self._seed_review(repo, base, head, review_id)
        api = self._api(head, base)
        release_file = directory / "release-fixture-app-42.json"

        unmerged = self._call(
            "peer_review.py", "record-release", review_id, "--repo", repo, "--pr", "42"
        )
        self.assertNotEqual(unmerged.returncode, 0)
        self.assertIn("release_blocked", unmerged.stdout + unmerged.stderr)
        self.assertFalse(release_file.exists())
        self.assertFalse(api.pr["merged"])

        api.mark_merged(head)
        api.pr["head"]["sha"] = base
        api.persist()
        wrong_head = self._call(
            "peer_review.py", "record-release", review_id, "--repo", repo, "--pr", "42"
        )
        self.assertNotEqual(wrong_head.returncode, 0)
        self.assertIn("release_blocked", wrong_head.stdout + wrong_head.stderr)
        self.assertFalse(release_file.exists())

        api.pr["head"]["sha"] = head
        api.persist()
        recorded = self._object(self._call(
            "peer_review.py", "record-release", review_id, "--repo", repo, "--pr", "42"
        ))
        self.assertEqual(recorded["head"], head)
        self.assertEqual(recorded["merge_commit"], head)
        self.assertTrue(release_file.is_file())
        self.assertEqual(read_json(release_file)["merge_commit"], head)
        self.assertGreaterEqual(len(api.requests), 3, "GitHub was never consulted")
        self.assertTrue(all(request["method"] == "GET" for request in api.requests))
        self.assertFalse(any(request["path"].endswith("/merge") for request in api.requests))
        self.assertEqual(json_lines(self.root / "gh-calls.jsonl"), [])
        self.assertNotRegex(
            unmerged.stdout + unmerged.stderr + wrong_head.stdout + wrong_head.stderr,
            r"gh\s+pr\s+merge|please\s+merge|request(?:ing)?\s+a\s+merge",
        )


if __name__ == "__main__":
    unittest.main()
