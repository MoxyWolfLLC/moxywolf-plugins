---
name: zenodo-deposit
description: Deposit a paper's artifacts (reference implementation, fixtures, dataset) on Zenodo, one record and DOI per artifact, from one artifact repository. Stage 10 of the academic-pipeline, optional, after the Stage 9 gate passes. Use when a paper has code or data a reader should be able to run or check, or when the user asks to put something on Zenodo or get it a DOI.
---

# Zenodo deposit (Stage 10)

A paper that claims something a reader can run should give them the thing, with a DOI that won't move. This stage puts each artifact in the user's artifact repository, uploads it to Zenodo as a draft, publishes it only when the user says so, and writes the DOI back into the paper.

## When it runs

After Stage 9 passes, if the run produced or names an executable or data artifact: a reference implementation, its fixtures, a dataset, an evaluation set. If there is none, report `Stage 10: SKIP (no artifact)`. Never report a pass for a stage that didn't run.

## Settled choices

- **One artifact repository, many records.** Artifacts live in one repository (MoxyWolf: `MoxyWolfLLC/zenodo`, cloned at `~/GitHub/zenodo`). Each artifact gets its own Zenodo record and DOI. Don't propose a repository per artifact.
- **Direct upload, not the GitHub integration.** Zenodo's GitHub integration stays **off** for the artifact repository: a GitHub release would archive every artifact together as one record. Uploads go through `scripts/zenodo_deposit.py`.
- **License.** MIT for code, unless the user says otherwise. Synthetic fixtures ship under the same license. Real data needs the user's call on license and on whether it may be published at all.
- **Creator.** The author's name, affiliation and ORCID come from the run's author block or the voice profile. Never invent an ORCID; if it isn't known, ask.

## Step 1. Lay out the artifact folder

In the artifact repository, create `<kind>/<slug>/`. Use `runners/` for executable reference implementations and `datasets/` for data; the slug is the run's target slug. The folder is self-contained:

| File | Holds |
| --- | --- |
| `README.md` | What it is, how to run it, which paper it accompanies, the DOI once published |
| `LICENSE` | The license text |
| `.zenodo.json` | Zenodo metadata: `upload_type`, `title`, `creators` (name, affiliation, orcid), `description`, `license`, `keywords`, `version` |
| `CITATION.cff` | Citation metadata with the author's ORCID; add `doi` and `date-released` after publishing |
| the code and inputs | Standard library where possible, so a reader needs nothing installed |
| `expected/` | The output of every check the artifact runs, so a reader can diff their run against it |

Run the artifact's checks from a fresh copy of the folder before uploading. If its output is deterministic, say so in the README and give the one-line diff that proves it. Scan the folder for internal paths, names, secrets and real personal data before it leaves the machine.

Add a row to the repository root `README.md` index (directory, what it is, paper, DOI = `Pending`). Commit, push, verify `ls-remote`, and pull back into the user's local clone.

## Step 2. Create a draft

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/zenodo_deposit.py" draft <artifact folder> [--token-file <env file>] [--sandbox]
```

It zips the folder under its slug (skipping caches and its own state file), creates a draft, uploads the zip and sends `.zenodo.json` as metadata. It records the draft in `<folder>/.zenodo-deposit.json`, which stays out of git. It prints the draft URL and the reserved DOI, which only becomes live on publishing.

**The token.** A Zenodo personal access token with `deposit:write` and `deposit:actions`, made under the user's Zenodo account settings, Applications. Read it where it lives, on the user's machine:

- from a vault env file (`ZENODO_TOKEN=...`) via `--token-file`, or
- from the clipboard on the user's Mac, run there, so it never enters the transcript: `ZENODO_TOKEN="$(pbpaste | tr -d '[:space:]')" python3 ... draft <folder>`.

Never ask the user to paste the token into chat. If they do anyway, use it, then tell them in one line to revoke it and make a new one, because it's now in the transcript.

Tell the user where to see the draft: `https://zenodo.org/uploads/<id>`, signed in as the token's owner. `/records/<id>` is "Page not found" until the record is published. That's expected, not an error.

## Step 3. Publish, only on the user's word

Publishing is permanent: a published record can't be deleted, only versioned. Run it only after the user says "publish" (or an unambiguous equivalent) in this run. "Looks great" isn't that; ask once.

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/zenodo_deposit.py" publish <artifact folder> [--token-file <env file>]
```

It refuses if no draft is recorded, if the draft was made on the sandbox, or if the record is already published. Then confirm that `https://doi.org/<doi>` resolves.

## Step 4. Write the DOI back

1. **Artifact repository.** Replace `Pending` in the index with the DOI link, add `doi` and `date-released` to the artifact's `CITATION.cff`, and add the DOI to its README. Commit, push, verify, pull back.
2. **The paper.** Add a `@misc` entry to the run's `sources.bib` (author, title, `howpublished = {Zenodo, version X, software}`, year, `doi`, `url = https://doi.org/<doi>`). Cite it where the paper describes the artifact and in the Data Availability Statement, which says where the artifact is archived and under what license.
3. **Rerun Stage 7 and the Stage 9 gate.** The new citation shifts Vancouver numbering, so the gate must pass again before the paper is presented.

## Report

One line per artifact: folder, record URL, DOI, license. Then the Stage 9 gate lines from the rerun.
