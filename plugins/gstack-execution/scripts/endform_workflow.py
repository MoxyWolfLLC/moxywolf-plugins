#!/usr/bin/env python3
"""
Ensure a repo carries .github/workflows/endform-e2e.yml (the Endform E2E gate). Stdlib only.

  endform_workflow.py check  --repo <path>
  endform_workflow.py ensure --repo <path> --project <vercel-project-name>

check  exits 0 and prints "present" when the file exists, 1 and "missing" when it does not,
       and reports whether the repo looks like a Playwright project and which package manager it uses.
ensure writes the file from references/endform-e2e.yml with the Vercel project name filled in and the
       install step matched to the repo's lockfile (pnpm / npm / bun). Never overwrites an existing file
       unless --force. Committing, pushing and pulling back are the caller's job (/gstack-build Step 4).
"""
import argparse
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
TEMPLATE = HERE.parent / "skills" / "gstack-execution" / "references" / "endform-e2e.yml"
WORKFLOW = Path(".github/workflows/endform-e2e.yml")
PNPM_STEP = "      - name: Set up pnpm\n        uses: pnpm/action-setup@v6\n        with:\n          run_install: true\n"
INSTALL = {
    "pnpm": PNPM_STEP,
    "npm": "      - name: Install dependencies\n        run: npm ci\n",
    "bun": "      - name: Set up bun\n        uses: oven-sh/setup-bun@v2\n\n      - name: Install dependencies\n        run: bun install --frozen-lockfile\n",
}


def package_manager(repo):
    if (repo / "pnpm-lock.yaml").exists():
        return "pnpm"
    if (repo / "bun.lockb").exists() or (repo / "bun.lock").exists():
        return "bun"
    if (repo / "package-lock.json").exists():
        return "npm"
    return None


def playwright_config(repo):
    return next((p for p in repo.glob("playwright.config.*")), None)


def check(repo):
    present = (repo / WORKFLOW).exists()
    pm, pw = package_manager(repo), playwright_config(repo)
    print(f"{'present' if present else 'missing'} workflow={WORKFLOW} package_manager={pm} playwright_config={pw.name if pw else None}")
    return 0 if present else 1


def ensure(repo, project, force):
    target = repo / WORKFLOW
    if target.exists() and not force:
        print(f"present, not touched: {target}")
        return 0
    pm = package_manager(repo)
    if pm is None:
        sys.exit("no lockfile found (pnpm-lock.yaml, package-lock.json, bun.lock*); is this a Node project deployed on Vercel?")
    text = TEMPLATE.read_text().replace("{{VERCEL_PROJECT}}", project)
    if pm != "pnpm":
        assert text.count(PNPM_STEP) == 1
        text = text.replace(PNPM_STEP, INSTALL[pm])
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(text)
    pw = playwright_config(repo)
    print(f"wrote {target} (project={project}, install={pm})")
    if pw is None:
        print("note: no playwright.config.* in this repo; the workflow will run zero tests until specs exist")
    return 0


def selftest():
    import subprocess, tempfile
    tmp = Path(tempfile.mkdtemp()); (tmp / "package-lock.json").write_text("{}")
    assert check(tmp) == 1
    ensure(tmp, "demo-project", False)
    out = (tmp / WORKFLOW).read_text()
    assert "project-name: demo-project" in out and "npm ci" in out and "pnpm/action-setup" not in out and "endform@latest test" in out
    assert check(tmp) == 0 and ensure(tmp, "other", False) == 0 and "demo-project" in (tmp / WORKFLOW).read_text()
    (tmp / "pnpm-lock.yaml").write_text(""); ensure(tmp, "p2", True); assert "pnpm/action-setup@v6" in (tmp / WORKFLOW).read_text()
    print("selftest ok")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--selftest", action="store_true")
    sub = ap.add_subparsers(dest="cmd")
    c = sub.add_parser("check"); c.add_argument("--repo", required=True)
    e = sub.add_parser("ensure"); e.add_argument("--repo", required=True); e.add_argument("--project", required=True); e.add_argument("--force", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        return selftest()
    repo = Path(a.repo).resolve()
    if a.cmd == "check":
        sys.exit(check(repo))
    if a.cmd == "ensure":
        sys.exit(ensure(repo, a.project, a.force))
    ap.print_help()


if __name__ == "__main__":
    main()
