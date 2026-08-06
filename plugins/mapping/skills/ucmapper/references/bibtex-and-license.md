# BibTexCitation and LicenseStamp — cki conventions

Companion to step 4 of the ucmapper skill. Canonical source is `GitHub/cki`; this file is a working summary, and where the two disagree, the repo wins.

## Schema

`GitHub/cki/schema/bibtex-citation.schema.json`. Required top-level: `@type` (const `BibTexCitation`), `schemaVersion` (const `1`), `entryType`, `citationKey`, `title`, `licenseStamp`, `id`. Optional: `author`, `institution`, `howpublished`, `year`, `month`, `url`, `urldate`, `note`, `keywords`. `additionalProperties` is false — an unexpected key fails validation.

`citationKey` must match `^[a-z0-9][a-z0-9._-]*$`.

`licenseStamp` requires all of: `@type` (const `LicenseStamp`), `licenseId`, `summary`, `permits`, `restricts`, `conditions`, `checkedOn`, `verifyUrl`. Also `additionalProperties: false`.

## The deterministic id

`GitHub/cki/scripts/catalog.py` computes:

```python
NS = uuid.uuid5(uuid.NAMESPACE_URL, "https://cki.opencontrols.ai")
assert entry["id"] == str(uuid.uuid5(NS, entry["citationKey"]))
```

So `id` is a pure function of `citationKey`. This is why the key must be derived from stable document identity rather than invented per run — a fresh key on a re-extraction creates a second catalog entry for the same document, and `catalog.py` fails on duplicate keys only when the keys collide, not when they diverge.

**The unit of identity is an edition, not a work.** The UCF mapper mints a new AD id for every new edition, so one AD id is exactly one edition, and each edition legitimately gets its own catalog entry: ISO/IEC 27002:2013 and ISO/IEC 27002:2022 are two documents with two keys and two `id`s. That resolves the divergence half of the warning above — re-extracting an edition means re-extracting the same AD id, which should always derive the same key — and leaves collision as the live risk. Collision is the *detectable* one: slug both editions to `iso-iec-27002-2013` because you read the year off the work rather than the edition, and the build fails on the duplicate key. Trailing year in the pattern means **edition year**. First publication and enactment belong in `note`.

Work-level relationships between those entries — this edition supersedes that one, this one was in force between these dates — deliberately do **not** live here. cki answers *what is this document and what may we do with it*; supersession and validity are reasoning-layer facts and belong in GraphCounsel, with cki carrying at most an identity-only pointer. See `DR-002` in the vault (`Projects/Team Plugins/00-Hub/`).

One-liner to compute it:

```bash
python3 -c "import uuid,sys; print(uuid.uuid5(uuid.uuid5(uuid.NAMESPACE_URL,'https://cki.opencontrols.ai'), sys.argv[1]))" "your-citation-key"
```

## License classes already in the catalog

Counted from `GitHub/cki/catalog/` as of 2026-07-29. Reuse an existing class before minting a new one — a new `licenseId` is a new legal position and should be a considered act.

| licenseId | Entries | Applies to |
|---|---|---|
| `MoxyWolf-Licensed-Corpus-Unconfirmed` | 954 | Corpus material whose license has not been confirmed. The honest default for third-party content when nothing better is established. |
| `US-PD` | 470 | U.S. Government work, public domain under 17 U.S.C. 105. Confirmed. |
| `US-PD-presumed` | 150 | Believed to be U.S. Government work but not confirmed. Use when the edicts analysis is sound but the provenance chain isn't nailed down. |
| `ECCouncil-MNDA` | 4 | EC-Council material under mutual NDA. |
| `SCF-MoxyWolf-Commercial-2026-07-02` | 4 | Secure Controls Framework under the dated commercial agreement. |
| `ScrapeSafe-OPEN` | 2 | Open per AI ScrapeSafe determination. |
| `FINRA-Public-Owned` | 1 | FINRA publishes publicly but retains ownership. |
| `CIS-Controls-NonCommercial` | 1 | CIS Controls, non-commercial terms. |

Note the shape of that distribution: the single largest class is an admission of uncertainty, and `US-PD-presumed` exists precisely so that a plausible-but-unconfirmed public-domain claim doesn't get filed as a confirmed one. Use them. The catalog is more useful honest than it is tidy.

## Worked example — a confirmed government entry

From `catalog/stigs/disa-stig-sdn-using-nv.json`:

```json
{
  "@type": "BibTexCitation",
  "schemaVersion": 1,
  "entryType": "techreport",
  "citationKey": "disa-stig-sdn-using-nv",
  "title": "SDN Using NV Security Technical Implementation Guide",
  "institution": "Defense Information Systems Agency (DISA)",
  "howpublished": "DoD Cyber Exchange (public.cyber.mil)",
  "year": "2017",
  "month": "mar",
  "url": "https://stigviewer.com/stigs/sdn_using_nv",
  "urldate": "2026-07-16",
  "note": "Current benchmark 1; benchmark status date 2017-03-01; lifecycle active. Source: STIGViewer live catalog, retrieved 2026-07-16.",
  "keywords": "STIG, DISA, security baseline, hardening",
  "licenseStamp": {
    "@type": "LicenseStamp",
    "licenseId": "US-PD",
    "summary": "U.S. Government work - public domain under 17 U.S.C. 105. No license required for reproduction, display, or derivative use.",
    "permits": ["view", "reproduce", "redistribute", "create derivative works", "programmatic access"],
    "restricts": [],
    "conditions": ["Cite the source document and version"],
    "checkedOn": "2026-07-16",
    "verifyUrl": "https://public.cyber.mil/stigs/"
  },
  "id": "150dc295-7c5f-53a4-9e64-3592cd4f184d"
}
```

Note what `summary` does there: it names the doctrine (17 U.S.C. 105) rather than asserting a conclusion. Do the same. For a U.S. state statute the analysis is the edicts-of-government doctrine rather than § 105, and the summary should say which one it is leaning on.

## For an Authority Document from the UCF mapper

`entryType` is `"misc"`. `institution` is the API's `originator`. `year` and `month` come from the as-of date embedded in `published_name` (e.g. "…as of July 17, 2026" → year 2026, month `jul`) — that is the currency of *this* snapshot, and it is **not** the edition year that goes in `citationKey`. Three dates are in play and they are easy to blur: the **edition year** (identity, in the key), the **as-of date** (currency of this snapshot, in `year`/`month`), and the **enactment or first-publication date** (provenance, in `note`). A statute enacted in 2018, last amended into an edition the mapper published in 2024, and fetched by us in 2026 carries all three, and only the middle one moves when we re-fetch.

The `note` should carry three things: enactment or first-publication provenance, what you actually loaded to verify and what you found on it, and a pointer to the `ad-{AD_ID}-citations.json` this entry ships inside.
