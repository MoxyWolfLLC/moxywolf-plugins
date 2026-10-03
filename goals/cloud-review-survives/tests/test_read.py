# drafted-by: gpt/gpt-6-astra
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import unittest


SCRIPT = "plugins/project-init/scripts/session_record.py"
SID = "11111111-2222-3333-4444-555555555555"
DISTINCTIVE = "The amber compass marks this session's review."
APPENDED = "This unapproved sentence was appended after publication."
SECTIONS = (
    "Objective and success criteria",
    "Outcome and deliverables",
    "Decisions, approvals, declines and redirects",
    "Human interventions and corrections",
    "Tool and external-action evidence",
    "Errors, retries, reversals and complexity",
    "Governance and privacy findings",
    "Proposals",
    "Open items and unresolved uncertainty",
    "Evidence gaps and completeness",
)


def remove_tree(root):
    root = Path(root)
    if not root.exists():
        return
    root.chmod(0o700)
    for directory, directories, files in os.walk(root):
        for name in directories:
            (Path(directory) / name).chmod(0o700)
        for name in files:
            (Path(directory) / name).chmod(0o600)
    shutil.rmtree(root)


def run_cli(test, *args, payload=None):
    return subprocess.run(
        [sys.executable, SCRIPT, *map(str, args)],
        cwd=os.environ["GOAL_CANDIDATE"],
        env=test.env,
        input=None if payload is None else json.dumps(payload),
        capture_output=True,
        text=True,
        timeout=120,
    )


def successful_cli(test, *args, payload=None):
    result = run_cli(test, *args, payload=payload)
    test.assertEqual(
        result.returncode,
        0,
        f"{args[0]} failed\nstdout:\n{result.stdout}\nstderr:\n{result.stderr}",
    )
    return result


