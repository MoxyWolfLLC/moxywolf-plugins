---
name: ucmapper
description: >
  Extract a Unified Compliance Framework Authority Document from the public UCF mapper API into a structured citations JSON and a self-contained collapsible HTML hierarchy viewer. Use when the user asks to extract, pull, scrape, or map a UCF Authority Document, references a mapper.unifiedcompliance.com public-comment URL, gives an AD id to extract, or invokes /mapping-ucmapper. Produces ad-{AD_ID}-citations.json (full parent/child hierarchy, recomputed genealogy, cki-conformant BibTexCitation with a deliberated LicenseStamp, honest warnings) and ad-{AD_ID}-hierarchy.html.
---

# UCF Authority Document extraction

Two files, one Authority Document:

- `ad-{AD_ID}-citations.json` — title, BibTexCitation, warnings, and every citation with its full hierarchy
- `ad-{AD_ID}-hierarchy.html` — a self-contained collapsible tree, works from disk with no network

The deterministic half of this job lives in `${CLAUDE_PLUGIN_ROOT}/skills/ucmapper/scripts/extract_ad.py`. Run the script; do not reimplement its transform in an ad-hoc snippet. Two runs of the same document must produce byte-identical output, and the parity check in step 5 only means something if both sides compute the same hash the same way.

Your job is the half a script cannot do: deciding whether this document's schema is what the transform assumes, finding and verifying the document's official URL, and choosing a LicenseStamp that is a defensible legal claim rather than a convenient default.

## Inputs

`AD_URL` is `https://mapper.unifiedcompliance.com/public-comment/index/{AD_ID}` (e.g. 4524). The user may give the URL or bare the id.

`OUTPUT_FOLDER` — **always ask**, every run. There is no default. Create the folder if it doesn't exist. Confirm the resolved absolute path back to the user before writing.

## Step 0 — Schema reconnaissance (mandatory, before any transform)

```
python3 ${CLAUDE_PLUGIN_ROOT}/skills/ucmapper/scripts/extract_ad.py --ad {AD_ID} --recon
```

This fetches the report and prints the document header, the sort_id depth and width profile, and sample citations spanning up to five depths. **Read the output.** You are confirming, with your own eyes and not by assertion:

- `published_name`, `id`, `stats.citations` exist at document level
- citations carry `id`, `reference`, `guidance`, `sort_id`, `sort_value`, `genealogy`, `parent`
- `sort_id` segments are fixed-width zero-padded (`001 002 003`) — the sort in step 2 is lexicographic and silently produces wrong order if they aren't
- `parent` is `{id}` or null; `genealogy` is space-separated zero-padded ids

The script raises a warning for each of these that fails, but a warning is not a decision. If anything diverges, **stop and adapt deliberately** — tell the user what diverged, what you propose to do about it, and make sure the deviation lands in the output's `warnings[]`. Do not force unfamiliar data into this document's shape. A document whose sort_id isn't fixed-width needs a different sort, not a warning and a shrug.

Reference point for what normal looks like: AD 4524 (CCPA) reports 232 raw citation rows, `stats.citations` 150, sort_id depths 1–5 at width 3, genealogy padded to 7. It transforms to exactly 150 citations across 17 roots with zero warnings beyond the standing genealogy-convention note.

## Step 1 — Get the data from the API, not the page

The mapper page is client-rendered Angular. Its HTML contains only `{{template}}` placeholders. **Do not scrape the DOM, and do not parse the tagged colour-coded guidance markup.** The real data is public, unauthenticated JSON at:

```
https://mapper.unifiedcompliance.com/api/authority-document/{AD_ID}/report
```

The script fetches this itself. The response is large (AD 4524 is ~5 MB); if you fetch it by hand with a web-fetch tool it will likely truncate, so use the script or a shell `curl -s {api_url} -o /tmp/ad{AD_ID}.json` and pass `--raw`.

**Failure handling.** Non-200 or malformed JSON → halt and report; the script retries at most twice and then exits 1. Do not paper over a failed fetch. Empty `citations[]` → the script emits a valid document with an empty citations array plus a warning. Never invent content to fill a gap.

## Step 2 — Transform (what the script does, and why)

Run it once the recon looks right:

```
python3 ${CLAUDE_PLUGIN_ROOT}/skills/ucmapper/scripts/extract_ad.py --ad {AD_ID} --raw /tmp/ad{AD_ID}.json --out "{OUTPUT_FOLDER}"
```

The rules it implements, so you can check its work:

