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
- **It never force-merges to hit a count.** Rows sharing a reference merge only when guidance, parent, and genealogy are all identical. A real collision keeps both rows and says so. An explained discrepancy against `stats.citations` beats a tidy number that misrepresents the document.
- **A parity check gates "done".** The API is re-fetched through a different path and the two transforms are diffed on per-citation hashes covering hierarchy shape, not just text. Must be 0/0/0.

`warnings[]` is load-bearing. An empty array is a claim; a populated one is the run telling you where to look.

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

AD 4524 (California Consumer Privacy Act, as of 2026-07-17): 232 raw rows → 150 citations matching `stats.citations` exactly, 17 roots, parity 0/0/0, no unexpected warnings.
