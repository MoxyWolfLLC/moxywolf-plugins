import base64
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
import unittest


SKILLS = {
    "finance": """
        budgeting-and-forecasting capital-allocation
        capital-structure-and-covenants chief-financial-officer
        cost-accounting financial-modeling financial-reporting-and-close
        financial-statement-analysis internal-controls-and-audit
        revenue-recognition tax treasury-and-liquidity unit-economics
    """.split(),
    "people": """
        benefits-and-leave chief-human-resources-officer
        compensation-and-leveling employee-relations employment-compliance
        hiring-and-interviewing learning-and-development
        onboarding-and-offboarding org-design payroll-operations
        performance-management workforce-planning
    """.split(),
    "it-operations": """
        backup-and-recovery chief-information-officer cloud-administration
        collaboration-platform-administration endpoint-management
        identity-lifecycle-administration it-asset-management
        network-administration service-desk systems-administration
        telephony-and-conferencing virtualization-operations
    """.split(),
    "security": """
        access-and-identity chief-information-security-officer
        data-protection-and-encryption detection-and-monitoring
        incident-response security-architecture-review threat-modeling
        vulnerability-management
    """.split(),
    "pmo": """
        benefits-realization change-and-adoption dependency-and-risk-management
        estimating-and-contingency head-of-pmo portfolio-governance
        program-management project-delivery schedule-development-and-analysis
    """.split(),
    "operations": """
        business-continuity-and-resilience capacity-and-demand-planning
        chief-operating-officer facilities-and-workplace incident-management
        operating-cadence process-design procurement-and-sourcing
        quality-management service-level-management supply-chain-and-logistics
        vendor-management
    """.split(),
    "corporate-strategy": """
        chief-strategy-officer market-entry mergers-and-acquisitions
        portfolio-strategy scenario-planning strategic-alliances
    """.split(),
    "customer-experience": """
        chief-customer-officer customer-onboarding-and-implementation
        customer-success-management escalation-management
        self-service-and-knowledge support-operations voice-of-customer
    """.split(),
}

WITHOUT_SOURCES = {
    ("it-operations", "service-desk"),
    ("operations", "chief-operating-officer"),
    ("operations", "operating-cadence"),
    ("corporate-strategy", "scenario-planning"),
    ("corporate-strategy", "strategic-alliances"),
    ("customer-experience", "chief-customer-officer"),
    ("customer-experience", "customer-success-management"),
    ("customer-experience", "voice-of-customer"),
}

EXCLUDED_DEPARTMENTS = """
    executive technology marketing demand-generation revenue product
    data-analytics legal-risk
""".split()

UPSTREAM_DESCRIPTIONS = {
    "finance": (
        "Financial modeling, budgeting and forecasting, unit economics, "
        "and financial decision support."
    ),
    "people": (
        "Org design, hiring and interviewing, compensation and leveling, "
        "and workforce planning."
    ),
    "it-operations": (
        "Corporate IT: service desk, systems and network administration, "
        "virtualization and cloud, telephony and conferencing, endpoints, "
        "assets, identity lifecycle, and backup and recovery."
    ),
    "security": (
        "Threat modeling, security architecture review, incident response, "
        "vulnerability management, and access and identity. Reviewer-class: "
        "blocking findings are not overrulable by the department under review."
    ),
    "pmo": (
        "Enterprise program management office: portfolio governance, program "
        "and project delivery, dependencies and delivery risk, benefits "
        "realization, and adoption."
    ),
    "operations": (
        "Program management, process design, vendor and supplier management, "
        "and operational delivery."
    ),
    "corporate-strategy": (
        "Portfolio strategy, corporate development, strategic alliances, "
        "and scenario planning."
    ),
    "customer-experience": (
        "Support operations, escalation management, voice of customer, "
        "and self-service. Owns what the customer experiences after the sale."
    ),
}

