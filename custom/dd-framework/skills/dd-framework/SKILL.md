---
name: dd-framework
description: Source of truth for the ldnddev Framework component system. Provides canonical component contracts (required/optional params, BEM classes, WCAG 2.2 AA accessibility rules, design tokens) plus a Python helper CLI for listing, fetching, and validating components. Consumed by AI agents and other skills (dd-blogs, page-builders) to author static HTML, Drupal Twig, or WordPress block markup that uses dd-framework components correctly. This skill does not render — render is the consumer CMS's job.
license: MIT
metadata:
    author: Jared Lyvers (ldnddev.com)
    version: 2.0.0
---

# dd-framework — Component Contracts for the ldnddev Framework

## Purpose

dd-framework provides AI agents with the **contract** for using ldnddev Framework components: required params, BEM class structure, accessibility rules, design tokens, and platform translation guidance. Consumers (dd-blogs, future page-builder skills, external Codex/Cursor agents) read the contracts and emit platform-correct markup for static HTML sites, Drupal sites, or WordPress sites.

**This skill is reference + validation, not render.** A Python renderer for in-process substitution would not help: Drupal renders its own Twig, WordPress renders its own PHP/blocks, static sites copy markup verbatim. Each consumer renders natively.

## When to use this skill

- An agent is adding, modifying, or auditing markup that uses `dd-*` classes.
- A consumer skill needs to enumerate available components, fetch a spec, or validate emitted HTML.
- A user asks "add a dd-hero", "build a card grid", "wrap this in a section", etc.

## Trigger phrases

- "add a dd-hero with..."
- "build a 3-column dd-card grid"
- "wrap this in a dd-section"
- "update the hero on /about"
- "validate this page against dd-framework"

## Components (22 total)

| Name | Wraps in `dd-section`? | Required params | Variants |
|---|---|---|---|
| `dd-accordion` | yes | `items` | — |
| `dd-alert` | yes | `heading`, `copy` | `-info` `-success` `-warning` `-error` |
| `dd-alternating` | yes | `items` | — |
| `dd-badge` | **no** | `label` | `-critical` `-warning` `-info` `-pass` |
| `dd-banner` | **no** | `image_src`, `image_alt` | — |
| `dd-bar-chart` | yes | `rows`, `name` | `-good` `-warn` `-bad` |
| `dd-blockquote` | yes | `quote`, `name` | — |
| `dd-card` | yes | `items` | `-horizontal` |
| `dd-cookie-consent` | **no** | — | — |
| `dd-cta` | **no** | `title`, `image_src`, `image_alt` | `-top-left` `-top-right` `-bottom-left` `-bottom-right` `-center` |
| `dd-data-table` | yes | `caption`, `columns`, `rows` | `-dense` |
| `dd-filmstrip` | yes | `items` | `-reverse` |
| `dd-finding` | yes | `items` | `-critical` `-warning` `-info` `-pass` |
| `dd-hero` | **no** | `title`, `image_src`, `image_alt` | — |
| `dd-milestones` | yes | `items` | — |
| `dd-modal` | **no** | `id`, `content` | — |
| `dd-score-ring` | yes | `score`, `max`, `label` | `-sm` `-lg` `-good` `-warn` `-bad` `-link` |
| `dd-section` | **no** | `content` | `-full-contained` `-full-bleed` `-narrow` |
| `dd-slider` | yes | `title`, `slides` | — |
| `dd-spacer` | **no** | `size` | `-sm` `-md` `-lg` `-xl` `-xxl` `-xxxl` `-divider` |
| `dd-tabs` | yes | `id`, `tabs` | — |
| `dd-timeline` | yes | `items` | — |

Full per-component contract lives in `assets/components/dd-{name}.spec.md`. Static HTML examples live in `assets/components/dd-{name}.html`. Index in `assets/components.manifest.json`.

## Helper CLI

The Python helper is the programmatic interface for other skills. JSON output by default; `--human` flag for prose. Strict validation by default; `--warn` makes findings non-fatal.

```bash
# Path to helper (resolve from this skill's install location)
DD=$(find . -path '*/dd-framework/skills/dd-framework/scripts/dd_framework_helper.py' | head -1)

# Enumerate components
python3 "$DD" list                           # JSON
python3 "$DD" list --human                   # prose

# Fetch a component
python3 "$DD" get dd-hero                    # spec + html + params (JSON)
python3 "$DD" get dd-hero --section spec     # just the spec.md
python3 "$DD" get dd-hero --section html     # just the HTML example
python3 "$DD" get dd-hero --section params   # just the params schema
python3 "$DD" get dd-hero --human            # prose

# Validate an HTML file
python3 "$DD" validate page.html             # exit 1 on errors
python3 "$DD" validate page.html --warn      # exit 0 (advisory)
python3 "$DD" validate page.html --human     # prose report
```

Deps: `beautifulsoup4` (for `validate` only — `list` and `get` are stdlib).

## Cross-skill invocation

Three ways for other skills to consume dd-framework:

**1. Skill tool invocation** (Claude Code) — load this skill, follow its instructions.

**2. Direct file read** — read `assets/components.manifest.json` and `assets/components/dd-{name}.spec.md` directly. Suitable when the consumer needs structured data without the helper.

**3. Helper shell-out** — call `python3 dd_framework_helper.py list|get|validate ...` from a consumer's own script. Pipe JSON output into the consumer's logic. This is how `dd-blogs/scripts/blog_helper.py` integrates.

