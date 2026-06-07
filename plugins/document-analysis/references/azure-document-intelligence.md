# Azure Document Intelligence — adoption reference

Status: **documented, not yet wired.** This captures what it'd take to add Azure Document Intelligence (DI) to the `document-analysis` plugin, the current facts (pricing, API version, data handling), and the open decisions — so the build is a quick, informed step when we choose to do it. Researched 2026-06-07.

## What it is and when to reach for it

Azure AI Document Intelligence (formerly Form Recognizer) is a cloud OCR/layout service. markitdown can route conversion through it instead of the built-in PDF/Office/image converters, producing **layout-faithful** Markdown — correct reading order, real table structure, multi-column handling, selection marks.

Three tiers of extraction fidelity now available in the plugin:

| Path | What it does | Cost | Data leaves the machine? |
|------|-------------|------|--------------------------|
| Built-in (default) | Text-layer extraction, structure-not-layout. Fine for clean digital docs. | Free (local) | No |
| `--use-llm` (OpenRouter) | Adds LLM image descriptions + embedded-image OCR. | Per-call LLM cost | Yes — to OpenRouter/model provider |
| Azure DI (this doc) | Layout-faithful extraction; best for scanned pages, dense tables, multi-column filings. | ~$0.01/page (see below) | Yes — to Azure |

Reach for DI when the built-in output is garbled by layout (the SEC N-PX filing's interleaved footnotes are the canonical example) or when the source is genuinely scanned and you need more than image-level OCR.

## Provisioning (Azure side — done once, in the portal)

1. Create a **Document Intelligence** (Azure AI Services) resource in the Azure portal.
2. From the resource's **Keys & Endpoint** blade, copy the **endpoint** (`https://<name>.cognitiveservices.azure.com/`) and an **API key**.
3. It's a paid service billed per page; an `F0` free tier exists for low volume.

## markitdown mechanics (verified against the installed 0.1.5 source)

- Optional dependency: `pip install 'markitdown[az-doc-intel]'` (pulls `azure-ai-documentintelligence` + `azure-identity`).
- Enable by passing an endpoint to the constructor:
  ```python
  MarkItDown(
      docintel_endpoint="https://<name>.cognitiveservices.azure.com/",
      docintel_api_version="2024-11-30",   # see API-version note below
  )
  ```
  Additional optional kwargs the constructor forwards: `docintel_credential`, `docintel_file_types`, `docintel_api_version`.
- **Auth resolution** (in `DocumentIntelligenceConverter.__init__`): if `docintel_credential` is passed, it's used; else if env var **`AZURE_API_KEY`** is set it becomes an `AzureKeyCredential`; else it falls back to `DefaultAzureCredential()` (Entra ID / `az login` / managed identity). So the simplest path is endpoint + `AZURE_API_KEY` in the environment.
- When an endpoint is configured, the DI converter handles PDF, DOCX, PPTX, XLSX, JPEG, PNG, BMP, TIFF. It calls `model_id="prebuilt-layout"` with Markdown output.

### API-version gotcha

markitdown's DI converter **defaults `api_version` to `"2024-07-31-preview"`** — a preview that's superseded by the v4.0 **GA release `2024-11-30`**. Preview versions get retired after GA, so a wiring should explicitly pass `docintel_api_version="2024-11-30"` rather than rely on markitdown's stale default.

## Pricing (current, approximate)

markitdown uses the **Layout** model. Per Microsoft's pricing and 2026 summaries:

- **Read** model: ~$1.50 / 1,000 pages
- **Layout & prebuilt** models (what markitdown uses): ~$10 / 1,000 pages → **~$0.01/page**
- **Custom** extraction/classification: ~$50 / 1,000 pages
- Add-on features (query fields, key-value, barcode, formula) add ~20-30% surcharges
- High-volume commitment tier drops to ~$0.53 / 1,000 pages at ~8M pages/month
- `F0` free tier for low volume

So a 4-page filing like the N-PX is ~$0.04 via Layout. A 10,000-page corpus is ~$100. Budget by page count.

## Data handling (relevant to the C3 governance concern)

Per Microsoft's Document Intelligence data/privacy documentation:

- The analyze **result is stored ~24 hours** (encrypted, for async retrieval) and can be deleted earlier via the **Delete Analyze Result** API. Documents aren't retained permanently by default.
- **Microsoft does not use submitted documents to train its models.**
- Data is encrypted in transit and at rest (FIPS 140-2 256-bit AES) and tenant-isolated.

This is a materially stronger posture than a generic LLM API, which is why DI may be the more defensible choice than `--use-llm` for client/regulated documents — but it's still third-party egress and should be a conscious per-engagement call (same family as the C3 note in the gstack-codex-review of 0.1.0).

## Proposed wiring (NOT YET IMPLEMENTED)

When we build it, the shape that matches the existing `--use-llm` pattern:

- `/markitdown-setup` also installs `markitdown[az-doc-intel]`.
- A `--docintel` flag on `/markitdown-convert` + `convert.py`. It resolves endpoint + key from a vault env file (mirroring the OpenRouter key), e.g. `MoxyWolf Vault/_Shared Knowledge/Agents and Plugins/azure-docintel.env` holding `AZURE_DOCINTEL_ENDPOINT=` and `AZURE_API_KEY=`. The driver exports `AZURE_API_KEY` and passes `docintel_endpoint=<endpoint>` + `docintel_api_version="2024-11-30"`.
- Record `docintel: true` (and endpoint host) in the frontmatter + manifest, so it joins the settings-aware skip — turning DI on re-converts previously built files.
- DI and `--use-llm` can coexist (DI for layout, LLM for image descriptions), but for cost control they'd more likely be used one at a time.

## Open decisions before building

1. **Auth method** — API key via vault env (simplest, sandbox-friendly) vs Entra ID / `DefaultAzureCredential` (no key in files, but needs an Azure identity wherever conversion runs). Leaning key-via-vault for parity with OpenRouter, pending the research Dorian wants to do.
2. **Does MoxyWolf already have an Azure subscription / DI resource**, or is this net-new spend?
3. **Per-engagement data-egress policy** for client documents — is Azure DI's 24h/no-training posture acceptable where a generic LLM isn't?
4. **Default vs opt-in** — DI as an explicit `--docintel` flag (assumed) vs auto-fallback when built-in output looks degraded (more magic, harder to reason about cost).

## Sources

- [Azure Document Intelligence pricing — Microsoft](https://azure.microsoft.com/en-us/pricing/details/document-intelligence/)
- [Azure Document Intelligence pricing summary 2026 — aiproductivity.ai](https://aiproductivity.ai/pricing/azure-document-intelligence/)
- [What's new in Azure Document Intelligence (v4.0 GA 2024-11-30) — Microsoft Learn](https://learn.microsoft.com/en-us/azure/ai-services/document-intelligence/whats-new?view=doc-intel-4.0.0)
- [Data, privacy, and security for Document Intelligence — Microsoft Learn](https://learn.microsoft.com/en-us/legal/cognitive-services/document-intelligence/data-privacy-security)
