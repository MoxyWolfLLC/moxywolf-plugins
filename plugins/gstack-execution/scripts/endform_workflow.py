#!/usr/bin/env python3
"""
Ensure a repo carries .github/workflows/endform-e2e.yml (the Endform E2E gate). Stdlib only.

  endform_workflow.py check    --repo <path>
  endform_workflow.py ensure   --repo <path> --project <vercel-project-name>
  endform_workflow.py scaffold --repo <path> [--title-regex "<expected <title>>"]

check  exits 0 and prints "present" when the file exists, 1 and "missing" when it does not,
       and reports whether the repo looks like a Playwright project and which package manager it uses.
ensure writes the file from references/endform-e2e.yml with the Vercel project name filled in and the
       install step matched to the repo's lockfile (pnpm / npm / bun). Never overwrites an existing file
       unless --force. Committing, pushing and pulling back are the caller's job (/gstack-build Step 4).
scaffold gives a repo with no Playwright suite the minimum one: package.json (devDependency @playwright/test only,
       created only if absent), playwright.config.ts reading BASE_URL, e2e/smoke.spec.ts, then runs
       npm install with NODE_ENV=development so the lockfile keeps devDependencies (a shell that exports
       NODE_ENV=production writes a lockfile npm ci then rejects in CI). Existing files are never overwritten.

Results never come from an "Endform connector"; there is none. The workflow's `e2e` check-run on the pull
request and its job log (which prints the Endform suite-run URL) are where a session reads the outcome.
"""
import argparse
import os
import re
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


def base_url_env(repo):
    """The env var the repo's playwright config reads for baseURL (BASE_URL when none is found)."""
    pw = playwright_config(repo)
    if pw:
        m = re.search(r"baseURL\s*:\s*process\.env\.([A-Z0-9_]+)", pw.read_text())
        if m:
            return m.group(1)
    return "BASE_URL"


def pnpm_version(repo):
    """pnpm/action-setup needs a version: from package.json packageManager, else None."""
    pj = repo / "package.json"
    if pj.exists():
        m = re.search(r'"packageManager"\s*:\s*"pnpm@([^"]+)"', pj.read_text())
        if m:
            return m.group(1)
    return None


def check(repo):
    present = (repo / WORKFLOW).exists()
    pm, pw = package_manager(repo), playwright_config(repo)
    print(f"{'present' if present else 'missing'} workflow={WORKFLOW} package_manager={pm} playwright_config={pw.name if pw else None} url_env={base_url_env(repo)}")
    if pm == "pnpm" and pnpm_version(repo) is None:
        print('warning: pnpm repo without "packageManager" in package.json; pnpm/action-setup will fail with "No pnpm version is specified"')
    if os.environ.get("NODE_ENV") == "production":
        print("warning: NODE_ENV=production is exported; npm install will omit devDependencies. Use NODE_ENV=development for installs and lockfiles.")
    if pw is None and (repo / "package.json").exists() is False:
        print("note: no package.json and no playwright config; run `scaffold` to add the minimum suite")
    return 0 if present else 1


PACKAGE_JSON = """{
  "name": "%s",
  "private": true,
  "description": "package.json exists for the Playwright e2e suite; see playwright.config.ts.",
  "scripts": {
    "e2e": "playwright test",
    "e2e:endform": "endform test"
  },
  "devDependencies": {
    "@playwright/test": "^1.55.0"
  }
}
"""
PLAYWRIGHT_CONFIG = """import { defineConfig } from "@playwright/test";

// BASE_URL is exported by .github/workflows/endform-e2e.yml (the Vercel preview deployment).
// Locally: BASE_URL=http://127.0.0.1:8899 ./node_modules/.bin/playwright test
// (use the repo's binary; a global `playwright` on PATH is not @playwright/test).
export default defineConfig({
  testDir: "e2e",
  timeout: 30_000,
  retries: 0,
  reporter: "list",
  use: {
    baseURL: process.env.BASE_URL ?? "http://127.0.0.1:3000",
    trace: "retain-on-failure",
  },
});
"""
SMOKE_SPEC = """import { test, expect } from "@playwright/test";

// First spec behind the Endform gate: the deployed site serves its entry page without page errors.
test("home page loads with the expected title", async ({ page }) => {
  const errors: string[] = [];
  page.on("pageerror", (e) => errors.push(e.message));
  const res = await page.goto("/");
  expect(res?.status()).toBe(200);
  await expect(page).toHaveTitle(%s);
  expect(errors, "page errors").toEqual([]);
});
"""


