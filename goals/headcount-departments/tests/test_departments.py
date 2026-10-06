# drafted-by: gpt/gpt-6-astra
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
import unittest


DEPARTMENT_SKILLS = {
    "finance": """
        budgeting-and-forecasting
        capital-allocation
        capital-structure-and-covenants
        chief-financial-officer
        cost-accounting
        financial-modeling
        financial-reporting-and-close
        financial-statement-analysis
        internal-controls-and-audit
        revenue-recognition
        tax
        treasury-and-liquidity
        unit-economics
    """.split(),
    "people": """
        benefits-and-leave
        chief-human-resources-officer
        compensation-and-leveling
        employee-relations
        employment-compliance
        hiring-and-interviewing
        learning-and-development
        onboarding-and-offboarding
        org-design
        payroll-operations
        performance-management
        workforce-planning
    """.split(),
    "it-operations": """
        backup-and-recovery
        chief-information-officer
        cloud-administration
        collaboration-platform-administration
        endpoint-management
        identity-lifecycle-administration
        it-asset-management
        network-administration
        service-desk
        systems-administration
        telephony-and-conferencing
        virtualization-operations
    """.split(),
    "security": """
        access-and-identity
        chief-information-security-officer
        data-protection-and-encryption
        detection-and-monitoring
        incident-response
        security-architecture-review
        threat-modeling
        vulnerability-management
    """.split(),
    "pmo": """
        benefits-realization
        change-and-adoption
        dependency-and-risk-management
        estimating-and-contingency
        head-of-pmo
        portfolio-governance
        program-management
        project-delivery
        schedule-development-and-analysis
    """.split(),
    "operations": """
        business-continuity-and-resilience
        capacity-and-demand-planning
        chief-operating-officer
        facilities-and-workplace
        incident-management
        operating-cadence
        process-design
        procurement-and-sourcing
        quality-management
        service-level-management
        supply-chain-and-logistics
        vendor-management
    """.split(),
    "corporate-strategy": """
        chief-strategy-officer
        market-entry
        mergers-and-acquisitions
        portfolio-strategy
        scenario-planning
        strategic-alliances
    """.split(),
    "customer-experience": """
        chief-customer-officer
        customer-onboarding-and-implementation
        customer-success-management
        escalation-management
        self-service-and-knowledge
        support-operations
        voice-of-customer
    """.split(),
}

DEPARTMENT_HEADS = {
    "finance": "chief-financial-officer",
    "people": "chief-human-resources-officer",
    "it-operations": "chief-information-officer",
    "security": "chief-information-security-officer",
    "pmo": "head-of-pmo",
    "operations": "chief-operating-officer",
    "corporate-strategy": "chief-strategy-officer",
    "customer-experience": "chief-customer-officer",
}

EXISTING_PLUGIN_NAMES = """
    4d-blog-engine
    academic-pipeline
    analytics
    bibtex-builder
    board-deck
    composio
    council
    daily-briefings
    daily-ops
    dev-infrastructure-skills
    document-analysis
    editorial-forge
    excalidraw-vault
    frontier-founder
    frontier-founder-smb
    github-repo-analyzer
    graphify
    gstack-execution
    mapping
    moxywolf-skills
    obsidian-skills
    obsidian-update
    ponytail
    product-orchestrator
    project-init
    email-lifecycle
    marcom-audit
    research-pipeline
    saas-frontend-designer
    saas-pricing-engine
    synergy-engine
    team-kanban
    understand-anything
    vault-code-learn
    vault-skills
    vtt-to-text
""".split()

# Fixed baseline fingerprints, captured before the department import.
# Entries include every field and retain their original relative order.
EXISTING_ENTRIES_SHA256 = (
    "afcd8282ff7dd6dc3b59cf87e685b02a2efdf26e9a82264de229954dc2bd4e43"
)
EXISTING_PACKAGE_PATHS_SHA256 = (
    "7cf1fee973443be4f1b595556c9774755cd70674272eb3ebbbc583ea785fb4ec"
)
EXISTING_PACKAGE_COUNT = 151

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

