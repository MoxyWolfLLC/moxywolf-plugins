---
name: daily-ops-deprecated-in-bundle
description: This skill has moved out of the moxywolf-skills bundle. Install the standalone `daily-ops` plugin from the same marketplace instead. Do NOT trigger this skill — it exists only as a redirect.
---

# daily-ops has moved

This skill used to ship as part of the `moxywolf-skills` bundle. As of bundle v1.1.0 it has been removed in favor of the standalone `daily-ops` plugin in the same marketplace — having two copies meant feature drift between them and made the connector migration painful.

## Install the real one

```
Cowork → Personal plugins → + → Add from marketplace → MoxyWolfLLC/moxywolf-plugins → daily-ops
```

Or via CLI:

```
claude plugin install daily-ops@moxywolf-plugins
```

## When this folder can be deleted

This SKILL.md and its parent directory can be safely removed in a follow-up commit once you've confirmed nothing references the bundle's `skills/daily-ops/` path. The redirect exists to avoid a silent disappearance for any tooling or notes that pointed at it.
