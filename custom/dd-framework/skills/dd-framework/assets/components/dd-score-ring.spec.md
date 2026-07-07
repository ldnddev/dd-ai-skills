# dd-score-ring

## Purpose
Radial SVG donut gauge that displays a score against a maximum, with a visible number and a short label. An arc sweeps proportionally to the value to give an immediate sense of completeness.

## Context
- Wraps in `dd-section` (typically several rings in a grid for KPI comparison).
- For audit scores, health indicators, and KPI summaries.
- Two forms: static **figure** form, or navigable **`-link`** anchor form.

## Required parameters
| name | type | description |
|---|---|---|
| `score` | number | The value. Rendered as visible `__num` text AND inside the accessible name. |
| `max` | number | The maximum (e.g. 100). |
| `label` | string | Short caption under the ring (`__label`). |

## Optional parameters
| name | type | default | description |
|---|---|---|---|
| `tone` | enum | — | `-good` `-warn` `-bad`. Arc color only; omit for neutral. |
| `size` | enum | — | `-sm` `-lg`. Omit for default. |
| `sub` | string | — | Secondary line (`__sub`) — e.g. "13 checks" or the link's action text. |
| `href` | string | — | When set, renders the `-link` anchor form. Requires `link_action`. |
| `link_action` | string | `View details` | Appended to the anchor's accessible name (e.g. "…View details"). |
| `dashoffset` | number | computed | `stroke-dashoffset` for the arc; computed from `score`/`max` against the `stroke-dasharray` circumference (263.9 for r=42). |

## Variants
| modifier | effect |
|---|---|
| `-sm` / `-lg` | Smaller / larger SVG. |
| `-good` / `-warn` / `-bad` | Arc stroke tone. |
| `-link` | Anchor form; whole gauge is navigable. |

## Canonical structure
**Figure form** — the SVG carries the accessible name:
```html
<div class="dd-score-ring {tone} {size}">
  <svg class="dd-score-ring__svg" viewBox="0 0 100 100" role="img" aria-label="{label}: {score} out of {max}">
    <circle class="dd-score-ring__track" cx="50" cy="50" r="42" fill="none" />
    <circle class="dd-score-ring__value" cx="50" cy="50" r="42" fill="none" stroke-dasharray="263.9" stroke-dashoffset="{dashoffset}" transform="rotate(-90 50 50)" />
    <text class="dd-score-ring__num" x="50" y="54" text-anchor="middle" aria-hidden="true">{score}</text>
  </svg>
  <div class="dd-score-ring__label">{label}</div>
  <div class="dd-score-ring__sub">{sub}</div><!-- optional -->
</div>
```
**Link form** — the `<a>` owns the name, the SVG is decorative:
```html
<a class="dd-score-ring {tone} -link" href="{href}" aria-label="{label}: {score} out of {max}. {link_action}">
  <svg class="dd-score-ring__svg" viewBox="0 0 100 100" aria-hidden="true"> … same circles … </svg>
  <div class="dd-score-ring__label">{label}</div>
  <div class="dd-score-ring__sub">{link_action}</div>
</a>
```
See `dd-score-ring.html`.

## Accessibility
**WCAG criteria touched:** 1.1.1 Non-text Content, 1.4.1 Use of Color, 2.3.3 Animation from Interactions, 2.4.7 Focus Visible, 2.5.8 Target Size (Minimum).

- **The visible number + label is the accessible truth** (1.1.1 / 1.4.1). Meaning never depends on arc length or tone color; the score is always present as visible text.
- **Figure form:** the SVG has `role="img"` + `aria-label` stating score and max. The `__num` text is `aria-hidden="true"` to avoid a duplicate announcement.
  - *Refinement (optional):* the visible `__label` already names the ring in reading order, so embedding the category in the SVG name too ("Performance: 82 out of 100") double-speaks "Performance". For a ring that always sits next to its `__label`, prefer a value-only SVG name — `aria-label="82 out of 100"` — and let `__label` carry the category. Keep the category in the SVG name only when the ring can appear detached from its label.
- **Link form:** the `<a>` owns the accessible name (score, max, and action). The SVG is `aria-hidden="true"` so there is exactly one announcement. Do NOT put `role="img"` on the SVG in this form.
- **Exactly one accessible name.** Never emit both an `aria-label` SVG and a named link — pick the form.
- **Motion (2.3.3):** the arc grow-in transition is gated behind `prefers-reduced-motion: no-preference`. The resting `stroke-dashoffset` is the inline attribute, so reduced-motion users see the correct arc with no animation.
- **Target size (2.5.8):** the `-link` form guarantees a ≥24×24px hit area and a visible `:focus-visible` outline that clears 3:1 in both themes (uses `$c_text_primary`, not brand green which fails 3:1 in light).

## Design tokens
| token | usage |
|---|---|
| `$c_text_primary` / `--dark` | number, label, focus outline |
| `$c_text_secondary` / `--dark` | sub text; neutral arc |
| `$c_support_border` / `--dark` | track ring |
| `$c_success_text` / `--dark` | `-good` arc |
| `$c_warning_text` / `--dark` | `-warn` arc |
| `$c_error_text` / `--dark` | `-bad` arc |

## JS hooks
None. `dashoffset` is a server-computed inline attribute: `dashoffset = 263.9 * (1 - score/max)` for `r=42`.

## Example params
```json
{ "score": 82, "max": 100, "label": "Performance", "tone": "-good", "sub": "13 checks", "dashoffset": 47.5 }
```
Link form:
```json
{ "score": 40, "max": 100, "label": "Security", "tone": "-bad", "href": "#section-security", "link_action": "View details", "dashoffset": 158.3 }
```

## Platform translation
**Static HTML:** Pick figure vs link form by presence of `href`. Compute `dashoffset` from `score`/`max`. Figure form: `role="img"` + `aria-label` on the SVG, `__num` aria-hidden. Link form: name on the `<a>`, SVG `aria-hidden`.

**Drupal Twig / WordPress:** Branch on `href`. Compute `dashoffset = 263.9 * (1 - score / max)`. In the figure branch emit `role="img"` + `aria-label="{{ label }}: {{ score }} out of {{ max }}"` on the SVG; in the link branch emit the name on the `<a>` and `aria-hidden="true"` on the SVG. Never emit both accessible names.
