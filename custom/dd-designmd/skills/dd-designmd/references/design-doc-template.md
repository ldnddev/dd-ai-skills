# {domain} — Semantic Design System

Every token and component claim must cite evidence (CSS rule, HTML structure, or deep-mode sample). Do not invent brand, voice, or values.

## Meta
Primary URL, domain, date, pages scanned, evidence mode, confidence.

## Overview
Evidence-only product/brand context. If a field is not on-site, write *not stated on scanned pages*.

### Product summary
One short paragraph from title / H1 / meta description / on-page copy.

### Brand style
Visual register from CSS/HTML (density, contrast, geometry, chrome). No personality fiction.

### Brand tone
Observed copy register (headline case, CTA verbs, formality) or quoted on-site voice guidelines — not an invented voice chart.

### Core visual principles
3–5 bullets derived from measured Layout, Elevation, Color, and Type.

## Logo & brand mark
Detected wordmark / icon assets. Clear space, on-light / on-dark, and minimum size **only** if those rules or variants appear on-site.

## Foundations
### Color
### Typography
### Motion
### Breakpoints

Layout, spacing, radius, and elevation are first-class sections below — do not duplicate those tables here.

## Layout & Spacing
Grid systems, padding rules, and container constraints.

### Grid
### Padding
### Containers

## Elevation & Shapes
Surface layering, shadows, and radii.

### Surfaces
### Shadows
### Radius
### Z-index

## Semantic tokens
## Color usage rules
When to use each semantic color, contrast pairs, and forbidden combinations. Palette ranks are not roles.

## Components
## Interactive states
Shared hover / focus / active / disabled / loading / visited treatments. Empty state = do not invent it. Focus ring details stay in Focus & keyboard.

## Patterns / page templates
## Iconography & media
## Content & copy patterns
Heading case, CTA verbs, and UI microcopy from on-page samples — not an invented voice chart.

## Focus & keyboard
Observed `:focus` / outline treatment as facts only (no a11y scores). Never `outline: none` without a documented replacement.

## Do / Don’t
Process rules (no invented tokens/rebrand) **and** site-specific generation constraints that stop common AI UI mistakes (e.g. no gradients if none exist; always pair error text with a non-color indicator).

## Implementation notes
## ldnddev Framework mapping
## Agent instructions
Final prompt context: how a coding agent must interpret this file when writing UI (tokens over raw values; Do/Don’t are hard rules; never invent missing tokens).

## Open questions & missing evidence
## Appendix — evidence samples
