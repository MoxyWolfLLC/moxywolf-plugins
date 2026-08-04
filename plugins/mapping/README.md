# mapping

Compliance-mapping extraction and crosswalk tooling. Turns mapping-source documents into structured, verifiable artifacts.

## Commands

| Command | What it does |
|---|---|
| `/mapping-ucmapper` | Extract a Unified Compliance Framework Authority Document into a citations JSON and a self-contained HTML hierarchy viewer |

## /mapping-ucmapper

Give it an Authority Document id (or a `mapper.unifiedcompliance.com/public-comment/index/{id}` URL) and an output folder. It produces:

- `ad-{AD_ID}-citations.json` — `published_name` as title, a cki-conformant `BibTexCitation` with a deliberated `LicenseStamp`, a `warnings[]` array, and every citation with cleaned guidance plus its full parent chain, children, sort value, and recomputed genealogy
- `ad-{AD_ID}-hierarchy.html` — a collapsible tree with the JSON embedded inline, works from disk with no network

Both written atomically.

### How it works

The mapper page is client-rendered Angular, so its HTML is nothing but `{{template}}` placeholders. The command ignores the DOM entirely and reads the public unauthenticated JSON at `/api/authority-document/{id}/report`.

The transform is deterministic and lives in `skills/ucmapper/scripts/extract_ad.py`: identity-checked dedupe by reference, survivor remapping so parent links stay valid, cycle and orphan guards, recomputed genealogy, and FNV-1a hashes per citation. The judgment calls stay with the agent — whether the document's schema matches what the transform assumes, what the official source URL is and whether it verifies, and which license class honestly applies.

Three properties worth naming, because they are the point:

- **Schema reconnaissance runs before any transform.** `--recon` prints the document header and sample citations across depths, and anything that diverges from the expected shape becomes a warning that a human has to resolve rather than a silent adaptation.
- **It never force-merges to hit a count.** Rows sharing a reference merge only when guidance, parent, and genealogy are all identical. A real collision keeps both rows and says so. An explained discrepancy against `stats.citations` beats a tidy number that misrepresents the document. Equally, it never leaves true duplicates unmerged: a reference can carry three or more variants, and every incoming row is tested against all of them.
- **A parity check gates "done".** The API is re-fetched through a different path and the two transforms are diffed on per-citation hashes covering hierarchy shape, not just text. Must be 0/0/0, with the manifest proven to cover every citation on both sides.

`warnings[]` is load-bearing. An empty array is a claim; a populated one is the run telling you where to look.

### Tests

`skills/ucmapper/scripts/test_extract_ad.py` — synthetic documents, no network, sub-second. Run it before and after any change to the transform. It pins the duplicate-reference case that 0.2.0 fixed, the determinism of two runs over the same document, the guidance-cleaning rules including the deliberate survival of a lone newline, and the orphan-parent guard.

### Usage

```
/mapping-ucmapper 4528
/mapping-ucmapper https://mapper.unifiedcompliance.com/public-comment/index/4528
/mapping-ucmapper 4528 ~/Documents/ucf-extracts/4528
```

The AD id is parsed from the argument on every invocation — bare id, full mapper URL, or an id embedded in prose all work, and the resolved id is echoed back before any fetch so a misparse costs one line instead of a 5 MB download. An id is never carried over from earlier in the conversation.

The output folder is asked for every run unless you pass one, because these artifacts feed a CI-validated catalog and writing them somewhere unintended is worse than one extra question.

Two entry points exist: `/mapping-ucmapper` (the command — parses the id, resolves the folder, then runs the skill) and `/ucmapper` (the skill directly, skipping that wrapper). Use the command.

### The BibTeX entry

Built per the conventions in `GitHub/cki` (schema, deterministic `uuid5` id, existing license classes) — see `skills/ucmapper/references/bibtex-and-license.md`. The command **embeds** the entry in the citations JSON. Adding it to `cki/catalog/` is a separate deliberate act it will offer but never take on its own: that catalog is CI-validated, and a `LicenseStamp` is a legal claim downstream systems trust.

### Verified against

- **AD 4524** (California Consumer Privacy Act, as of 2026-07-17): 232 raw rows → 150 citations matching `stats.citations` exactly, 17 roots, parity 0/0/0, no unexpected warnings.
- **AD 4528** (DoD Instruction 5010.40, issued 2024-12-11): 456 raw rows → 369 citations matching `stats.citations` exactly, 5 roots, sort_id depths 1–7, parity 0/0/0, only the standing genealogy-convention warning. Licensed `US-PD` — the instruction names the GAO Green Book and OMB Circulars A-123/A-11 but reproduces no third-party text, so nothing non-governmental rides along.
- **AD 4501** (ISO/IEC 27002:2022, edition 3): 2,420 raw rows → 2,076 citations matching `stats.citations` exactly, 4 roots (§ 5 to § 8). The document that exposed the first-variant-only dedupe bug fixed in 0.2.1 — `§ 5.17 Control` carries a section heading plus two body rows identical to each other, and before the fix the count came out 2,077 with one citation stranded outside the tree. Licensed `MoxyWolf-Licensed-Corpus-Unconfirmed`, reusing the key that already exists in the catalog rather than minting a second identity for one document. ISO sells this standard and its stated terms prohibit reproduction without written permission and prohibit ML/AI use of the text outright, so the stamp restricts any machine-queryable surface. Verification is partial by necessity: the title and edition confirm on iso.org, but the body is paywalled, so no individual citation could be checked against the source.
- **AD 4509** (Australian Government Information Security Manual, June 2026): 2,136 raw rows → 1,912 citations against `stats.citations` 1,911, 23 roots. The +1 is the duplicate-reference case: `Personnel awareness` is a real subsection under both Telephone systems and Mobile device usage, kept as two citations rather than force-merged. This is the document that exposed the reference-keyed manifest bug fixed in 0.2.0. Licensed `MoxyWolf-Licensed-Corpus-Unconfirmed`, not public domain — the originator is a Commonwealth of Australia body so 17 U.S.C. 105 does not apply, and cyber.gov.au refused automated retrieval, so the licence could not be read and was stamped restrictively pending a human check.
