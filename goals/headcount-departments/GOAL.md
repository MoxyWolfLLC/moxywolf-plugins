## Serves
Tenth objective: external intake

## Outcome
Eight departments from headcount (`cbrock84/headcount` at `98d1c17`, MIT) are plugins in this marketplace: finance, people, it-operations, security, pmo, operations, corporate-strategy and customer-experience, 79 skills in all. Each department also ships a department agent that Claude can delegate work to; it starts from the department head's skill and loads the specialist skill the request needs. Dorian chose these eight on 2026-10-06 because the other eight headcount departments overlap plugins he already runs, and DR-011 says to curate overlap, not run two versions side by side. The skills are copied, not re-expressed, so each plugin carries the upstream MIT notice and says what was changed.

## Non-goals
- the other eight headcount departments (executive, technology, marketing, demand-generation, revenue, product, data-analytics, legal-risk)
- headcount's ChatGPT and Codex manifests, its verticals, its org chart and its build scripts
- rewriting the skills' advice or voice
- moving the marketplace's top-level version, which is the release bump after the goal merges

## Scenarios
- Given the goal branch, then the catalog check reads all 79 imported department skills and passes each one
- Given the goal branch, then the marketplace lists the eight department plugins, each with an agent file named for its department that loads its department head's skill
- An existing plugin's marketplace entry changing, or an existing skill failing the catalog check, must never happen

## Goal tests
- `tests/test_departments.py::Departments.test_catalog_check_passes_every_imported_skill` (outcome)
- `tests/test_departments.py::Departments.test_marketplace_lists_eight_departments_with_agents` (outcome)
- `tests/test_departments.py::Departments.test_existing_plugins_unchanged_and_passing` (invariant)

