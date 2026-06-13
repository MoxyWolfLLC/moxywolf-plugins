# Frontier Founder SMB (FFSMB)

Pre-built small-business workflows for Cowork — run your whole business in plain English, with an approval gate on anything that touches money or customers. A MoxyWolf-owned public fork of Anthropic's **Small Business** plugin, re-homed from its original stack onto a modern indie-founder stack.

> **Build status: v0.1.0 — scaffold + front door.** Connector decisions are locked (below) and the router/onboarding skills are rewritten. The remaining skill bodies are being migrated off the original connectors per the rewrite spec (`Taskade/Team Plugins/06 – Engineering/smb-plugin-fork-connector-rewrite-spec.md`). Not yet install-ready.

## The stack

| Job | Connector | Notes |
|---|---|---|
| CRM | **Clarify AI** | `https://api.clarify.ai/mcp` — contacts, companies, deals, tasks, pipeline; native `find-leads` over 28M companies / 175M people |
| Payments | **Stripe** | invoicing, refunds, disputes, Tap to Pay on iPhone |
| Accounting | **QuickBooks** | system of record for margin / reconciliation |
| E-signature | **DocuSign** | contracts, offer letters |
| Email · Calendar · Files | **Google** (Gmail / Calendar / Drive) | Microsoft 365 auto-detect is a phase-1.5 follow-up |
| Design | **claude.ai/design** | driven in-session, not an MCP connector |

Swapped out from the Anthropic original: PayPal → Stripe; HubSpot → Clarify; Canva → claude.ai/design; **Square removed** (Stripe Tap to Pay on iPhone covers iPhone-native card-present). Rationale: [PD-001](../../) (Council GTM deliberation).

## What it does

Money: `/plan-payroll` · `/month-heads-up` · `/close-month` · `/price-check` · `/tax-prep`
Customers: `/call-list` · `/run-campaign` · `/sales-brief` · `/customer-pulse-check` · `/handle-complaint` · `/crm-cleanup`
Contracts & hiring: `/review-contract` · `/job-post-builder`
Your week: `/monday-brief` · `/friday-brief` · `/quarterly-review`
Getting started: just say "set me up" → `smb-onboard`. Not sure where to begin? `smb-router` is the concierge.

Every step that moves money or messages a customer asks for your approval first.

## Companion: Apollo for B2B prospecting

FFSMB manages the funnel you have. For *acquiring* net-new B2B customers beyond Clarify's built-in `find-leads`, install the **Apollo** plugin (`apollo:prospect`, `apollo:enrich-lead`, `apollo:sequence-load`) — deeper enrichment and multi-step outbound sequences. FFSMB's CRM skills optionally call Apollo enrichment when a Clarify contact is missing fields; `smb-router` recommends it when your need is "find new customers." Two Frontier Founder plugins that compose.

## Credit

Forked from Anthropic's Small Business plugin (Cowork marketplace). MoxyWolf re-homed the connectors and re-branded; the workflow design and skill structure originate with Anthropic.

## Versioning

- **0.1.0** — fork scaffold: branding, connector manifest (Clarify/Stripe/QuickBooks/DocuSign/Google/Slack), README, rewritten `smb-router` + `smb-onboard`. Remaining skill bodies in progress.
