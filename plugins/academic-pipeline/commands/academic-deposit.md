---
description: Deposit a paper's artifact on Zenodo as its own record and DOI (Stage 10 only)
argument-hint: [artifact folder, or the paper whose artifact to deposit] [--sandbox]
---

Run **Stage 10** of the academic pipeline standalone, using the **`zenodo-deposit`** skill.

1. Identify the artifact: the folder in `$ARGUMENTS`, or the reference implementation, fixtures or dataset the named paper describes. If there's none, say so and stop.
2. Lay out or check its folder in the artifact repository (`<kind>/<slug>/` with `README.md`, `LICENSE`, `.zenodo.json`, `CITATION.cff`, inputs and `expected/`), run its checks from a fresh copy, commit, push and pull back.
3. Create a Zenodo **draft** with `scripts/zenodo_deposit.py draft`, reading the token on the user's machine (clipboard or vault file), never from chat. Write the reserved DOI into the folder's `CITATION.cff` and README, rerun `draft` to refresh the same draft, commit, and give the user the draft URL.
4. Publish with `scripts/zenodo_deposit.py publish` **only** after the user says "publish" in this run. Publishing is permanent.
5. Write the DOI into the artifact repository's index and, if a paper is named, into the Stage 7 BibTeX file and `pipeline/draft_document.md` (including the Data Availability Statement), then rerun Stage 7 and the Stage 9 gate.