Graceful degrade: consumers should detect dd-framework absence (missing helper path or manifest) and continue with reduced functionality (no validate, fall back to a built-in static fallback for the components they need).

## Platform translation guide

Each spec file ends with platform translation snippets. General rules:

**Static HTML** — substitute params directly into the canonical structure. Loop arrays in your build pipeline (Eleventy, Astro, etc.). No build step required for the markup itself.

**Drupal** — render the canonical structure as a Twig component (`themes/custom/{theme}/templates/components/dd-{name}.html.twig`). Pair with a `.libraries.yml` declaring CSS/JS dependencies. Pass params as a render array from the consuming module / paragraph type / layout builder block.

**WordPress** — implement as a Gutenberg block (`block.json` + `render.php`) OR as an ACF Flexible Content row. Escape per field type: `esc_url` (URLs), `esc_attr` (attributes), `esc_html` (plain text), `wp_kses_post` (rich text). Enqueue framework CSS/JS once in `theme.js` / via `wp_enqueue_scripts`.

For each component, the spec file's "Platform translation" section provides concrete Twig and PHP examples.

## Color system & a11y baseline

Tokens (light / dark mode pairs):

| Role | Base hex | Light surface | Dark surface |
|---|---|---|---|
| Primary | `#88d9f7` | `$c_primary_default` | `$c_primary_default--dark` |
| Secondary | `#ffca76` | `$c_secondary_default` | `$c_secondary_default--dark` |
| Tertiary | `#f98971` | `$c_tertiary_default` | `$c_tertiary_default--dark` |
| Support | `#46be8c` | `$c_support_*` | `$c_support_*--dark` |
| Text primary | — | `#1c1e21` | `#f5f6f7` |
| Text secondary | — | `#5a5f66` | `#9ea3aa` |

Full token map in `references/Agent-UI-Colors.md` and `references/Agent-UI-Theme-Builder.md`.

**Accessibility baseline (per component):**
- Contrast: ≥ 4.5:1 for normal text, ≥ 3:1 for large text (1.4.3); ≥ 3:1 for non-text (1.4.11)
- Focus visible: 2px solid outline minimum (2.4.7); never `outline: none` without a replacement
- Reduced motion: animations (AOS, sliders, marquees, counters) honor `prefers-reduced-motion: reduce`
- Keyboard: every interactive element reachable and operable via keyboard alone (2.1.1); no keyboard traps (2.1.2)
- Names: every interactive element has an accessible name (4.1.2)
- Target size: interactive controls ≥ 24×24 CSS px (2.5.8 AA)

Per-component WCAG criteria are listed in each spec's Accessibility section.

## Validation in CI / dev loop

Run `validate` against built HTML files to catch component misuse:

```bash
# In a build pipeline
for f in dist/*.html; do
  python3 dd_framework_helper.py validate "$f" || exit 1
done

# Pre-commit hook
python3 dd_framework_helper.py validate --warn page.html
```

`validate` catches:
- Unknown `dd-*` classes (typos)
- Missing structural children (`__items` / `__content`)
- `dd-hero` without `aria-label` / `aria-labelledby` or `<h1>`
- `dd-card` `<img>` missing `alt`
- `dd-alert -warning/-error` missing `role="alert"`
- `dd-alert` with conflicting `role` + `aria-live`
- `dd-modal` not using `<dialog>`
- `dd-tabs` using `<a>` instead of `<button>`, or `aria-selected` not `"true"`/`"false"`
- `dd-section` without accessible name
- `dd-cookie-consent` using `role="dialog"` with `aria-modal="false"`
- `dd-filmstrip` using `<figure>` as caption (should be `<figcaption>`)

It does NOT catch semantic correctness (is the alt text meaningful?), color contrast at runtime, or motion-related issues. Pair with `dd-a11y` skill for full WCAG audits via Playwright + axe-core.

## Layout

```
dd-framework/
├── .claude-plugin/plugin.json
├── install.sh
├── README.md
└── skills/dd-framework/
    ├── SKILL.md                          ← you are here
    ├── references/
    │   ├── Agent-UI-Colors.md
    │   └── Agent-UI-Theme-Builder.md
    ├── scripts/
    │   ├── dd_framework_helper.py        ← CLI
    │   ├── test_dd_framework_helper.py   ← pytest
    │   └── requirements.txt              ← beautifulsoup4, pytest
    └── assets/
        ├── components.manifest.json      ← index of all 22 components
        └── components/
            ├── dd-{name}.html            ← static HTML reference
            └── dd-{name}.spec.md         ← contract: params, a11y, tokens, translation
```

## Build commands (consumer-side, for ldnddev's own sites)

When working inside an ldnddev project that uses Lando:

```bash
lando grunt build       # full build
lando grunt dev         # dev build with watch
lando grunt sync        # sync assets to web/
```

These commands belong to the consumer project, not to dd-framework itself. dd-framework ships no build artifacts.

## Troubleshooting

- **Helper command not found** — install via `bash install.sh` or `/plugin install dd-framework@dd-skills`. Verify `scripts/dd_framework_helper.py` exists.
- **`validate` fails with "beautifulsoup4 required"** — `pip install -r scripts/requirements.txt`.
- **Unknown component error from `get`** — run `list` to see the 22 valid names. Class typos like `dd-hreo` won't match.
- **`validate` reports unknown `dd-*` class** — either the class is a typo, or it's a custom component not in dd-framework. Either fix the typo or accept the warning.