# Captured from cbrock84/headcount at
# 98d1c17d480f606060102a781f9a8601690685f7.
# Each digest covers sorted department-relative skill/source paths, with
# path UTF-8 bytes + NUL + original file bytes + NUL for each file.
UPSTREAM_DIGESTS = {
    "finance": "fc5ef611e4002b8ba9a9553b09ddaa0b6bc41d82e310ac77a980d2c469ac5c09",
    "people": "60a6a3dd4b2d5e84e74a82618f10c6be9d02e5be9122e56db21c48b3f05b151f",
    "it-operations": "7ea9eea50b43aab8d6f366e0475fe760e270089ad9854a0c5b94276dbe91f99d",
    "security": "169975bd43cbe70645327f07c5ad6b042428299ad1b462893a550b9dec3e5202",
    "pmo": "7c91b5d671cff0a700e6769c0ee620c53e653e9fcd1df87efae698f1206b8c42",
    "operations": "c7b29c6b367f031a3d7a4a4e791191fda1772a6165b28c6a7225a37fd9bb0b14",
    "corporate-strategy": "a2f02448d7a72b4076600296863ce2f8aa69058abcad4c910322381fc06238a4",
    "customer-experience": "ce35238694d9759ee25514d165607cbe0e7a6dddfb2c8e3872ae71f2290808f4",
}

LICENSE_SHA256 = (
    "2dec83f130fcd40ed46432c82f629ea8d2a061bca9ffa82ff5f584ae97723973"
)

QUOTED_DESCRIPTIONS = {
    "finance/skills/chief-financial-officer/SKILL.md",
    "people/skills/chief-human-resources-officer/SKILL.md",
    "operations/skills/chief-operating-officer/SKILL.md",
}

# Zero-based line positions and verbatim upstream lines. Only the backticked
# excluded-department references in these lines may become plain words.
REFERENCE_EDITS = {
    "finance/skills/internal-controls-and-audit/SKILL.md": {
        77: (
            "Related but distinct: `legal-risk:corporate-governance` "
            "owns board and entity governance,"
        ),
        78: (
            "`legal-risk:enterprise-risk` owns the risk framework. "
            "This skill owns controls over financial"
        ),
    },
    "finance/skills/revenue-recognition/SKILL.md": {
        46: (
            "Give `revenue:chief-revenue-officer` and "
            "`revenue:pricing-and-packaging` a small set of standard"
        ),
        48: (
            "alongside `legal-risk:contract-review`, which owns the legal "
            "exposure the same clauses create."
        ),
    },
    "finance/skills/tax/SKILL.md": {
        37: (
            "changes — see `revenue:pricing-and-packaging`, "
            "because bundling can change the answer."
        ),
    },
    "it-operations/skills/backup-and-recovery/SKILL.md": {
        41: (
            "directly. Settle it with `legal-risk:privacy-and-data-protection`."
        ),
    },
    "it-operations/skills/chief-information-officer/SKILL.md": {
        37: (
            "  `technology:cloud-infrastructure` designs the environment "
            "the product runs in. Where a corporate"
        ),
    },
    "it-operations/skills/cloud-administration/SKILL.md": {
        12: (
            "infrastructure as code, scaling, region failure — see "
            "`technology:cloud-infrastructure`. The two"
        ),
        42: (
            "`legal-risk:privacy-and-data-protection` describes, "
            "and a departing employee's access to it is"
        ),
    },
    "it-operations/skills/endpoint-management/SKILL.md": {
        45: (
            "and record what data was on it for "
            "`legal-risk:privacy-and-data-protection` to assess notification."
        ),
    },
    "it-operations/skills/systems-administration/SKILL.md": {
        10: (
            "Cloud environment design belongs to "
            "`technology:cloud-infrastructure`; this is operating the systems"
        ),
    },
    "it-operations/skills/telephony-and-conferencing/SKILL.md": {
        74: (
            "whether or not anyone chose it. "
            "`legal-risk:privacy-and-data-protection` owns the obligations; this"
        ),
    },
    "security/skills/chief-information-security-officer/SKILL.md": {
        58: (
            "`legal-risk:chief-legal-and-risk-officer`. "
            "The distinction preserves the finding rather than"
        ),
        88: (
            "`legal-risk:privacy-and-data-protection` "
            "for the obligations themselves."
        ),
    },
    "pmo/skills/dependency-and-risk-management/SKILL.md": {
        8: (
            "appetite and register at company level — is "
            "`legal-risk:enterprise-risk`, and the two should not be"
        ),
    },
    "operations/skills/facilities-and-workplace/SKILL.md": {
        30: "`legal-risk:contract-review` for the terms.",
    },
    "operations/skills/procurement-and-sourcing/SKILL.md": {
        54: (
            "Route the resulting terms through `legal-risk:contract-review`, "
            "and anything touching customer data"
        ),
        55: (
            "through `legal-risk:privacy-and-data-protection` "
            "before signature rather than after."
        ),
    },
    "operations/skills/service-level-management/SKILL.md": {
        40: (
            "with contractual teeth, `legal-risk:contract-review` "
            "owns the remedy language; this skill owns"
        ),
    },
    "corporate-strategy/skills/chief-strategy-officer/SKILL.md": {
        46: (
            "document. Hand the conclusion to `executive:chief-executive` "
            "for the capital call and"
        ),
    },
    "corporate-strategy/skills/strategic-alliances/SKILL.md": {
        2: (
            "description: Structures partnerships that change what the "
            "business can do — technology integrations, channel and reseller "
            "arrangements, joint ventures, and OEM relationships. Use this to "
            "evaluate or structure a strategic partnership, decide between "
            "partnering and building, negotiate commercial terms of an "
            "alliance, or diagnose a partnership that is signed but not "
            "producing. For audience-borrowing partnerships, use "
            "`marketing:partnership-marketing`."
        ),
    },
    "customer-experience/skills/customer-onboarding-and-implementation/SKILL.md": {
        44: "it, `technology:data-migration` covers the discipline.",
    },
    "customer-experience/skills/customer-success-management/SKILL.md": {
        8: (
            "churn analysis itself, see `revenue:retention`. "
            "The failure this discipline exists to prevent is"
        ),
    },
}