# Only this separate program reads candidate files. It imports no candidate code.
SNAPSHOT_PROGRAM = r"""
import json
import sys
from pathlib import Path

marketplace = json.loads(
    Path(".claude-plugin/marketplace.json").read_text(encoding="utf-8")
)
departments = {}
for name in json.loads(sys.argv[1]):
    root = Path("plugins") / name
    manifest_path = root / ".claude-plugin" / "plugin.json"
    agent_path = root / "agents" / (name + ".md")
    departments[name] = {
        "manifest": (
            json.loads(manifest_path.read_text(encoding="utf-8"))
            if manifest_path.is_file() else None
        ),
        "agent_path": agent_path.as_posix(),
        "agent": (
            agent_path.read_text(encoding="utf-8")
            if agent_path.is_file() else None
        ),
    }
print(json.dumps({"marketplace": marketplace, "departments": departments}))
"""


def _fingerprint(value):
    serialized = json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    )
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def _run_json(case, arguments):
    candidate = os.environ.get("GOAL_CANDIDATE")
    case.assertTrue(candidate, "GOAL_CANDIDATE must name the candidate checkout")
    with tempfile.TemporaryDirectory(prefix="department-goal-") as scratch:
        environment = os.environ.copy()
        environment.update({
            "PYTHONDONTWRITEBYTECODE": "1",
            "TMPDIR": scratch,
            "TMP": scratch,
            "TEMP": scratch,
        })
        result = subprocess.run(
            [sys.executable, "-B", *arguments],
            cwd=candidate,
            env=environment,
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=120,
        )
    case.assertEqual(
        result.returncode,
        0,
        "Candidate command failed:\n"
        + result.stdout
        + "\n"
        + result.stderr,
    )
    case.assertEqual(result.stderr, "", "Candidate wrote to standard error")
    try:
        return json.loads(result.stdout)
    except ValueError as error:
        case.fail("Candidate did not print valid JSON: %s\n%s" % (
            error, result.stdout
        ))


def _catalog(case):
    report = _run_json(
        case, ["plugins/gstack-execution/scripts/skill_packaging.py", "--json"]
    )
    case.assertIsInstance(report, dict)
    case.assertEqual(report.get("gate"), "PASS")
    case.assertEqual(report.get("unit"), "packages")
    case.assertEqual(report.get("failed"), [])
    checks = report.get("checks")
    case.assertIsInstance(checks, list)
    case.assertGreater(len(checks), 0, "The catalog must examine actual packages")
    case.assertEqual(report.get("examined"), len(checks))
    records = {}
    for check in checks:
        case.assertIsInstance(check, dict)
        package = check.get("package")
        case.assertIsInstance(package, str)
        case.assertNotIn(package, records, "Duplicate catalog check: " + package)
        case.assertEqual(check.get("status"), "pass", repr(check))
        records[package] = check
    return records


def _snapshot(case, departments=()):
    return _run_json(
        case, ["-c", SNAPSHOT_PROGRAM, json.dumps(list(departments))]
    )


def _department_package(path):
    return any(
        path.startswith("plugins/" + department + "/")
        for department in DEPARTMENT_SKILLS
    )


