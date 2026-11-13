# drafted-by: gpt/gpt-6-astra
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import unittest


ORIGINAL_LINT = "plugins/4d-blog-engine/scripts/prose_lint.py"
ACADEMIC_LINT = "plugins/academic-pipeline/scripts/prose_lint.py"
SOCIAL_SCORE = "plugins/4d-blog-engine/scripts/social_score.py"

CLEAN_POST = (
    "The evidence was missing.\n\n"
    "We checked again.\n\n"
    "A reviewer traced the disputed mapping to a missing source paragraph. "
    "During the next review, she attached the passage and recorded why the "
    "proposed match did not satisfy the published requirement. "
    "The record includes the question, the document version, and the evidence "
    "available when the decision was made.\n\n"
    "Another reviewer can inspect those materials without repeating the "
    "original search or asking the author to reconstruct the discussion. "
    "If a later edition changes the requirement, the team can identify which "
    "decisions need another look and retain the earlier explanation alongside "
    "the revision. "
    "We used this process on the last batch of mappings and found two cases "
    "that needed additional source material before review could continue."
)

FLAGGED_TEXT = (
    "Teams propose and vote. Signed rule cards decide. "
    "A reviewer rules on what the cards can’t settle. "
    "Here's where the record explains how the panel reached its decision.\n\n"
    + CLEAN_POST
)

SEVERE_TEXT = (
    "We leverage robust synergy to utilize this system.\n\n" + FLAGGED_TEXT
)


def run_program(script, text, *, social=False, longform=False):
    """Run the public CLI with all inputs and reports outside the checkout."""
    candidate = os.environ["GOAL_CANDIDATE"]
    with tempfile.TemporaryDirectory(prefix="shared-lint-goal-") as directory:
        folder = Path(directory)
        source = folder / "input.md"
        report = folder / "report.md"
        source.write_text(text, encoding="utf-8")

        command = [sys.executable, script]
        if social:
            command.extend(["--file", str(source), "--type", "post"])
        else:
            command.extend([
                str(source),
                "--report",
                "--longform" if longform else "--no-longform",
            ])
        command.extend(["--out", str(report)])

        process = subprocess.run(
            command,
            cwd=candidate,
            stdin=subprocess.DEVNULL,
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=120,
            env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
        )
        sidecar = report.with_suffix(".json")
        result = (
            json.loads(sidecar.read_text(encoding="utf-8"))
            if sidecar.is_file()
            else None
        )
        markdown = (
            report.read_text(encoding="utf-8") if report.is_file() else ""
        )
        return process, result, markdown


def diagnostics(process):
    return (
        f"Exit code: {process.returncode}\n"
        f"stdout:\n{process.stdout}\n"
        f"stderr:\n{process.stderr}"
    )