EXCLUDED_REFERENCE = re.compile(
    r"`(?:" + "|".join(EXCLUDED_DEPARTMENTS) + r"):[a-z0-9-]+`"
)

EXISTING_PLUGIN_NAMES = """
    4d-blog-engine academic-pipeline analytics bibtex-builder board-deck
    composio council daily-briefings daily-ops dev-infrastructure-skills
    document-analysis editorial-forge excalidraw-vault frontier-founder
    frontier-founder-smb github-repo-analyzer graphify gstack-execution mapping
    moxywolf-skills obsidian-skills obsidian-update ponytail product-orchestrator
    project-init email-lifecycle marcom-audit research-pipeline
    saas-frontend-designer saas-pricing-engine synergy-engine team-kanban
    understand-anything vault-code-learn vault-skills vtt-to-text
""".split()

EXISTING_ENTRIES_SHA256 = (
    "afcd8282ff7dd6dc3b59cf87e685b02a2efdf26e9a82264de229954dc2bd4e43"
)
EXISTING_PACKAGE_PATHS_SHA256 = (
    "7cf1fee973443be4f1b595556c9774755cd70674272eb3ebbbc583ea785fb4ec"
)

MARKETPLACE_METADATA = {
    "$schema": (
        "https://raw.githubusercontent.com/hesreallyhim/"
        "claude-code-json-schema/main/marketplace.schema.json"
    ),
    "name": "moxywolf-plugins",
    "description": (
        "Canonical MoxyWolf plugin marketplace. Hosts every plugin authored "
        "by MoxyWolf LLC plus a bundle of the standalone skills used across "
        "the team. Source of truth lives in the MoxyWolf Vault on Google Drive."
    ),
    "version": "1.117.0",
    "owner": {
        "name": "MoxyWolf LLC",
        "email": "dorianc@moxywolf.com",
    },
}