def _frontmatter(case, text):
    """Read scalar agent metadata from emitted text using only the stdlib."""
    lines = text.splitlines()
    case.assertTrue(lines, "Agent file is empty")
    case.assertEqual(lines[0].strip(), "---", "Agent needs YAML frontmatter")
    end = next(
        (index for index, line in enumerate(lines[1:], 1)
         if line.strip() in ("---", "...")),
        None,
    )
    case.assertIsNotNone(end, "Agent frontmatter is not closed")
    fields = {}
    index = 1
    while index < end:
        line = lines[index]
        if not line.strip() or line.lstrip().startswith("#"):
            index += 1
            continue
        match = re.fullmatch(r"([A-Za-z0-9_.-]+):(?:[ \t]+(.*))?", line)
        case.assertIsNotNone(match, "Invalid agent metadata line: " + line)
        key, raw = match.group(1), (match.group(2) or "").strip()
        case.assertNotIn(key, fields, "Duplicate agent metadata key: " + key)
        index += 1
        continuation = []
        while index < end and (
            not lines[index].strip() or lines[index][:1].isspace()
        ):
            continuation.append(lines[index])
            index += 1
        if re.fullmatch(r"[|>][+-]?[1-9]?", raw):
            nonempty = [line for line in continuation if line.strip()]
            indent = min(
                (len(line) - len(line.lstrip()) for line in nonempty),
                default=0,
            )
            content = [
                line[indent:] if line.strip() else ""
                for line in continuation
            ]
            while content and not content[-1]:
                content.pop()
            if raw.startswith("|"):
                value = "\n".join(content)
            else:
                paragraphs = []
                paragraph = []
                for line in content:
                    if line:
                        paragraph.append(line)
                    else:
                        paragraphs.append(" ".join(paragraph))
                        paragraph = []
                paragraphs.append(" ".join(paragraph))
                value = "\n".join(paragraphs)
            if value and "-" not in raw:
                value += "\n"
        elif raw.startswith('"'):
            try:
                value = json.loads(raw)
            except ValueError:
                case.fail("Invalid quoted agent metadata: " + line)
            case.assertIsInstance(value, str)
        elif raw.startswith("'"):
            case.assertTrue(raw.endswith("'") and len(raw) >= 2)
            value = raw[1:-1].replace("''", "'")
        else:
            value = " ".join(
                part for part in [raw, *(line.strip() for line in continuation)]
                if part
            )
            value = re.split(r"\s+#", value, maxsplit=1)[0].rstrip()
        fields[key] = value
    return fields, "\n".join(lines[end + 1:])


