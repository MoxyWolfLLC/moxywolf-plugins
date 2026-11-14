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
SUITE_RUNNER = "plugins/gstack-execution/scripts/run_all_tests.py"

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

PARALLEL_RUN = (
    "Teams propose and vote. Signed rule cards decide. "
    "A reviewer rules on what the cards can’t settle. "
    "Every output keeps the exact question it answered and the evidence "
    "it saw along the way."
)

CLOSING_ZINGER = (
    "The method treats a missing match as a voted and gated result instead "
    "of silence. It also measures the links that were missed across every "
    "batch it runs. Most tools skip it."
)

SIGNATURE_TEXT = (
    "It is not a guess about the outcome, but a record of the vote and "
    "the evidence behind it.\n\n" + CLEAN_POST
)

SIGNATURE_DEVICES = ["contrast-framing", "three-beat-reveal"]


def diagnostics(process):
    return (
        f"Exit code: {process.returncode}\n"
        f"stdout:\n{process.stdout}\n"
        f"stderr:\n{process.stderr}"
    )


class Holdout(unittest.TestCase):
    def invoke(self, script, arguments, timeout=120):
        return subprocess.run(
            [sys.executable, "-B", script, *map(str, arguments)],
            cwd=os.environ["GOAL_CANDIDATE"],
            stdin=subprocess.DEVNULL,
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=timeout,
            env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
        )

    def run_text(self, script, text, *, post_type=None, longform=False):
        with tempfile.TemporaryDirectory(prefix="holdout prose ") as directory:
            folder = Path(directory)
            source = folder / "input prose.md"
            report = folder / "report.md"
            source.write_text(text, encoding="utf-8")

            if post_type is not None:
                arguments = [
                    "--file", source, "--type", post_type, "--out", report,
                ]
            else:
                arguments = [
                    source,
                    "--report",
                    "--longform" if longform else "--no-longform",
                    "--signature-devices", ",".join(SIGNATURE_DEVICES),
                    "--out", report,
                ]

            process = self.invoke(script, arguments)
            self.assertTrue(report.is_file(), diagnostics(process))
            sidecar = report.with_suffix(".json")
            self.assertTrue(sidecar.is_file(), diagnostics(process))
            result = json.loads(sidecar.read_text(encoding="utf-8"))
            markdown = report.read_text(encoding="utf-8")
            self.assertEqual(source.read_text(encoding="utf-8"), text)
            return process, result, markdown

    def assert_lint_lines(self, process, expected):
        heading = re.search(r"(?im)^.*\bProse lint\b.*$", process.stdout)
        self.assertIsNotNone(heading, diagnostics(process))
        lines = process.stdout[heading.end():].splitlines()
        occupied = set()

        for rule, severity, count in expected:
            matches = [
                index
                for index, line in enumerate(lines)
                if re.search(
                    rf"(?<![\w:]){re.escape(rule)}(?![\w:])", line
                )
                and re.search(rf"\b{severity}\b", line, re.IGNORECASE)
            ]
            self.assertEqual(
                len(matches), count,
                f"Expected {count} separate {rule} ({severity}) lines.\n"
                + diagnostics(process),
            )
            self.assertTrue(
                occupied.isdisjoint(matches),
                "Different findings must appear on different lines.\n"
                + diagnostics(process),
            )
            occupied.update(matches)

    def test_minor_findings_are_printed_without_holding_the_post(self):
        cases = (
            (
                "closing zinger",
                CLEAN_POST + "\n\n" + CLOSING_ZINGER,
                [("closing_zinger", "Minor", 1)],
            ),
            (
                "curly here opener",
                CLEAN_POST
                + "\n\nHere’s where the reviewer recorded the evidence used "
                "to settle the disputed mapping.",
                [("here_opener", "Minor", 1)],
            ),
            (
                "six separate Minor findings",
                CLEAN_POST.replace(" ", "; ", 6),
                [("semicolon", "Minor", 6)],
            ),
        )

        for name, text, expected in cases:
            with self.subTest(case=name):
                process, result, _ = self.run_text(
                    SOCIAL_SCORE, text, post_type="post"
                )
                # Six Minors give the standalone lint an F. Social gating
                # must inspect severity instead of propagating that exit code.
                self.assertEqual(process.returncode, 0, diagnostics(process))
                self.assertEqual(process.stderr, "", diagnostics(process))
                self.assertIn("STATUS=pass TYPE=post", process.stdout)
                self.assertIs(result["passed"], True)
                self.assert_lint_lines(process, expected)

    def test_social_lint_covers_other_rules_types_and_long_articles(self):
        major_post = CLEAN_POST.replace(
            "The evidence", "The vibrant evidence", 1
        )
        hidden_post = CLEAN_POST.replace("evidence", "evi\u200bdence", 1)
        article = PARALLEL_RUN + "\n\n" + "\n\n".join([CLEAN_POST] * 8)
        thread = (
            "## Post 1\n"
            "The vibrant evidence was missing. We checked again.\n\n"
            "## Post 2\n"
            "A reviewer traced the disputed mapping to a missing source "
            "paragraph and attached the passage to the review record.\n\n"
            "## Post 3\n"
            "Another reviewer can inspect those materials without repeating "
            "the original search or asking the author to reconstruct "
            "the discussion."
        )
        cases = (
            (
                "Major despite an A lint grade",
                "post", major_post,
                [("banned_word:vibrant", "Major", 1)],
            ),
            (
                "Medium outside the goal fixture",
                "post", hidden_post,
                [("hidden_unicode", "Medium", 1)],
            ),
            (
                "Facebook",
                "facebook-post", major_post,
                [("banned_word:vibrant", "Major", 1)],
            ),
            (
                "first comment",
                "first-comment",
                major_post + "\n\nhttps://example.invalid/evidence",
                [("banned_word:vibrant", "Major", 1)],
            ),
            (
                "Twitter",
                "twitter-thread", thread,
                [("banned_word:vibrant", "Major", 1)],
            ),
            (
                "article above automatic long-form threshold",
                "article", article,
                [
                    ("parallel_run", "Medium", 1),
                    ("ttr_low", "Medium", 1),
                ],
            ),
        )

        for name, post_type, text, expected in cases:
            with self.subTest(case=name):
                process, result, _ = self.run_text(
                    SOCIAL_SCORE, text, post_type=post_type
                )
                self.assertEqual(process.returncode, 1, diagnostics(process))
                self.assertEqual(process.stderr, "", diagnostics(process))
                self.assertIn(
                    f"STATUS=fail TYPE={post_type}", process.stdout
                )
                self.assertIs(result["passed"], False)
                self.assert_lint_lines(process, expected)
                if post_type == "article":
                    self.assertNotIn(
                        "standalone_oneliners_high", process.stdout,
                        "Social articles must not acquire long-form rules.",
                    )

    def test_format_verdicts_and_missing_file_streams_are_preserved(self):
        cases = (
            ("post", CLEAN_POST, 0, True, None),
            (
                "post",
                CLEAN_POST + "\n\n#review #records #audit #sources",
                0, True, ("hashtag_count", "Medium"),
            ),
            (
                "article", CLEAN_POST,
                1, False, ("length_out_of_band", "Major"),
            ),
        )
        for post_type, text, exit_code, passed, finding in cases:
            with self.subTest(post_type=post_type, finding=finding):
                process, result, _ = self.run_text(
                    SOCIAL_SCORE, text, post_type=post_type
                )
                self.assertEqual(
                    process.returncode, exit_code, diagnostics(process)
                )
                self.assertEqual(process.stderr, "", diagnostics(process))
                self.assertIs(result["passed"], passed)
                verdict = "pass" if passed else "fail"
                self.assertIn(
                    f"STATUS={verdict} TYPE={post_type}", process.stdout
                )
                if finding is not None:
                    self.assertIn(
                        finding,
                        [
                            (item["rule"], item["severity"])
                            for item in result["findings"]
                        ],
                    )

        with tempfile.TemporaryDirectory(prefix="holdout missing ") as directory:
            missing = Path(directory) / "absent post.md"
            report = Path(directory) / "report.md"
            for script in (SOCIAL_SCORE, ORIGINAL_LINT, ACADEMIC_LINT):
                with self.subTest(missing_file_script=script):
                    arguments = (
                        ["--file", missing, "--type", "post", "--out", report]
                        if script == SOCIAL_SCORE
                        else [missing, "--report", "--out", report]
                    )
                    process = self.invoke(script, arguments)
                    self.assertEqual(
                        process.returncode, 2, diagnostics(process)
                    )
                    self.assertEqual(process.stdout, "", diagnostics(process))
                    self.assertEqual(
                        process.stderr,
                        f"ERROR: file not found: {missing}\n",
                    )
                    self.assertFalse(report.exists())
                    self.assertFalse(report.with_suffix(".json").exists())

    def test_academic_and_original_preserve_grade_boundaries_and_voice_flags(self):
        grade_c = (
            (PARALLEL_RUN + "\n\n" + CLEAN_POST)
            .replace("The evidence", "The robust evidence\u200b")
            .replace(",", ";", 1)
        )
        cases = (
            ("A", CLEAN_POST, False, 0, "A", 0, 0, []),
            (
                "B", CLEAN_POST.replace(" ", "; ", 4),
                False, 0, "B", 4, 0, [("semicolon", "Minor")] * 4,
            ),
            (
                "C", grade_c, False, 0, "C", 8, 1,
                [
                    ("banned_word:robust", "Major"),
                    ("semicolon", "Minor"),
                    ("hidden_unicode", "Medium"),
                    ("parallel_run", "Medium"),
                ],
            ),
            (
                "D",
                CLEAN_POST.replace(
                    "The evidence", "The robust seamless evidence"
                ),
                True, 1, "D", 6, 2,
                [
                    ("banned_word:robust", "Major"),
                    ("banned_word:seamless", "Major"),
                ],
            ),
            (
                "F",
                CLEAN_POST.replace(
                    "The evidence", "The robust seamless vibrant evidence"
                ),
                True, 1, "F", 10, 3,
                [
                    ("banned_word:robust", "Major"),
                    ("banned_word:seamless", "Major"),
                    ("banned_word:vibrant", "Major"),
                    ("burstiness_drifting", "Minor"),
                ],
            ),
            (
                "F from Minors",
                CLEAN_POST.replace(" ", "; ", 6),
                False, 1, "F", 6, 0, [("semicolon", "Minor")] * 6,
            ),
            (
                "long-form allowance",
                PARALLEL_RUN + "\n\n" + CLEAN_POST,
                True, 0, "A", 0, 0, [],
            ),
            (
                "declared voice",
                SIGNATURE_TEXT,
                True, 0, "A", 0, 0, [],
            ),
        )

        for script in (ORIGINAL_LINT, ACADEMIC_LINT):
            for (
                name, text, longform, exit_code, grade, score, majors, findings
            ) in cases:
                with self.subTest(script=script, case=name):
                    process, result, markdown = self.run_text(
                        script, text, longform=longform
                    )
                    self.assertEqual(
                        process.returncode, exit_code, diagnostics(process)
                    )
                    self.assertEqual(process.stderr, "", diagnostics(process))
                    self.assertEqual(
                        (
                            result["grade"],
                            result["score"],
                            result["majors"],
                            result["total_findings"],
                        ),
                        (grade, score, majors, len(findings)),
                    )
                    self.assertIs(result["longform"], longform)
                    self.assertEqual(
                        result["signature_devices"], SIGNATURE_DEVICES
                    )
                    self.assertCountEqual(
                        [
                            (item["rule"], item["severity"])
                            for item in result["findings"]
                        ],
                        findings,
                    )
                    self.assertIn(
                        f"STATUS=scanned GRADE={grade} SCORE={score} "
                        f"FINDINGS={len(findings)} MAJORS={majors} "
                        f"LONGFORM={'yes' if longform else 'no'}",
                        process.stdout,
                    )
                    self.assertIn(f"**Grade:** {grade}", markdown)
                    if name == "declared voice":
                        self.assertEqual(
                            [
                                (
                                    item["device"],
                                    item["count"],
                                    item["declared_signature"],
                                )
                                for item in result["advisories"]
                            ],
                            [("contrast-framing", 1, True)],
                        )

    def test_repository_runner_executes_both_required_suites(self):
        # Execute the repository's public runner. The holdout does not
        # inspect, import, copy, or mutate candidate checkout files.
        for root, required_suite in (
            ("plugins/4d-blog-engine", "test_social_score.py"),
            ("plugins/academic-pipeline", "test_prose_lint_copy.py"),
        ):
            with self.subTest(root=root):
                process = self.invoke(
                    SUITE_RUNNER, ["--root", root], timeout=600
                )
                self.assertEqual(process.returncode, 0, diagnostics(process))
                self.assertRegex(
                    process.stdout,
                    rf"(?m)^PASS\s+(?:[^\r\n]*/)?"
                    rf"{re.escape(required_suite)}\s*$",
                )
                self.assertRegex(
                    process.stdout,
                    r"(?m)^examined [1-9]\d* checks: "
                    r"[1-9]\d* passed, 0 failed\s*$",
                )
                self.assertNotRegex(process.stdout, r"(?m)^FAIL\b")


if __name__ == "__main__":
    unittest.main()