def build_publication(test):
    test.tmp = Path(tempfile.mkdtemp(prefix="session-read-", dir="/tmp")).resolve()
    test.addCleanup(remove_tree, test.tmp)
    candidate = Path(os.environ["GOAL_CANDIDATE"]).resolve()
    test.assertNotIn(candidate, (test.tmp, *test.tmp.parents))

    test.staging = test.tmp / "staging"
    home = test.tmp / "home"
    home.mkdir()
    bin_dir = test.tmp / "bin"
    bin_dir.mkdir()
    scanner = bin_dir / "gitleaks"
    scanner.write_text(
        f"#!{sys.executable}\n"
        "import pathlib\n"
        "import sys\n"
        "args = sys.argv[1:]\n"
        "if args == ['version']:\n"
        "    print('8.30.1')\n"
        "    sys.exit(0)\n"
        "if args and args[0] == 'dir':\n"
        "    if '--report-path' in args:\n"
        "        report = args[args.index('--report-path') + 1]\n"
        "        pathlib.Path(report).write_text('[]', encoding='utf-8')\n"
        "    sys.exit(0)\n"
        "sys.exit(2)\n",
        encoding="utf-8",
    )
    scanner.chmod(0o755)

    test.env = os.environ.copy()
    for name in ("GITHUB_TOKEN", "GSTACK_PEER_REVIEW_DIR"):
        test.env.pop(name, None)
    test.env.update(
        SESSION_RECORD_STAGING=str(test.staging),
        SESSION_RECORD_SETTLE="0.05",
        SESSION_RECORD_WAIT="1",
        SESSION_RECORD_GITLEAKS_VERSION="8.30.1",
        HOME=str(home),
        TMPDIR=str(test.tmp),
        PYTHONDONTWRITEBYTECODE="1",
        PATH=str(bin_dir) + os.pathsep + os.environ.get("PATH", os.defpath),
    )

    transcript = test.tmp / f"{SID}.jsonl"
    rows = [
        {
            "type": "user",
            "promptId": "p1",
            "timestamp": "2026-10-03T10:00:00Z",
            "message": {"role": "user", "content": "work"},
        },
        {
            "type": "assistant",
            "timestamp": "2026-10-03T10:00:01Z",
            "message": {
                "role": "assistant",
                "content": [{"type": "text", "text": "done"}],
            },
        },
    ]
    transcript.write_text(
        "".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8"
    )
    successful_cli(
        test,
        "hook-stop",
        payload={
            "hook_event_name": "Stop",
            "session_id": SID,
            "prompt_id": "p1",
            "last_assistant_message": "done",
        },
    )
    successful_cli(
        test, "capture", "--transcript", transcript, "--session-id", SID
    )
    test.capture = test.staging / "session-records" / SID / "capture"
    prompt = successful_cli(test, "review-prompt", "--capture", test.capture)
    match = re.search(r"^prompt_sha256=([0-9a-f]{64})$", prompt.stderr, re.M)
    test.assertIsNotNone(match, prompt.stderr)

    evidence = (test.capture / "evidence.jsonl").read_text(encoding="utf-8")
    event_id = json.loads(evidence.splitlines()[0])["event_id"]
    citation = "ev:" + event_id[:12]
    draft = test.staging / "drafts" / "d1"
    draft.mkdir(parents=True)
    sections = []
    for number, title in enumerate(SECTIONS, 1):
        body = f"Nothing to report. {citation}"
        if number == 1:
            body += f"\n\n{DISTINCTIVE} {citation}"
        sections.append(f"## {number}. {title}\n\n{body}")
    (draft / "review.md").write_text(
        "\n\n".join(sections) + "\n", encoding="utf-8"
    )
    proposal = {
        "proposal_id": "P1",
        "evidence_event_ids": [citation],
        "classification": "check",
        "scope": "session review",
        "expected_benefit": "Retain the completed session review.",
        "risk": "low",
        "reversibility": "easy",
        "owner": "Dorian",
    }
    (draft / "proposals.jsonl").write_text(
        json.dumps(proposal) + "\n", encoding="utf-8"
    )
    (draft / "observed.jsonl").write_text("", encoding="utf-8")
    finalized = successful_cli(
        test,
        "review-finalize",
        "--capture", test.capture,
        "--draft", draft,
        "--prompt-sha256", match.group(1),
        "--tool", "claude",
        "--model", "m",
        "--family", "anthropic",
    )
    review = json.loads(finalized.stdout)
    test.assertEqual(review["validation_status"], "valid", finalized.stdout)
    prepared = successful_cli(
        test,
        "publish-prepare",
        "--capture", test.capture,
        "--review", review["review"],
        "--audience", "Dorian",
    )
    preparation = json.loads(prepared.stdout)
    test.publication_id = preparation["publication_id"]
    test.assertRegex(test.publication_id, r"^\d{8}-\d{6}-[0-9a-f]{6}$")
    publication = test.capture.parent / "publications" / test.publication_id
    test.vault = test.tmp / "vault"
    published = successful_cli(
        test,
        "publish",
        "--publication", publication,
        "--confirm", preparation["approval_digest"],
        "--confirmed-by", "dorianatmoxywolf",
        "--dest", test.vault,
    )
    test.published = test.vault / f"{SID}-{test.publication_id}"
    test.assertEqual(json.loads(published.stdout)["published"], str(test.published))
    test.assertTrue(test.published.is_dir())
    test.assertIn(
        DISTINCTIVE,
        (test.published / "review" / "review.md").read_text(encoding="utf-8"),
    )


class Read(unittest.TestCase):
    def setUp(self):
        build_publication(self)

    def test_prints_the_published_review_after_staging_is_gone(self):
        """Scenario: Given a review published from a session, when the session's staging folder is gone, then read prints the review from the published folder"""
        remove_tree(self.staging)
        self.assertFalse(self.staging.exists())

        result = run_cli(self, "read", self.published)

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn(DISTINCTIVE, result.stdout)
        self.assertIn(self.publication_id, result.stdout)

    def test_never_prints_a_changed_publication(self):
        """Scenario: A published folder whose files changed after publishing being printed as the review must never happen"""
        review = self.published / "review" / "review.md"
        review.chmod(0o600)
        with review.open("a", encoding="utf-8") as stream:
            stream.write("\n" + APPENDED + "\n")
        remove_tree(self.staging)

        result = run_cli(self, "read", self.published)

        self.assertNotEqual(result.returncode, 0, result.stderr)
        self.assertNotIn(DISTINCTIVE, result.stdout)
        self.assertNotIn(APPENDED, result.stdout)


if __name__ == "__main__":
    unittest.main()