def scaffold(repo, title_regex):
    import subprocess
    wrote = []
    for rel, content in (("package.json", PACKAGE_JSON % repo.name), ("playwright.config.ts", PLAYWRIGHT_CONFIG),
                         ("e2e/smoke.spec.ts", SMOKE_SPEC % (title_regex or "/./"))):
        t = repo / rel
        if t.exists():
            print(f"kept {rel}")
            continue
        t.parent.mkdir(parents=True, exist_ok=True); t.write_text(content); wrote.append(rel)
    env = {**os.environ, "NODE_ENV": "development"}
    r = subprocess.run(["npm", "install"], cwd=str(repo), env=env, capture_output=True, text=True)
    if r.returncode != 0:
        sys.exit(f"npm install failed: {r.stderr.strip()[-400:]}")
    lock = repo / "package-lock.json"
    if lock.exists() and "@playwright/test" not in lock.read_text():
        sys.exit("package-lock.json has no @playwright/test; the install ran with devDependencies omitted")
    print(f"scaffolded {wrote or 'nothing new'}; npm install ok (NODE_ENV=development); run: BASE_URL=<url> ./node_modules/.bin/playwright test")
    return 0


def ensure(repo, project, force):
    target = repo / WORKFLOW
    if target.exists() and not force:
        print(f"present, not touched: {target}")
        return 0
    pm = package_manager(repo)
    if pm is None:
        sys.exit("no lockfile found (pnpm-lock.yaml, package-lock.json, bun.lock*); is this a Node project deployed on Vercel?")
    text = TEMPLATE.read_text().replace("{{VERCEL_PROJECT}}", project)
    env_var = base_url_env(repo)
    text = text.replace("set-url-env-var: BASE_URL", f"set-url-env-var: {env_var}")
    if pm == "pnpm":
        if pnpm_version(repo) is None:
            sys.exit('pnpm repo without a "packageManager" field: add "packageManager": "pnpm@<version>" to package.json '
                     '(pnpm/action-setup refuses to run without a version), then rerun ensure')
    else:
        assert text.count(PNPM_STEP) == 1
        text = text.replace(PNPM_STEP, INSTALL[pm])
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(text)
    pw = playwright_config(repo)
    print(f"wrote {target} (project={project}, install={pm}, url env={env_var})")
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
    (tmp / "pnpm-lock.yaml").write_text("")
    try:
        ensure(tmp, "p2", True); assert False, "pnpm without packageManager must refuse"
    except SystemExit as e:
        assert "packageManager" in str(e)
    (tmp / "package.json").write_text('{"packageManager": "pnpm@12.4.1"}')
    (tmp / "playwright.config.ts").write_text("export default { use: { baseURL: process.env.OC_E2E_BASE_URL ?? 'x' } }")
    ensure(tmp, "p2", True); out = (tmp / WORKFLOW).read_text()
    assert "pnpm/action-setup@v6" in out and "set-url-env-var: OC_E2E_BASE_URL" in out and "set-url-env-var: BASE_URL" not in out
    # scaffold: files only (npm is stubbed out by a fake on PATH)
    import stat
    fake = tmp / "bin"; fake.mkdir(); (fake / "npm").write_text("#!/bin/sh\necho '{\"packages\":{\"node_modules/@playwright/test\":{}}}' > package-lock.json\n"); (fake / "npm").chmod(0o755)
    os.environ["PATH"] = str(fake) + os.pathsep + os.environ["PATH"]
    t2 = Path(tempfile.mkdtemp()); scaffold(t2, "/Demo/")
    assert (t2 / "package.json").exists() and (t2 / "playwright.config.ts").exists() and "/Demo/" in (t2 / "e2e/smoke.spec.ts").read_text()
    (t2 / "package.json").write_text("custom"); scaffold(t2, None); assert (t2 / "package.json").read_text() == "custom"
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
    if a.cmd == "scaffold":
        sys.exit(scaffold(repo, a.title_regex))
    ap.print_help()


if __name__ == "__main__":
    main()