class SharedLint(unittest.TestCase):
    def test_academic_copy_reports_run_and_here_opener(self):
        """Outcome.
        Scenario: Given an abstract with three short same-shape sentences in a row and a "Here's where" opener, when the academic pipeline's copy of the lint runs on it, then it reports a parallel_run and a here_opener finding
        """
        process, result, markdown = run_program(ACADEMIC_LINT, FLAGGED_TEXT)
        self.assertEqual(process.returncode, 0, diagnostics(process))
        self.assertIsInstance(result, dict, diagnostics(process))
        self.assertIs(result["longform"], False)

        findings = {
            (finding["rule"], finding["severity"])
            for finding in result["findings"]
        }
        self.assertIn(("parallel_run", "Medium"), findings)
        self.assertIn(("here_opener", "Minor"), findings)
        self.assertIn("parallel_run", markdown)
        self.assertIn("here_opener", markdown)

    def test_social_score_reports_lint_findings_and_fails(self):
        """Outcome.
        Scenario: Given the same text as a LinkedIn post, when social_score.py checks it, then it reports the parallel_run and here_opener findings by rule id and fails the check
        """
        # This fixture passes today's format checks. Its original lint grade
        # is A, so social enforcement must inspect severity, not lint exit code.
        process, _, _ = run_program(
            SOCIAL_SCORE, FLAGGED_TEXT, social=True
        )
        self.assertEqual(process.returncode, 1, diagnostics(process))

        heading = re.search(
            r"(?im)^.*\bProse lint\b.*$", process.stdout
        )
        self.assertIsNotNone(heading, diagnostics(process))
        lint_lines = process.stdout[heading.end():].splitlines()

        matched_lines = []
        for rule, severity in (
            ("parallel_run", "Medium"),
            ("here_opener", "Minor"),
        ):
            with self.subTest(rule=rule):
                matches = [
                    index
                    for index, line in enumerate(lint_lines)
                    if re.search(rf"\b{re.escape(rule)}\b", line)
                    and re.search(rf"\b{severity}\b", line, re.IGNORECASE)
                ]
                self.assertEqual(
                    len(matches), 1,
                    f"Expected one finding line for {rule} ({severity}).\n"
                    + diagnostics(process),
                )
                matched_lines.append(matches[0])
        self.assertNotEqual(
            matched_lines[0],
            matched_lines[1],
            "Each lint finding must have its own report line.",
        )

    def test_original_lint_grades_fixed_text_as_today(self):
        """Invariant.
        Scenario: The 4d-blog-engine lint grading a fixed text differently from how it grades it today must never happen
        """
        # Literal baseline expectations; never derive them from another copy.
        cases = (
            (
                "clean",
                CLEAN_POST,
                False,
                0,
                ("A", 0, 0, 0),
                [],
            ),
            (
                "short-form findings",
                FLAGGED_TEXT,
                False,
                0,
                ("A", 3, 0, 2),
                [("here_opener", "Minor"), ("parallel_run", "Medium")],
            ),
            (
                "long-form allowance",
                FLAGGED_TEXT,
                True,
                0,
                ("A", 1, 0, 1),
                [("here_opener", "Minor")],
            ),
            (
                "failing grade",
                SEVERE_TEXT,
                False,
                1,
                ("F", 15, 4, 6),
                [
                    ("banned_word:leverage", "Major"),
                    ("banned_word:robust", "Major"),
                    ("banned_word:synergy", "Major"),
                    ("banned_word:utilize", "Major"),
                    ("here_opener", "Minor"),
                    ("parallel_run", "Medium"),
                ],
            ),
        )

        for name, text, longform, exit_code, baseline, findings in cases:
            with self.subTest(case=name):
                process, result, markdown = run_program(
                    ORIGINAL_LINT, text, longform=longform
                )
                self.assertEqual(
                    process.returncode, exit_code, diagnostics(process)
                )
                self.assertIsInstance(result, dict, diagnostics(process))
                self.assertEqual(
                    (
                        result["grade"],
                        result["score"],
                        result["majors"],
                        result["total_findings"],
                    ),
                    baseline,
                )
                self.assertIs(result["longform"], longform)
                self.assertCountEqual(
                    [
                        (finding["rule"], finding["severity"])
                        for finding in result["findings"]
                    ],
                    findings,
                )
                grade, score, majors, count = baseline
                self.assertIn(
                    f"STATUS=scanned GRADE={grade} SCORE={score} "
                    f"FINDINGS={count} MAJORS={majors}",
                    process.stdout,
                )
                self.assertIn(f"**Grade:** {grade}", markdown)

    def test_social_score_passes_clean_post_as_today(self):
        """Invariant.
        Scenario: social_score.py failing a clean post that passes its format checks today must never happen
        """
        process, result, _ = run_program(
            SOCIAL_SCORE, CLEAN_POST, social=True
        )
        self.assertEqual(process.returncode, 0, diagnostics(process))
        self.assertIn("STATUS=pass TYPE=post", process.stdout)
        self.assertIsInstance(result, dict, diagnostics(process))
        self.assertIs(result["passed"], True)
        self.assertEqual(result["type"], "post")
        self.assertEqual(result["metrics"]["char_count"], 789)
        self.assertEqual(result["metrics"]["word_count"], 121)
        self.assertEqual(result["metrics"]["hashtag_count"], 0)
        self.assertIs(result["metrics"]["hook_position"]["passed"], True)
        self.assertCountEqual(
            [
                (finding["rule"], finding["severity"])
                for finding in result["findings"]
            ],
            [("outside_sweet_spot", "Minor")],
        )


if __name__ == "__main__":
    unittest.main()