# File access occurs exclusively in this separate program. The unittest
# process receives bytes as base64 on stdout and never opens candidate files.
SNAPSHOT_PROGRAM = r"""
import base64
import json
import sys
from pathlib import Path

selected, excluded = json.loads(sys.argv[1])
result = {
    "marketplace": json.loads(
        Path(".claude-plugin/marketplace.json").read_bytes()
    ),
    "departments": {},
    "excluded": [],
}
for name in excluded:
    path = Path("plugins") / name
    if path.exists() or path.is_symlink():
        result["excluded"].append(name)
for name in selected:
    root = Path("plugins") / name
    files = {}
    directories = []
    symlinks = []
    if root.is_symlink():
        symlinks.append(".")
    if root.is_dir():
        for path in sorted(root.rglob("*")):
            relative = path.relative_to(root).as_posix()
            if path.is_symlink():
                symlinks.append(relative)
            elif path.is_file():
                files[relative] = base64.b64encode(
                    path.read_bytes()
                ).decode("ascii")
            elif path.is_dir():
                directories.append(relative)
    result["departments"][name] = {
        "files": files,
        "directories": directories,
        "symlinks": symlinks,
    }
print(json.dumps(result))
"""


def _run(case, arguments, timeout=120, ci=False):
    candidate = os.environ.get("GOAL_CANDIDATE")
    case.assertTrue(candidate, "GOAL_CANDIDATE must name the candidate checkout")
    with tempfile.TemporaryDirectory(prefix="department-holdout-") as scratch:
        environment = os.environ.copy()
        environment.update({
            "PYTHONDONTWRITEBYTECODE": "1",
            "TMPDIR": scratch,
            "TMP": scratch,
            "TEMP": scratch,
        })
        if ci:
            environment["CI"] = "true"
        try:
            return subprocess.run(
                [sys.executable, "-B", *arguments],
                cwd=candidate,
                env=environment,
                capture_output=True,
                text=True,
                encoding="utf-8",
                timeout=timeout,
            )
        except subprocess.TimeoutExpired:
            case.fail("Candidate command timed out: " + repr(arguments))


def _json_result(case, result):
    case.assertEqual(
        result.returncode,
        0,
        "Command failed:\n" + result.stdout + "\n" + result.stderr,
    )
    case.assertEqual(result.stderr, "", "Unexpected standard error")
    try:
        return json.loads(result.stdout)
    except ValueError as error:
        case.fail("Invalid JSON on standard output: %s\n%s" % (
            error, result.stdout,
        ))


def _snapshot(case):
    return _json_result(case, _run(case, [
        "-c",
        SNAPSHOT_PROGRAM,
        json.dumps([list(SKILLS), EXCLUDED_DEPARTMENTS]),
    ]))


def _file_bytes(case, department, relative):
    files = department["files"]
    case.assertIn(relative, files, "Missing required file: " + relative)
    return base64.b64decode(files[relative], validate=True)


def _fingerprint(value):
    serialized = json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    )
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def _skill_files(department):
    paths = set()
    for skill in SKILLS[department]:
        paths.add("skills/%s/SKILL.md" % skill)
        if (department, skill) not in WITHOUT_SOURCES:
            paths.add("skills/%s/references/sources.md" % skill)
    return paths


def _restore_permitted_edits(case, path, data):
    """Reconstruct upstream only after validating each permitted edit."""
    text = data.decode("utf-8")
    case.assertIsNone(
        EXCLUDED_REFERENCE.search(text),
        "Unconverted reference to an excluded department in " + path,
    )
    lines = text.splitlines(keepends=True)

    if path in QUOTED_DESCRIPTIONS:
        case.assertGreater(len(lines), 2, "Truncated skill: " + path)
        line = lines[2]
        case.assertTrue(
            line.startswith('description: "') and line.endswith('"\n'),
            "Colon-space description must be double quoted: " + path,
        )
        try:
            value = json.loads(line[len("description: "):].rstrip("\n"))
        except ValueError as error:
            case.fail("Invalid quoted description in %s: %s" % (path, error))
        case.assertIsInstance(value, str)
        lines[2] = "description: " + value + "\n"

    for index, original in REFERENCE_EDITS.get(path, {}).items():
        case.assertGreater(len(lines), index, "Truncated skill: " + path)
        original += "\n"
        pieces = []
        position = 0
        references = list(EXCLUDED_REFERENCE.finditer(original))
        for reference in references:
            pieces.append(re.escape(original[position:reference.start()]))
            # Accept different plain-English function names without accepting
            # backticks, colon addresses, links, or new Markdown structures.
            pieces.append(r"([A-Za-z][A-Za-z0-9 &'’(),.\-]*?)")
            position = reference.end()
        pieces.append(re.escape(original[position:]))
        match = re.fullmatch("".join(pieces), lines[index])
        case.assertIsNotNone(
            match,
            "Only the excluded skill address may change at %s:%d"
            % (path, index + 1),
        )
        for replacement in match.groups():
            case.assertTrue(
                replacement.strip(),
                "An excluded reference must become a named function",
            )
        lines[index] = original

    return "".join(lines).encode("utf-8")