1. **Title** is `published_name` verbatim. Do NOT append the AD id.
2. **Sort** by (`sort_id`, `id`), lexicographic — sound only because step 0 confirmed fixed-width segments.
3. **Dedupe by `reference`, identity-checked.** The API repeats a reference once per mandate row. Rows merge only when cleaned guidance, parent id, and genealogy are *all* identical. If rows sharing a reference differ in any of those, **both are kept** as distinct citations and a `warnings[]` entry describes the collision. Never force-merge to make the count match `stats.citations` — a tidy number that misrepresents the document is worse than an explained discrepancy. Every dropped row's id remaps to its survivor so parent links stay valid. A reference can accumulate more than two variants, and each incoming row is tested against **every** variant already surviving under that reference, not just the first: through 0.2.0 only the first was compared, so once one genuine collision was recorded, later rows identical to *each other* were never merged. AD 4501 (ISO/IEC 27002:2022) is the case — `§ 5.17 Control` carries a section heading plus two identical body rows, and the count came out 2077 against `stats.citations` 2076 with one citation stranded outside the tree. Fixed in 0.2.1.
4. **Guidance cleaning**, in this order: remove every `{...}` brace-delimited tagged-term span (e.g. `{reasonable step}`), then collapse every run of 2+ whitespace characters to a single space (`\s{2,}` → `" "`), then remove spaces before `,.;:!?)`, then trim. Note the exact rule: a *lone* newline is whitespace but not a run of two, so it survives. That is deliberate and pinned so the JS side can match.
5. **Hierarchy** per citation: walk `parent.id` chains through the survivor remap for the full ancestor chain; children are the surviving citations whose parent resolves to this one, unique by reference.
6. **Cycle and orphan guard.** A chain revisiting a seen id, or a `parent.id` resolving to nothing, stops that walk, excludes the bad link, and records it in `warnings[]`. Never loop; never silently drop.
7. **Genealogy is recomputed, not copied.** Output `genealogy` is the survivor-chain ids, zero-padded, root first, and — this is the plugin's own convention — **including the citation itself**. The API's `genealogy` field uses a different convention (ancestors only, except roots, which list themselves) and may reference merged-away ids. The script emits a standing warning saying so; the two fields are not interchangeable.

Output shape:

```json
{
  "title": "<published_name>",
  "bibTexCitation": { },
  "warnings": ["<anything assumed, deviated, or flagged during this run — empty array if clean>"],
  "citations": [
    {
      "reference": "§ 1798.100",
      "guidance": "<cleaned text>",
      "hierarchy": {
        "@type": "HierarchyItem",
        "schemaVersion": 1,
        "@id": "https://mapper.unifiedcompliance.com/public-comment/index/{AD_ID}#citation-<id>",
        "elementId": "<id>",
        "parents": [{"@type": "Parent", "elementId": "...", "reference": "..."}],
        "children": [{"@type": "Child", "elementId": "...", "reference": "..."}],
        "sortValue": "<sort_id>",
        "genealogy": ["<survivor-chain ids>"]
      }
    }
  ]
}
```

**Validation, all required and all performed by the script:** unique-citation count against `stats.citations` — if they differ after the identity-checked dedupe, the conflicting rows go into `warnings[]` and the run reports rather than fails; every citation reachable from the roots by walking children; root count > 0 unless the document is genuinely flat. Read the printed summary. A run with warnings is not automatically a bad run, but it is never a run you pass along without reading them.

Both files are written atomically — temp name in the destination folder, then rename.

## Step 3 — HTML hierarchy viewer

The script emits it: JSON embedded inline (no external fetch, works from disk), roots at top level, `<details>/<summary>` per branch, leaves as plain rows, reference in bold colour then guidance, child count on branches, Expand-all / Collapse-all, warnings surfaced in a banner.

Two injection guards, both already in the generated file, both mandatory if you ever regenerate it by hand:

- **(a)** all text goes through the `textContent` trick before touching `innerHTML`
- **(b)** the serialized JSON has `</` replaced with `<\/` before embedding — a guidance string containing `</script>` would otherwise terminate the script element

## Step 4 — BibTeX entry (cki methodology, adapted)

The cki repo (`GitHub/cki`) builds BibTexCitation entries *from* a URL. Here you must first **find** the document's official URL. Read `${CLAUDE_PLUGIN_ROOT}/skills/ucmapper/references/bibtex-and-license.md` for the schema, the deterministic id rule, and the license classes already in the catalog.

