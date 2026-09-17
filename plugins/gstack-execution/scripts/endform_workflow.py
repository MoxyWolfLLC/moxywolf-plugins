#!/usr/bin/env python3
"""
Ensure a repo carries .github/workflows/endform-e2e.yml (the Endform E2E gate). Stdlib only.

  endform_workflow.py check     --repo <path>
  endform_workflow.py preflight --repo <path>
  endform_workflow.py ensure    --repo <path> --project <vercel-project-name>
  endform_workflow.py scaffold  --repo <path> [--title-regex "<expected <title>>"]

check  exits 0 and prints "present" when the file exists, 1 and "missing" when it does not,
       and reports whether the repo looks like a Playwright project and which package manager it uses.
preflight answers, locally and with no network, whether the gate can actually RUN here, and names every
       condition it examined. It catches the topology defects that otherwise surface as a red check
       several minutes after a push: the workflow running from a directory that is not the Playwright
       project root, a tsconfig the test project extends resolving outside that root, and secrets the
       workflow references. Per EV-001 a condition it could not examine reports SKIP, never PASS, and a
       run that examined nothing exits non-zero instead of reporting success. Network-dependent
       conditions (does the secret exist on GitHub, is the Vercel project linked) are the caller's;
       preflight names them so the caller can check them.
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
    text = _read(pw) if pw else None
    if text:
        m = re.search(r"baseURL\s*:\s*process\.env\.([A-Z0-9_]+)", text)
        if m:
            return m.group(1)
    return "BASE_URL"


def pnpm_version(repo):
    """pnpm/action-setup needs a version: from package.json packageManager, else None."""
    text = _read(repo / "package.json")
    if text:
        m = re.search(r'"packageManager"\s*:\s*"pnpm@([^"]+)"', text)
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


def _read(path):
    """File text, or None when the path is absent or the mount refuses the read."""
    try:
        return path.read_text()
    except (OSError, UnicodeDecodeError):
        return None

# Four outcomes, deliberately separate (EV-002's pattern). NA is a condition that does not apply to
# this repo and is not a gap. SKIP is a condition that applies and could NOT be examined, which is a
# gap, so it exits non-zero: skipped is not passed.
PASS, FAIL, SKIP, NA = "PASS", "FAIL", "SKIP", "n/a"
PKG_SKIP = {"node_modules", ".git", ".next", "dist", "build", ".venv", "vendor"}


def _packages_with_playwright(repo, max_depth=3):
    """Package roots (relative to repo) whose package.json declares @playwright/test."""
    found = []
    for pj in repo.rglob("package.json"):
        rel = pj.relative_to(repo)
        if any(part in PKG_SKIP for part in rel.parts) or len(rel.parts) - 1 > max_depth:
            continue
        try:
            if "@playwright/test" in pj.read_text():
                found.append(rel.parent)
        except OSError:
            continue
    return sorted(found, key=lambda x: str(x))


def _run_dir(repo):
    """Directory the workflow's endform test step runs in: its working-directory, else the repo root.

    Returns (Path relative to repo, examined) -- examined is False when there is no workflow to read.
    """
    wf = repo / WORKFLOW
    if not wf.exists():
        return Path("."), False
    text = _read(wf)
    if text is None:
        return Path("."), False
    step = re.search(r"endform@[^\n]*test", text)
    if not step:
        return Path("."), False
    lines = text.splitlines()
    hit = text[:step.start()].count("\n")
    # the step is the "- " item containing the command; its keys are siblings and may follow `run:`
    starts = [i for i, ln in enumerate(lines) if re.match(r"\s*-\s", ln)]
    begin = max((i for i in starts if i <= hit), default=0)
    end = min((i for i in starts if i > hit), default=len(lines))
    block = "\n".join(lines[begin:end])
    m = re.search(r"working-directory:\s*(\S+)", block)
    return (Path(m.group(1).strip().strip('"\'')) if m else Path(".")), True


def _tsconfig_extends(repo, pkg):
    """How each tsconfig under pkg extends: ("escape"|"bare", tsconfig, spec), or None when contained.

    A relative `extends` is resolved and compared against pkg. A BARE specifier
    ("@repo/typescript-config/nextjs.json") resolves through node_modules, which this
    stdlib check cannot follow -- and in a workspace it points at a sibling package the
    remote runner must also package. Reporting that as contained would be a pass over
    input never examined, so it is returned for the caller to mark unexamined.
    """
    root = (repo / pkg).resolve()
    for tc in sorted(root.glob("tsconfig*.json")):
        text = _read(tc)
        if text is None:
            continue
        m = re.search(r'"extends"\s*:\s*"([^"]+)"', text)
        if not m:
            continue
        spec = m.group(1)
        if not spec.startswith("."):
            return "bare", tc.relative_to(repo), spec
        target = (tc.parent / spec).resolve()
        try:
            target.relative_to(root)
        except ValueError:
            return "escape", tc.relative_to(repo), spec
    return None


def _workflow_secrets(repo):
    text = _read(repo / WORKFLOW)
    return None if text is None else sorted(set(re.findall(r"secrets\.([A-Za-z0-9_]+)", text)))


def preflight(repo):
    """Every condition reports its own status. SKIP is not PASS; examining nothing is a failure."""
    out = []

    def rec(name, status, detail):
        out.append((name, status, detail))

    wf_path = repo / WORKFLOW
    if not wf_path.exists():
        rec("workflow_present", FAIL, f"{WORKFLOW} is absent; run `ensure`")
    elif _read(wf_path) is None:
        rec("workflow_present", SKIP, f"{WORKFLOW} exists but this mount refuses to read it "
                                      "(EDEADLK); rerun against a fresh clone outside the mount")
    else:
        rec("workflow_present", PASS, str(WORKFLOW))

    pm = package_manager(repo)
    rec("package_manager", PASS if pm else FAIL, pm or "no lockfile found")
    if pm == "pnpm":
        v, readable = pnpm_version(repo), _read(repo / "package.json") is not None
        rec("pnpm_version_pinned", PASS if v else (FAIL if readable else SKIP),
            v or ('package.json has no "packageManager": "pnpm@<version>"' if readable
                  else "package.json is unreadable on this mount"))
    else:
        rec("pnpm_version_pinned", NA, f"not a pnpm repo (package_manager={pm})")

    pkgs = _packages_with_playwright(repo)
    run_dir, run_examined = _run_dir(repo)
    if not pkgs:
        rec("playwright_project_root", FAIL, "no package.json declares @playwright/test; run `scaffold`")
        rec("run_dir_is_project_root", NA, "no Playwright project to compare against")
    elif not run_examined:
        rec("playwright_project_root", PASS, ", ".join(str(p) for p in pkgs))
        rec("run_dir_is_project_root", SKIP, "no workflow test step to read a run directory from")
    else:
        rec("playwright_project_root", PASS, ", ".join(str(p) for p in pkgs))
        ok = run_dir in pkgs
        rec("run_dir_is_project_root", PASS if ok else FAIL,
            f"workflow runs in {run_dir}" if ok else
            f"workflow runs in '{run_dir}' but @playwright/test is declared in "
            f"{', '.join(repr(str(p)) for p in pkgs)}; the run will find no tests")

    if pkgs:
        hit = next(((pkg, e) for pkg in pkgs for e in [_tsconfig_extends(repo, pkg)] if e), None)
        if hit is None:
            rec("tsconfig_within_project", PASS, "every tsconfig extends within its own project root")
        else:
            pkg, (kind, tc, spec) = hit
            if kind == "escape":
                rec("tsconfig_within_project", FAIL,
                    f"{tc} extends '{spec}', which resolves outside {pkg}; "
                    "the remote runner cannot package it")
            else:
                rec("tsconfig_within_project", SKIP,
                    f"{tc} extends the package specifier '{spec}', which this check cannot resolve "
                    "without module resolution; in a workspace it points at a sibling package the "
                    "remote runner must also package. Confirm the runner receives it.")
    else:
        rec("tsconfig_within_project", NA, "no Playwright project to inspect")

    roots = pkgs or [Path(".")]
    cfg = next(((r, c) for r in roots for c in [playwright_config(repo / r)] if c), None)
    rec("playwright_config", PASS if cfg else FAIL,
        str(cfg[1].relative_to(repo)) if cfg else
        f"no playwright.config.* in {', '.join(repr(str(r)) for r in roots)}")

    secrets = _workflow_secrets(repo)
    rec("workflow_secrets", SKIP if secrets is None else PASS,
        "no workflow to read" if secrets is None else
        (f"references {', '.join(secrets)}; confirm each exists in the repo's Actions secrets"
         if secrets else "workflow references no secrets"))

    if os.environ.get("NODE_ENV") == "production":
        rec("node_env", FAIL, "NODE_ENV=production is exported; installs will omit devDependencies")
    else:
        rec("node_env", PASS, os.environ.get("NODE_ENV") or "unset")

    return _report(out)


def _report(out):
    """Print each condition, then coverage. Skipped is not passed, and examining nothing fails."""
    width = max(len(n) for n, _, _ in out)
    for name, status, detail in out:
        print(f"{status:4}  {name:<{width}}  {detail}")
    examined = [n for n, st, _ in out if st in (PASS, FAIL)]
    failed = [n for n, st, _ in out if st == FAIL]
    skipped = [n for n, st, _ in out if st == SKIP]
    na = [n for n, st, _ in out if st == NA]
    print(f"\nexamined {len(examined)} of {len(out)} conditions "
          f"({len(skipped)} unexamined, {len(na)} not applicable); {len(failed)} failed"
          + (f": {', '.join(failed)}" if failed else ""))
    if skipped:
        print(f"unexamined, so not passed: {', '.join(skipped)}")
    if not examined:
        print("preflight examined nothing; that is a failure, not a pass")
        return 1
    return 1 if failed or skipped else 0


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

    # --- XE-001 preflight -------------------------------------------------
    import io, contextlib

    def run_preflight(root):
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = preflight(root)
        return rc, buf.getvalue()

    def status_of(text, name):
        for line in text.splitlines():
            parts = line.split()
            if len(parts) > 1 and parts[1] == name:
                return parts[0]
        raise AssertionError(f"condition {name} not reported:\n{text}")

    # every subcommand the docstring advertises is reachable from the CLI.
    # The original defect: scaffold was documented and dispatched but never registered,
    # and the selftest called it as a function, so it passed over a path no caller could take.
    doc_cmds = {ln.split()[1] for ln in __doc__.splitlines()
                if ln.strip().startswith("endform_workflow.py ") and len(ln.split()) > 1}
    registered = set(main.__wrapped__.choices) if hasattr(main, "__wrapped__") else None
    import argparse as _ap
    _probe = _ap.ArgumentParser(); _probe.add_argument("--selftest", action="store_true")
    _sub = _probe.add_subparsers(dest="cmd")
    for _c in ("check", "ensure", "preflight", "scaffold"):
        _sub.add_parser(_c)
    assert doc_cmds == {"check", "ensure", "preflight", "scaffold"}, doc_cmds
    for cmd in doc_cmds:
        r = subprocess.run([sys.executable, str(Path(__file__).resolve()), cmd, "--repo", "/nonexistent-xe001"],
                           capture_output=True, text=True)
        assert "invalid choice" not in r.stderr, f"{cmd} is documented but not registered: {r.stderr.strip()}"

    # the monorepo defect: workflow runs at the repo root, Playwright lives in a package
    mono = Path(tempfile.mkdtemp())
    (mono / "package-lock.json").write_text("{}")
    (mono / "website").mkdir()
    (mono / "website" / "package.json").write_text('{"devDependencies":{"@playwright/test":"^1.55.0"}}')
    (mono / "website" / "playwright.config.ts").write_text("export default {}")
    (mono / WORKFLOW).parent.mkdir(parents=True)
    (mono / WORKFLOW).write_text("jobs:\n  e2e:\n    steps:\n      - run: npx endform@latest test\n")
    rc, text = run_preflight(mono)
    assert rc == 1 and status_of(text, "run_dir_is_project_root") == "FAIL", text
    assert "will find no tests" in text

    # same tree, workflow corrected to run where the project actually is
    (mono / WORKFLOW).write_text(
        "jobs:\n  e2e:\n    steps:\n      - run: npx endform@latest test\n        working-directory: website\n")
    _, text = run_preflight(mono)
    assert status_of(text, "run_dir_is_project_root") == "PASS", text

    # the shared-tsconfig defect: the test project extends a file outside its own root
    (mono / "tsconfig.base.json").write_text("{}")
    (mono / "website" / "tsconfig.json").write_text('{"extends": "../tsconfig.base.json"}')
    rc, text = run_preflight(mono)
    assert rc == 1 and status_of(text, "tsconfig_within_project") == "FAIL", text
    (mono / "website" / "tsconfig.json").write_text('{"extends": "./tsconfig.strict.json"}')
    (mono / "website" / "tsconfig.strict.json").write_text("{}")
    _, text = run_preflight(mono)
    assert status_of(text, "tsconfig_within_project") == "PASS", text

    # a workspace package specifier is NOT examined, so it must not report PASS.
    # Real shape, from stigviewer: "extends": "@repo/typescript-config/nextjs.json".
    (mono / "website" / "tsconfig.json").write_text('{"extends": "@repo/typescript-config/nextjs.json"}')
    rc, text = run_preflight(mono)
    assert rc == 1 and status_of(text, "tsconfig_within_project") == "SKIP", text
    assert "@repo/typescript-config" in text and "cannot resolve" in text, text
    (mono / "website" / "tsconfig.json").write_text('{"extends": "./tsconfig.strict.json"}')

    # secrets are surfaced before the push, not discovered by a red check
    (mono / WORKFLOW).write_text(
        "jobs:\n  e2e:\n    steps:\n      - run: npx endform@latest test\n"
        "        working-directory: website\n        env:\n"
        "          PW: ${{ secrets.E2E_APP_ACCESS_PASSWORD }}\n")
    _, text = run_preflight(mono)
    assert "E2E_APP_ACCESS_PASSWORD" in text, text

    # a repo with no Playwright project reports SKIP for what it could not examine, never PASS
    bare = Path(tempfile.mkdtemp()); (bare / "package-lock.json").write_text("{}")
    rc, text = run_preflight(bare)
    assert rc == 1 and status_of(text, "run_dir_is_project_root") == "n/a", text
    assert status_of(text, "tsconfig_within_project") == "n/a", text

    # an inapplicable condition is not a gap; an unexamined one is, and it must not exit green
    buf2 = io.StringIO()
    with contextlib.redirect_stdout(buf2):
        rc = _report([("a", PASS, "-"), ("b", NA, "-")])
    assert rc == 0, buf2.getvalue()
    buf3 = io.StringIO()
    with contextlib.redirect_stdout(buf3):
        rc = _report([("a", PASS, "-"), ("b", SKIP, "could not read")])
    assert rc == 1 and "unexamined, so not passed: b" in buf3.getvalue(), buf3.getvalue()

    # EV-001: a run that examined nothing fails rather than reporting success
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        rc = _report([("a", NA, "-"), ("b", NA, "-")])
    assert rc == 1 and "examined nothing" in buf.getvalue()

    print("selftest ok")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--selftest", action="store_true")
    sub = ap.add_subparsers(dest="cmd")
    c = sub.add_parser("check"); c.add_argument("--repo", required=True)
    e = sub.add_parser("ensure"); e.add_argument("--repo", required=True); e.add_argument("--project", required=True); e.add_argument("--force", action="store_true")
    p = sub.add_parser("preflight"); p.add_argument("--repo", required=True)
    f = sub.add_parser("scaffold"); f.add_argument("--repo", required=True); f.add_argument("--title-regex", default=None)
    a = ap.parse_args()
    if a.selftest:
        return selftest()
    repo = Path(a.repo).resolve()
    if a.cmd == "check":
        sys.exit(check(repo))
    if a.cmd == "preflight":
        sys.exit(preflight(repo))
    if a.cmd == "ensure":
        sys.exit(ensure(repo, a.project, a.force))
    if a.cmd == "scaffold":
        sys.exit(scaffold(repo, a.title_regex))
    ap.print_help()


if __name__ == "__main__":
    main()
