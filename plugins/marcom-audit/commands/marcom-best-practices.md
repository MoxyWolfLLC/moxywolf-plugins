---
description: Find the best practices for a MARCOM target by sweeping our installed toolbox, the Workforce Automation tool catalog (capabilities we don't have yet), and external research — then benchmark our current practice and recommend. Usage: /marcom-best-practices [target]
---

Run the `marcom-best-practices` skill for the target the user names (a MARCOM project, idea, channel, campaign, or funnel stage — e.g. "our onboarding email sequence", "the OpenControls launch", "LinkedIn thought-leadership").

The premise is that we're probably doing it wrong and want the full toolbox consulted before changing direction. The skill:

1. Classifies the target into MARCOM domains (lifecycle email/outreach is expanded into onboarding → nurturing → upgrade → retention, not one bucket).
2. Sweeps three tiers — our installed plugins/skills, the Workforce Automation Supabase catalog of ~580K ecosystem tools (to recommend capabilities we don't have), and heavy external web research.
3. Benchmarks MoxyWolf's current practice against what it finds, using live analytics where available.
4. Writes a prioritized best-practices brief to the target's `12 – MARCOM/` folder, lists adoption candidates, and auto-runs the top applicable installed skills to produce starter deliverables.

If the user didn't name a target, ask for it (plus goal/metric and product line) before sweeping. Follow the full skill instructions in `skills/marcom-best-practices/SKILL.md`.