1. **Web-search the `published_name`.** Collect multiple candidate URLs and rank them: the issuing body's own domain (matching `originator`) beats aggregators and mirrors — Justia, public.law, third-party PDF hosts — always.
2. **Verify the chosen URL live.** Load it and confirm the document title *and* at least one known citation reference from the extraction appear in the page text. A URL that returns 200 is not a verified URL.
3. **If nothing verifies**, use the UCF mapper page itself as `url` and `verifyUrl`, add a `warnings[]` entry, and state the limitation in `note`. Never substitute an unverified mirror to fill the field.
4. **Build the entry** per cki conventions (`GitHub/cki/schema/bibtex-citation.schema.json`, examples throughout `catalog/`).
5. `entryType`: `"misc"`. `citationKey`: a deterministic kebab-case slug derived from document identity, not invented fresh per run — pattern `{jurisdiction-or-originator}-{code/standard}-{title-number}-{short-name}-{enactment-year}`. AD 4524 → `ca-civ-div3-part4-title-1-81-5-ccpa-2018`. The same document must always yield the same key, because:
6. `id` is `uuid5` of the citationKey under namespace `uuid5(NAMESPACE_URL, "https://cki.opencontrols.ai")`. `GitHub/cki/scripts/catalog.py` validates this and fails the build if it doesn't match.
7. `institution`: the `originator` from the API. `year` / `month`: from the as-of date in the title. `urldate` and `checkedOn`: today.
8. `note`: enactment provenance, the verification statement (what you loaded and what you found on it), and a cross-reference to the citations JSON.
9. **LicenseStamp is a decision procedure, not a default.** Branch on originator type:
   - Government body publishing its own law or regulation → an edicts-of-government analysis may support `US-PD` (or the jurisdiction equivalent); cite the doctrine in `summary`
   - Private or international standards body (ISO, PCI SSC, ANSI, EC-Council, SCF…) → **not** public domain; check the cki catalog for an existing license class for that originator and reuse it
   - No precedent or unclear → choose the narrowest applicable class, set restrictive `permits`, and flag for human confirmation in `note`
   - **Never default to `US-PD` when uncertain.** Restrictive-and-flagged beats permissive-and-wrong. This stamp is a legal claim downstream systems will trust.
10. Write the entry to a JSON file and embed it by re-running the script with `--bibtex`, which places it as top-level `bibTexCitation` between `title` and `citations`:

```
python3 ${CLAUDE_PLUGIN_ROOT}/skills/ucmapper/scripts/extract_ad.py --ad {AD_ID} --raw /tmp/ad{AD_ID}.json --out "{OUTPUT_FOLDER}" --bibtex /tmp/bib{AD_ID}.json
```

This command **embeds only**. Adding the entry to `GitHub/cki/catalog/` is a separate deliberate act — that catalog is CI-validated and a wrong LicenseStamp propagates. Offer it; never do it unasked.

## Step 5 — Parity check (required before declaring done)

Independently re-fetch the API **through a different tool or path than the one that built the file** — a browser fetch if available, otherwise a second host-shell fetch after a short delay — then diff:

```
python3 ${CLAUDE_PLUGIN_ROOT}/skills/ucmapper/scripts/extract_ad.py --ad {AD_ID} --raw /tmp/ad{AD_ID}.json --parity /tmp/ad{AD_ID}-second.json
```

The hash input per citation is `reference + guidance + parentChain + sortValue + genealogy.join(",") + childCount`, where `parentChain` is the ancestor elementIds root-first joined by `,`. Hierarchy shape is covered, not just text. The manifest is **keyed by `elementId`, not by `reference`** — rule 3 deliberately keeps two citations that share a reference when they differ in guidance, parent or genealogy, so a reference-keyed manifest overwrites one of them and drops it from the diff while still reporting 0/0/0. That was a live bug through 0.1.1: AD 4509 (Australian Government ISM) carries `Personnel awareness` under both Telephone systems and Mobile device usage, its manifest held 1911 keys for 1912 citations, and an edit confined to the uncovered row passed clean. Fixed in 0.2.0 and pinned by `scripts/test_extract_ad.py`.

The script also asserts, independently of the hashes, that citation counts are equal on both sides, that each side's manifest covers every one of its own citations (`coverage` in the printed output), and that both reconcile against `stats.citations` modulo documented `warnings[]` collisions. Hash agreement over a short manifest is not parity, so a coverage shortfall fails the run on its own.

Result must be **0 missing / 0 extra / 0 content mismatch** with `coverage` full on both sides, or every exception traceable to a `warnings[]` entry. Exit code 2 means parity failed.

**Two gotchas worth the ink.** In JavaScript, FNV-1a must use `Math.imul(h, 0x01000193) >>> 0` — plain multiplication overflows Number precision and produces false mismatches against Python's `(h * 0x01000193) & 0xFFFFFFFF`. And a passing parity check proves the two fetches agree; it does **not** prove the transform rules fit this document. That is what step 0 and `warnings[]` are for, and no amount of green hashes substitutes for having read the recon output.

Before changing anything in `extract_ad.py`, run its tests — they need no network and take under a second:

```
python3 ${CLAUDE_PLUGIN_ROOT}/skills/ucmapper/scripts/test_extract_ad.py
```

Capture the exit code directly rather than through a pipe (`python3 test_extract_ad.py > out 2>&1; RC=$?`); `cmd | tail` reports tail's status and will show a green 0 over a failing suite.

## Reporting back

Tell the user: the resolved output folder, both filenames, the citation count against `stats.citations`, the root count, the parity result, the chosen `citationKey` and `licenseId` with one line on why that license class, and every `warnings[]` entry verbatim. If warnings is empty, say so — it means something.