class Departments(unittest.TestCase):
    def test_catalog_check_passes_every_imported_skill(self):
        """Scenario: Given the goal branch, then the catalog check reads all 79 imported department skills and passes each one"""
        records = _catalog(self)
        expected = {
            "plugins/%s/skills/%s/SKILL.md" % (department, skill)
            for department, skills in DEPARTMENT_SKILLS.items()
            for skill in skills
        }
        self.assertEqual(len(expected), 79)
        imported = {path for path in records if _department_package(path)}
        self.assertEqual(
            imported,
            expected,
            "The catalog must examine exactly the 79 specified department skills",
        )
        for path in sorted(expected):
            with self.subTest(package=path):
                self.assertEqual(records[path]["status"], "pass")

    def test_marketplace_lists_eight_departments_with_agents(self):
        """Scenario: Given the goal branch, then the marketplace lists the eight department plugins, each with an agent file named for its department that loads its department head's skill"""
        snapshot = _snapshot(self, DEPARTMENT_SKILLS)
        entries = snapshot["marketplace"]["plugins"]
        names = [entry["name"] for entry in entries]
        self.assertEqual(len(names), len(set(names)), "Plugin names must be unique")
        self.assertEqual(
            set(names), set(EXISTING_PLUGIN_NAMES) | set(DEPARTMENT_SKILLS)
        )
        by_name = {entry["name"]: entry for entry in entries}
        descriptions = set()

        for department, head in DEPARTMENT_HEADS.items():
            with self.subTest(department=department):
                entry = by_name[department]
                self.assertEqual(entry.get("source"), "./plugins/" + department)
                self.assertEqual(entry.get("version"), "0.1.0")

                data = snapshot["departments"][department]
                manifest = data["manifest"]
                self.assertIsInstance(manifest, dict, "Missing plugin manifest")
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
                description = manifest.get("description")
                self.assertIsInstance(description, str)
                self.assertTrue(description.strip(), "Plugin needs a description")
                self.assertEqual(entry.get("description"), description)

                self.assertEqual(
                    data["agent_path"],
                    "plugins/%s/agents/%s.md" % (department, department),
                )
                agent = data["agent"]
                self.assertIsInstance(agent, str, "Missing department agent")
                metadata, body = _frontmatter(self, agent)
                self.assertEqual(metadata.get("name"), department)
                delegation = metadata.get("description")
                self.assertIsInstance(delegation, str)
                self.assertTrue(delegation.strip(), "Agent needs delegation guidance")
                self.assertLessEqual(len(delegation), 1024)
                descriptions.add(delegation.strip())

                # Inspect instructions in the body, not just metadata or a title.
                reference = department + ":" + head
                self.assertIn(reference, body)
                paragraphs = re.split(r"\n\s*\n", body)
                head_instructions = [
                    paragraph for paragraph in paragraphs
                    if reference in paragraph
                ]
                self.assertTrue(
                    any(
                        re.search(r"\b(load|read|open|invoke|use)\b", paragraph, re.I)
                        and re.search(
                            r"\b(first|start|begin|before)\b", paragraph, re.I
                        )
                        for paragraph in head_instructions
                    ),
                    "Agent must instruct loading its department head first",
                )
                self.assertRegex(
                    body.lower(), r"\bspecialist\b",
                    "Agent must route to a specialist skill",
                )
                self.assertRegex(
                    body.lower(), r"\b(request|task|need|question|match|appropriate)\w*\b"
                )
                self.assertRegex(
                    body.lower(), r"\b(load|read|open|invoke|use)\b"
                )
                self.assertRegex(
                    body.lower(), r"\b(remit|scope|boundary|boundaries|within|inside)\b"
                )
                self.assertRegex(
                    body.lower(), r"\b(outside|out[- ]of[- ]scope|other department)\b"
                )
                self.assertIn("references/sources.md", body)
                self.assertRegex(body.lower(), r"\b(cite|citation|citations)\b")
                self.assertRegex(body.lower(), r"\b(return|respond|response|output)\b")
                self.assertRegex(body.lower(), r"\b(answer|recommendation|recommendations)\b")
                self.assertRegex(body.lower(), r"\bskills\b")
                self.assertRegex(body.lower(), r"\bsources\b")
                self.assertRegex(
                    body.lower(),
                    r"\b(open|unresolved|outstanding|remaining)\s+questions\b",
                )

        self.assertEqual(
            len(descriptions),
            8,
            "Each agent needs department-specific delegation guidance",
        )

    def test_existing_plugins_unchanged_and_passing(self):
        """Scenario: An existing plugin's marketplace entry changing, or an existing skill failing the catalog check, must never happen"""
        marketplace = _snapshot(self)["marketplace"]
        self.assertEqual(
            {key: value for key, value in marketplace.items() if key != "plugins"},
            MARKETPLACE_METADATA,
            "Marketplace metadata, including its top-level version, must not change",
        )
        entries = marketplace["plugins"]
        names = [entry["name"] for entry in entries]
        self.assertEqual(len(names), len(set(names)), "Plugin names must be unique")
        baseline_names = set(EXISTING_PLUGIN_NAMES)
        self.assertTrue(
            baseline_names.issubset(names),
            "An existing marketplace plugin was removed or renamed",
        )
        self.assertTrue(
            set(names).issubset(baseline_names | set(DEPARTMENT_SKILLS)),
            "An unselected plugin was added to the marketplace",
        )
        existing_entries = [
            entry for entry in entries if entry["name"] in baseline_names
        ]
        self.assertEqual(
            [entry["name"] for entry in existing_entries],
            EXISTING_PLUGIN_NAMES,
            "Existing entries must retain their relative order",
        )
        self.assertEqual(
            _fingerprint(existing_entries),
            EXISTING_ENTRIES_SHA256,
            "An existing marketplace entry changed",
        )

        records = _catalog(self)
        existing_paths = sorted(
            path for path in records if not _department_package(path)
        )
        self.assertEqual(len(existing_paths), EXISTING_PACKAGE_COUNT)
        self.assertEqual(
            _fingerprint(existing_paths),
            EXISTING_PACKAGE_PATHS_SHA256,
            "The catalog must still examine every original package",
        )
        for path in existing_paths:
            with self.subTest(package=path):
                self.assertEqual(records[path]["status"], "pass")


if __name__ == "__main__":
    unittest.main()