class Holdout(unittest.TestCase):
    def test_upstream_content_and_exact_import_payload(self):
        snapshot = _snapshot(self)
        self.assertEqual(
            snapshot["excluded"], [],
            "An excluded headcount department landed in the checkout",
        )
        self.assertEqual(sum(map(len, SKILLS.values())), 79)

        for department in SKILLS:
            with self.subTest(department=department):
                data = snapshot["departments"][department]
                self.assertEqual(data["symlinks"], [], "Imports must be copies")
                for directory in data["directories"]:
                    self.assertNotIn(
                        ".codex-plugin", directory.split("/"),
                        "A Codex manifest directory was copied",
                    )

                expected_skills = _skill_files(department)
                expected_payload = expected_skills | {
                    ".claude-plugin/plugin.json",
                    "README.md",
                    "LICENSE",
                    "agents/%s.md" % department,
                }
                self.assertEqual(
                    set(data["files"]),
                    expected_payload,
                    "Missing content or unplanned files in " + department,
                )

                digest = hashlib.sha256()
                for relative in sorted(expected_skills):
                    content = _file_bytes(self, data, relative)
                    restored = _restore_permitted_edits(
                        self, department + "/" + relative, content
                    )
                    digest.update(relative.encode("utf-8") + b"\0")
                    digest.update(restored + b"\0")
                self.assertEqual(
                    digest.hexdigest(),
                    UPSTREAM_DIGESTS[department],
                    "Skill/source content differs from 98d1c17 beyond "
                    "the two permitted edits: " + department,
                )

    def test_attribution_descriptions_and_marketplace_preservation(self):
        snapshot = _snapshot(self)
        marketplace = snapshot["marketplace"]
        self.assertEqual(
            {key: value for key, value in marketplace.items()
             if key != "plugins"},
            MARKETPLACE_METADATA,
        )
        entries = marketplace["plugins"]
        names = [entry["name"] for entry in entries]
        self.assertEqual(len(names), len(set(names)))
        self.assertEqual(
            set(names), set(EXISTING_PLUGIN_NAMES) | set(SKILLS)
        )
        existing = [
            entry for entry in entries
            if entry["name"] in EXISTING_PLUGIN_NAMES
        ]
        self.assertEqual(
            [entry["name"] for entry in existing], EXISTING_PLUGIN_NAMES
        )
        self.assertEqual(_fingerprint(existing), EXISTING_ENTRIES_SHA256)
        by_name = {entry["name"]: entry for entry in entries}

        for department, skills in SKILLS.items():
            with self.subTest(department=department):
                data = snapshot["departments"][department]
                self.assertEqual(
                    hashlib.sha256(
                        _file_bytes(self, data, "LICENSE")
                    ).hexdigest(),
                    LICENSE_SHA256,
                    "MIT notice must be verbatim, including Chris Brock's "
                    "copyright line",
                )
                manifest = json.loads(_file_bytes(
                    self, data, ".claude-plugin/plugin.json"
                ))
                self.assertEqual(manifest.get("name"), department)
                self.assertEqual(manifest.get("version"), "0.1.0")
                self.assertEqual(
                    manifest.get("repository"),
                    "https://github.com/cbrock84/headcount",
                )
                author = manifest.get("author")
                if isinstance(author, dict):
                    author = author.get("name")
                self.assertEqual(author, "MoxyWolf LLC")
                self.assertEqual(
                    manifest.get("description"),
                    UPSTREAM_DESCRIPTIONS[department],
                    "A nonempty substitute description is not upstream's",
                )

                entry = by_name[department]
                self.assertEqual(entry.get("source"), "./plugins/" + department)
                self.assertEqual(entry.get("version"), "0.1.0")
                self.assertEqual(
                    entry.get("description"), UPSTREAM_DESCRIPTIONS[department]
                )

                readme = _file_bytes(self, data, "README.md").decode("utf-8")
                lower = readme.lower()
                self.assertIn("cbrock84/headcount", lower)
                self.assertIn("98d1c17", lower)
                self.assertRegex(lower, r"\bmit\b")
                self.assertRegex(
                    lower, r"\b(copied|copy|copies|vendored|verbatim)\b",
                    "README must disclose that the skills were copied",
                )
                words = " ".join(re.findall(r"[a-z0-9]+", lower))
                for skill in skills:
                    self.assertIn(
                        skill.replace("-", " "), words,
                        "README omits skill " + skill,
                    )
                self.assertRegex(lower, r"\bagents?\b")
                self.assertIn(department.replace("-", " "), words)

                if any(
                    path.startswith(department + "/")
                    for path in REFERENCE_EDITS
                ):
                    self.assertRegex(
                        lower, r"\b(references?|addresses?|cross[- ]department)\b",
                        "README must disclose reference edits",
                    )
                    self.assertRegex(
                        lower, r"\b(plain|prose|functions?|replac\w*|rewrit\w*)\b"
                    )
                if any(
                    path.startswith(department + "/")
                    for path in QUOTED_DESCRIPTIONS
                ):
                    self.assertRegex(lower, r"\bdescriptions?\b")
                    self.assertRegex(
                        lower, r"\bquot\w*\b",
                        "README must disclose description quoting",
                    )

    def test_catalog_stdout_stderr_exit_and_complete_coverage(self):
        result = _run(self, [
            "plugins/gstack-execution/scripts/skill_packaging.py", "--json"
        ])
        report = _json_result(self, result)
        self.assertIsInstance(report, dict)
        self.assertEqual(report.get("gate"), "PASS")
        self.assertEqual(report.get("unit"), "packages")
        self.assertEqual(report.get("failed"), [])
        checks = report.get("checks")
        self.assertIsInstance(checks, list)
        self.assertEqual(report.get("examined"), len(checks))

        records = {}
        for check in checks:
            self.assertIsInstance(check, dict)
            path = check.get("package")
            self.assertIsInstance(path, str)
            self.assertNotIn(path, records, "Duplicate catalog result: " + path)
            self.assertEqual(check.get("status"), "pass", repr(check))
            records[path] = check

        expected = {
            "plugins/%s/skills/%s/SKILL.md" % (department, skill)
            for department, skills in SKILLS.items()
            for skill in skills
        }
        imported = {
            path for path in records
            if any(path.startswith("plugins/" + department + "/")
                   for department in SKILLS)
        }
        self.assertEqual(imported, expected)
        existing = sorted(set(records) - imported)
        self.assertEqual(len(existing), 151)
        self.assertEqual(
            _fingerprint(existing), EXISTING_PACKAGE_PATHS_SHA256
        )

    def test_ci_runner_executes_nonzero_checks_and_exits_zero(self):
        result = _run(
            self,
            ["plugins/gstack-execution/scripts/run_all_tests.py"],
            timeout=1200,
            ci=True,
        )
        self.assertEqual(
            result.returncode,
            0,
            "CI runner must exit 0:\n"
            + result.stdout[-20000:] + "\n" + result.stderr[-20000:],
        )
        # PLAN.md requires empty stderr for the catalog command only.
        # The runner's count may be reported on either output stream.
        output = result.stdout + "\n" + result.stderr
        summaries = re.findall(
            r"(?m)^\s*examined\s+(\d+)\s+checks:\s+"
            r"(\d+)\s+passed,\s+(\d+)\s+failed\s*$",
            output,
        )
        self.assertTrue(
            summaries,
            "CI runner must report what it actually examined; "
            "discovery or --list output alone is insufficient",
        )
        examined, passed, failed = map(int, summaries[-1])
        self.assertGreater(examined, 0, "A zero-check CI run does not pass")
        self.assertEqual(failed, 0)
        self.assertEqual(passed, examined)


if __name__ == "__main__":
    unittest.main()
