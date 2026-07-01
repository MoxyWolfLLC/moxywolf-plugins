---
name: design-taste
description: >
  This skill should be used when the user says "make it not look AI-generated",
  "give it taste", "it looks generic", "it looks templated", "anti-slop",
  "before you build the page", "set the design direction", "avoid the AI defaults",
  or any request to establish design intent BEFORE generating or polishing a
  frontend. This is the anti-slop inference gate: it forces a Design Read, sets
  three tunable dials, and bans the LLM design defaults. Generation lives in the
  `frontend-design` skill; polish and audit live in `baseline-ui`. Run this first.
version: 1.0.0
---

# Design Taste - The Anti-Slop Inference Gate

> Adapted by MoxyWolf LLC (2026-06-30) from [taste-skill](https://github.com/Leonxlnx/taste-skill) (MIT, (c) 2026 Leonxlnx). The Design Read, the three dials, the anti-default discipline, and the em-dash ban below are adapted from taste-skill's `design-taste-frontend`. See the plugin `NOTICE`.

This is the **upstream gate** for every frontend task in this plugin. It runs before code, not instead of it. It carries only the inference and discipline layer that decides *what* to build; the actual work lives elsewhere:

- **Generate new UI** → the `frontend-design` skill.
- **Polish / audit existing UI** → the `baseline-ui` skill (its two-altitude AI-slop test is the surface-pattern catch; this gate is the intent catch).

Most AI design output is bad because the model jumps to a default aesthetic instead of reading the room. Run this gate to stop that.

## 1. The Design Read (declare intent before any code)

Read the signals first: page kind (landing / portfolio / redesign / editorial), the vibe words the user used, any reference URLs or products they named, the audience (the audience picks the aesthetic, not your taste), brand assets that already exist, and any quiet constraints (accessibility-critical, public-sector, regulated, trust-first commerce) which **override** aesthetic preference.

Then state it in one line before generating:

> **"Reading this as: \<page kind> for \<audience>, with a \<vibe> language, leaning toward \<design system or aesthetic family>."**

If the brief is genuinely ambiguous, ask exactly **one** clarifying question, never a multi-question dump. If you can infer confidently from context, do not ask. Just declare the read and proceed.

## 2. The Three Dials (set them, reason them)

After the read, set three dials. They gate layout, motion, and density downstream.

- **`DESIGN_VARIANCE`** - 1 = perfect symmetry, 10 = artsy chaos
- **`MOTION_INTENSITY`** - 1 = static, 10 = cinematic / physics
- **`VISUAL_DENSITY`** - 1 = art gallery / airy, 10 = cockpit / packed data

**Baseline: `8 / 6 / 4`.** Use the baseline unless the read overrides it. Never silently ship the baseline without reasoning it against the brief.

### Dial inference (read → values)

| Signal | VARIANCE | MOTION | DENSITY |
|---|---|---|---|
| minimalist / clean / calm / editorial / Linear-style | 5-6 | 3-4 | 2-3 |
| premium consumer / Apple-y / luxury / brand | 7-8 | 5-7 | 3-4 |
| playful / wild / Dribbble / Awwwards / experimental / agency | 9-10 | 8-10 | 3-4 |
| landing page / portfolio / marketing (default) | 7-9 | 6-8 | 3-5 |
| trust-first / public-sector / regulated / accessibility-critical | 3-4 | 2-3 | 4-5 |
| SaaS dashboard / data-heavy app UI | 3-5 | 2-4 | 6-8 |

## 3. Anti-Default Discipline

Do not default to the LLM tells: AI-purple gradients, a centered hero over a dark mesh, three equal feature cards, generic glassmorphism on everything, infinite-loop micro-animations everywhere, Inter + slate-900. Reach past them deliberately based on the design read. (The full surface-pattern ban list lives in `baseline-ui`'s slop test; run it during polish.)

**Category-reflex test:** if someone could guess the theme and palette from the category alone, it is the first training-data reflex. Rework until the aesthetic is not obvious from the domain.

## 4. The Em-Dash Ban (non-negotiable)

**Em-dash (`—`) is completely banned in all user-visible output.** No "limited use," no "in body copy is fine." It is the #1 visual Tell in production tests and it matches the MoxyWolf house voice profile. The em-dash is forbidden in headlines, eyebrows, pills, button text, body copy, quotes, attribution, captions, nav items, and alt text. The en-dash (`–`) as a separator is banned too; ranges use a regular hyphen (`2018-2026`, `€40-80k`).

The only permitted dash on the page is the regular hyphen `-` (compound words, ranges, dividers) and the math minus sign. A single `—` or `–` anywhere visible means the output fails pre-flight and must be rewritten.

## 5. Pre-Flight Gate (the intent checks)

Run these before handing off to generation or polish. These are the intent-level boxes; `baseline-ui`'s pre-flight covers the surface-craft boxes (contrast, spacing, motion cleanup, real images). Do not skip either.

- [ ] **Design Read declared** - the one-liner is stated, not assumed.
- [ ] **Dials set and reasoned** - explicit values justified against the brief, not a silent baseline.
- [ ] **Design system chosen** - a real system when applicable, or the aesthetic labeled honestly.
- [ ] **Redesign mode detected** - if the task is a redesign, an audit ran first (hand to `baseline-ui`).
- [ ] **Zero em-dashes** - none anywhere user-visible (Section 4).
- [ ] **Not the category reflex** - the aesthetic is not guessable from the domain alone (Section 3).

If any box cannot be honestly ticked, the direction is not set. Fix it before writing code.