## Allowed paths
- plugins/finance/.claude-plugin/plugin.json
- plugins/finance/README.md
- plugins/finance/LICENSE
- plugins/finance/agents/finance.md
- plugins/finance/skills/budgeting-and-forecasting/SKILL.md
- plugins/finance/skills/budgeting-and-forecasting/references/sources.md
- plugins/finance/skills/capital-allocation/SKILL.md
- plugins/finance/skills/capital-allocation/references/sources.md
- plugins/finance/skills/capital-structure-and-covenants/SKILL.md
- plugins/finance/skills/capital-structure-and-covenants/references/sources.md
- plugins/finance/skills/chief-financial-officer/SKILL.md
- plugins/finance/skills/chief-financial-officer/references/sources.md
- plugins/finance/skills/cost-accounting/SKILL.md
- plugins/finance/skills/cost-accounting/references/sources.md
- plugins/finance/skills/financial-modeling/SKILL.md
- plugins/finance/skills/financial-modeling/references/sources.md
- plugins/finance/skills/financial-reporting-and-close/SKILL.md
- plugins/finance/skills/financial-reporting-and-close/references/sources.md
- plugins/finance/skills/financial-statement-analysis/SKILL.md
- plugins/finance/skills/financial-statement-analysis/references/sources.md
- plugins/finance/skills/internal-controls-and-audit/SKILL.md
- plugins/finance/skills/internal-controls-and-audit/references/sources.md
- plugins/finance/skills/revenue-recognition/SKILL.md
- plugins/finance/skills/revenue-recognition/references/sources.md
- plugins/finance/skills/tax/SKILL.md
- plugins/finance/skills/tax/references/sources.md
- plugins/finance/skills/treasury-and-liquidity/SKILL.md
- plugins/finance/skills/treasury-and-liquidity/references/sources.md
- plugins/finance/skills/unit-economics/SKILL.md
- plugins/finance/skills/unit-economics/references/sources.md
- plugins/people/.claude-plugin/plugin.json
- plugins/people/README.md
- plugins/people/LICENSE
- plugins/people/agents/people.md
- plugins/people/skills/benefits-and-leave/SKILL.md
- plugins/people/skills/benefits-and-leave/references/sources.md
- plugins/people/skills/chief-human-resources-officer/SKILL.md
- plugins/people/skills/chief-human-resources-officer/references/sources.md
- plugins/people/skills/compensation-and-leveling/SKILL.md
- plugins/people/skills/compensation-and-leveling/references/sources.md
- plugins/people/skills/employee-relations/SKILL.md
- plugins/people/skills/employee-relations/references/sources.md
- plugins/people/skills/employment-compliance/SKILL.md
- plugins/people/skills/employment-compliance/references/sources.md
- plugins/people/skills/hiring-and-interviewing/SKILL.md
- plugins/people/skills/hiring-and-interviewing/references/sources.md
- plugins/people/skills/learning-and-development/SKILL.md
- plugins/people/skills/learning-and-development/references/sources.md
- plugins/people/skills/onboarding-and-offboarding/SKILL.md
- plugins/people/skills/onboarding-and-offboarding/references/sources.md
- plugins/people/skills/org-design/SKILL.md
- plugins/people/skills/org-design/references/sources.md
- plugins/people/skills/payroll-operations/SKILL.md
- plugins/people/skills/payroll-operations/references/sources.md
- plugins/people/skills/performance-management/SKILL.md
- plugins/people/skills/performance-management/references/sources.md
- plugins/people/skills/workforce-planning/SKILL.md
- plugins/people/skills/workforce-planning/references/sources.md
- plugins/it-operations/.claude-plugin/plugin.json
- plugins/it-operations/README.md
- plugins/it-operations/LICENSE
- plugins/it-operations/agents/it-operations.md
- plugins/it-operations/skills/backup-and-recovery/SKILL.md
- plugins/it-operations/skills/backup-and-recovery/references/sources.md
- plugins/it-operations/skills/chief-information-officer/SKILL.md
- plugins/it-operations/skills/chief-information-officer/references/sources.md
- plugins/it-operations/skills/cloud-administration/SKILL.md
- plugins/it-operations/skills/cloud-administration/references/sources.md
- plugins/it-operations/skills/collaboration-platform-administration/SKILL.md
- plugins/it-operations/skills/collaboration-platform-administration/references/sources.md
- plugins/it-operations/skills/endpoint-management/SKILL.md
- plugins/it-operations/skills/endpoint-management/references/sources.md
- plugins/it-operations/skills/identity-lifecycle-administration/SKILL.md
- plugins/it-operations/skills/identity-lifecycle-administration/references/sources.md
- plugins/it-operations/skills/it-asset-management/SKILL.md
- plugins/it-operations/skills/it-asset-management/references/sources.md
- plugins/it-operations/skills/network-administration/SKILL.md
- plugins/it-operations/skills/network-administration/references/sources.md
- plugins/it-operations/skills/service-desk/SKILL.md
- plugins/it-operations/skills/systems-administration/SKILL.md
- plugins/it-operations/skills/systems-administration/references/sources.md
- plugins/it-operations/skills/telephony-and-conferencing/SKILL.md
- plugins/it-operations/skills/telephony-and-conferencing/references/sources.md
- plugins/it-operations/skills/virtualization-operations/SKILL.md
- plugins/it-operations/skills/virtualization-operations/references/sources.md
- plugins/security/.claude-plugin/plugin.json
- plugins/security/README.md
- plugins/security/LICENSE
- plugins/security/agents/security.md
- plugins/security/skills/access-and-identity/SKILL.md
- plugins/security/skills/access-and-identity/references/sources.md
- plugins/security/skills/chief-information-security-officer/SKILL.md
- plugins/security/skills/chief-information-security-officer/references/sources.md
- plugins/security/skills/data-protection-and-encryption/SKILL.md
- plugins/security/skills/data-protection-and-encryption/references/sources.md
- plugins/security/skills/detection-and-monitoring/SKILL.md
- plugins/security/skills/detection-and-monitoring/references/sources.md
- plugins/security/skills/incident-response/SKILL.md
- plugins/security/skills/incident-response/references/sources.md
- plugins/security/skills/security-architecture-review/SKILL.md
- plugins/security/skills/security-architecture-review/references/sources.md
- plugins/security/skills/threat-modeling/SKILL.md
- plugins/security/skills/threat-modeling/references/sources.md
- plugins/security/skills/vulnerability-management/SKILL.md
- plugins/security/skills/vulnerability-management/references/sources.md
- plugins/pmo/.claude-plugin/plugin.json
- plugins/pmo/README.md
- plugins/pmo/LICENSE
- plugins/pmo/agents/pmo.md
- plugins/pmo/skills/benefits-realization/SKILL.md
- plugins/pmo/skills/benefits-realization/references/sources.md
- plugins/pmo/skills/change-and-adoption/SKILL.md
- plugins/pmo/skills/change-and-adoption/references/sources.md
- plugins/pmo/skills/dependency-and-risk-management/SKILL.md
- plugins/pmo/skills/dependency-and-risk-management/references/sources.md
- plugins/pmo/skills/estimating-and-contingency/SKILL.md
- plugins/pmo/skills/estimating-and-contingency/references/sources.md
- plugins/pmo/skills/head-of-pmo/SKILL.md
- plugins/pmo/skills/head-of-pmo/references/sources.md
- plugins/pmo/skills/portfolio-governance/SKILL.md
- plugins/pmo/skills/portfolio-governance/references/sources.md
- plugins/pmo/skills/program-management/SKILL.md
- plugins/pmo/skills/program-management/references/sources.md
- plugins/pmo/skills/project-delivery/SKILL.md
- plugins/pmo/skills/project-delivery/references/sources.md
- plugins/pmo/skills/schedule-development-and-analysis/SKILL.md
- plugins/pmo/skills/schedule-development-and-analysis/references/sources.md
- plugins/operations/.claude-plugin/plugin.json
- plugins/operations/README.md
- plugins/operations/LICENSE
- plugins/operations/agents/operations.md
- plugins/operations/skills/business-continuity-and-resilience/SKILL.md
- plugins/operations/skills/business-continuity-and-resilience/references/sources.md
- plugins/operations/skills/capacity-and-demand-planning/SKILL.md
- plugins/operations/skills/capacity-and-demand-planning/references/sources.md
- plugins/operations/skills/chief-operating-officer/SKILL.md
- plugins/operations/skills/facilities-and-workplace/SKILL.md
- plugins/operations/skills/facilities-and-workplace/references/sources.md
- plugins/operations/skills/incident-management/SKILL.md
- plugins/operations/skills/incident-management/references/sources.md
- plugins/operations/skills/operating-cadence/SKILL.md
- plugins/operations/skills/process-design/SKILL.md
- plugins/operations/skills/process-design/references/sources.md
- plugins/operations/skills/procurement-and-sourcing/SKILL.md
- plugins/operations/skills/procurement-and-sourcing/references/sources.md
- plugins/operations/skills/quality-management/SKILL.md
- plugins/operations/skills/quality-management/references/sources.md
- plugins/operations/skills/service-level-management/SKILL.md
- plugins/operations/skills/service-level-management/references/sources.md
- plugins/operations/skills/supply-chain-and-logistics/SKILL.md
- plugins/operations/skills/supply-chain-and-logistics/references/sources.md
- plugins/operations/skills/vendor-management/SKILL.md
- plugins/operations/skills/vendor-management/references/sources.md
- plugins/corporate-strategy/.claude-plugin/plugin.json
- plugins/corporate-strategy/README.md
- plugins/corporate-strategy/LICENSE
- plugins/corporate-strategy/agents/corporate-strategy.md
- plugins/corporate-strategy/skills/chief-strategy-officer/SKILL.md
- plugins/corporate-strategy/skills/chief-strategy-officer/references/sources.md
- plugins/corporate-strategy/skills/market-entry/SKILL.md
- plugins/corporate-strategy/skills/market-entry/references/sources.md
- plugins/corporate-strategy/skills/mergers-and-acquisitions/SKILL.md
- plugins/corporate-strategy/skills/mergers-and-acquisitions/references/sources.md
- plugins/corporate-strategy/skills/portfolio-strategy/SKILL.md
- plugins/corporate-strategy/skills/portfolio-strategy/references/sources.md
- plugins/corporate-strategy/skills/scenario-planning/SKILL.md
- plugins/corporate-strategy/skills/strategic-alliances/SKILL.md
- plugins/customer-experience/.claude-plugin/plugin.json
- plugins/customer-experience/README.md
- plugins/customer-experience/LICENSE
- plugins/customer-experience/agents/customer-experience.md
- plugins/customer-experience/skills/chief-customer-officer/SKILL.md
- plugins/customer-experience/skills/customer-onboarding-and-implementation/SKILL.md
- plugins/customer-experience/skills/customer-onboarding-and-implementation/references/sources.md
- plugins/customer-experience/skills/customer-success-management/SKILL.md
- plugins/customer-experience/skills/escalation-management/SKILL.md
- plugins/customer-experience/skills/escalation-management/references/sources.md
- plugins/customer-experience/skills/self-service-and-knowledge/SKILL.md
- plugins/customer-experience/skills/self-service-and-knowledge/references/sources.md
- plugins/customer-experience/skills/support-operations/SKILL.md
- plugins/customer-experience/skills/support-operations/references/sources.md
- plugins/customer-experience/skills/voice-of-customer/SKILL.md
- .claude-plugin/marketplace.json

## Spend cap
$10

## Provider budgets
- openrouter: $6

## Max calls
40

## Max items
4

## Max review rounds per item
3

## Stop conditions
- any goal test regresses
- a change reaches a hooks folder or any other CODEOWNERS path
- the marketplace's top-level version moves on the goal branch
- a file from a headcount department outside the eight lands in the repository
- a deploy to any environment other than goal-holdout; the repository reports no other environment, so any deploy at all is Dorian's call

## Pre-mortem
- the skill folders exist but their text is truncated, paraphrased or copied from a different commit, so the catalog passes on content that isn't headcount's
- a skill still points at a department this marketplace doesn't carry (`legal-risk:...`, `revenue:...`, `technology:...`, `executive:...`, `marketing:...`), so the reference dangles when it loads
- the agents are one generic file renamed eight times and never load their department head's skill
- the MIT notice is missing or altered, so the copy breaks the license
- an overlapping department or the ChatGPT manifests come along with the eight
- a new marketplace entry reuses an existing plugin's name, or an existing entry's text changes in the edit
