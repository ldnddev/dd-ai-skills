# dd-bar-chart

## Purpose
Dependency-free set of horizontal bars for comparing labelled values. Each row pairs a text label and value with a proportional bar, so trends read clearly without any charting library.

## Context
- Wraps in `dd-section`.
- For score breakdowns, category comparisons, and lightweight report visuals.
- Keep the row count modest so each bar and value stay legible.

## Required parameters
| name | type | description |
|---|---|---|
| `rows` | array | Each row: `label` (string), `value` (string, e.g. `"82/100"`), `pct` (number 0–100 for the fill width), optional `tone`. |
| `name` | string | Accessible name for the figure. Supply as a visible `caption` (preferred) **or** as `aria_label` when there is no caption. Never omit both. |

## Optional parameters
| name | type | default | description |
|---|---|---|---|
| `caption` | string | — | Visible `<figcaption>`. When set, the figure is named via `aria-labelledby` pointing at it. |
| `aria_label` | string | — | Used only when there is no visible caption. |
| `tone` (per row) | enum | — | `-good` `-warn` `-bad`. Omit for the neutral fill. |

## Variants (per row)
| modifier | tone | fill token |
|---|---|---|
| (none) | Neutral | `$c_text_secondary` |
| `-good` | Healthy | `$c_success_text` |
| `-warn` | Middling | `$c_warning_text` |
| `-bad` | Poor | `$c_error_text` |

## Canonical structure
```html
<!-- Named by the visible caption via aria-labelledby (no duplicated string). -->
<figure class="dd-bar-chart" role="group" aria-labelledby="{caption_id}">
  <figcaption class="dd-bar-chart__caption" id="{caption_id}">{caption}</figcaption>
  <ul class="dd-bar-chart__list">
    <li class="dd-bar-chart__row {tone}">
      <span class="dd-bar-chart__label">{label}</span>
      <span class="dd-bar-chart__track" aria-hidden="true"><span class="dd-bar-chart__fill" style="inline-size: {pct}%"></span></span>
      <span class="dd-bar-chart__value">{value}</span>
    </li>
    <!-- repeat per row -->
  </ul>
</figure>
```
When there is no visible caption, drop the `<figcaption>` and name the figure with `aria-label="{aria_label}"` instead of `aria-labelledby`.
See `dd-bar-chart.html`.

## Accessibility
**WCAG criteria touched:** 1.1.1, 1.3.1, 1.4.1 Use of Color, 1.4.10 Reflow, 1.4.11 Non-text Contrast, 2.3.3 Animation from Interactions.

- **Label + value text is the accessible truth.** The `__track` / `__fill` bars are decorative and marked `aria-hidden="true"`. Meaning never depends on bar length or color (1.4.1).
- The figure is a **`<figure role="group">`** with an accessible name — `aria-labelledby` → the visible `<figcaption>`, or `aria-label` when there is no caption. Never leave the group unnamed. The `role="group"` override of the implicit `figure` role is **intentional** (a named, navigable boundary); verify NVDA/VoiceOver announce the group name on entry. If AT support is inconsistent, drop `role="group"` and rely on native `figure`/`figcaption`.
- **Reflow (1.4.10):** the value is a grid sibling after the track and must never wrap or hide behind the bar at 320px width / 400% zoom. `__value` uses `white-space: nowrap` and the track absorbs the shrink via `minmax(0,1fr)`; below 30rem the row restacks (label+value on one line, full-width track below).
- **Non-text contrast (1.4.11):** the fill must clear 3:1 against the track. Tones use the semantic `*_text` tokens specifically to satisfy this.
- **Motion (2.3.3):** the fill grow-in transition is gated behind `prefers-reduced-motion: no-preference`. The resting width is the inline `style`, so reduced-motion users see the correct bar with no animation.

## Design tokens
| token | usage |
|---|---|
| `$c_text_primary` / `--dark` | label + value text |
| `$c_text_secondary` / `--dark` | caption; neutral fill |
| `$c_support_border` / `--dark` | track background |
| `$c_success_text` / `--dark` | `-good` fill |
| `$c_warning_text` / `--dark` | `-warn` fill |
| `$c_error_text` / `--dark` | `-bad` fill |

## JS hooks
None. Fill width is set inline via `style="inline-size:{pct}%"`.

## Example params
```json
{
  "caption": "Category scores",
  "rows": [
    { "label": "Performance", "value": "82/100", "pct": 82, "tone": "-good" },
    { "label": "Security", "value": "40/100", "pct": 40, "tone": "-bad" }
  ]
}
```

## Platform translation
**Static HTML:** Substitute rows. Generate a unique `caption_id` per chart. Use `aria-labelledby` when a caption exists, else `aria-label`.

**Drupal Twig (`dd-bar-chart.html.twig`):**
```twig
{% set cid = 'barchart-cap-' ~ id %}
<figure class="dd-bar-chart" role="group"
  {%- if caption %} aria-labelledby="{{ cid }}"{% else %} aria-label="{{ aria_label }}"{% endif %}>
  {% if caption %}<figcaption class="dd-bar-chart__caption" id="{{ cid }}">{{ caption }}</figcaption>{% endif %}
  <ul class="dd-bar-chart__list">
    {% for row in rows %}
    <li class="dd-bar-chart__row{% if row.tone %} {{ row.tone }}{% endif %}">
      <span class="dd-bar-chart__label">{{ row.label }}</span>
      <span class="dd-bar-chart__track" aria-hidden="true"><span class="dd-bar-chart__fill" style="inline-size: {{ row.pct }}%"></span></span>
      <span class="dd-bar-chart__value">{{ row.value }}</span>
    </li>
    {% endfor %}
  </ul>
</figure>
```

**WordPress (block render.php):**
```php
<?php
$caption = $attributes['caption'] ?? '';
$rows    = $attributes['rows'] ?? [];
$cid     = 'barchart-cap-' . esc_attr( $attributes['id'] ?? wp_unique_id() );
?>
<figure class="dd-bar-chart" role="group" <?php echo $caption ? 'aria-labelledby="' . $cid . '"' : 'aria-label="' . esc_attr( $attributes['aria_label'] ?? '' ) . '"'; ?>>
  <?php if ( $caption ) : ?><figcaption class="dd-bar-chart__caption" id="<?php echo $cid; ?>"><?php echo esc_html( $caption ); ?></figcaption><?php endif; ?>
  <ul class="dd-bar-chart__list">
    <?php foreach ( $rows as $row ) : ?>
    <li class="dd-bar-chart__row<?php echo ! empty( $row['tone'] ) ? ' ' . esc_attr( $row['tone'] ) : ''; ?>">
      <span class="dd-bar-chart__label"><?php echo esc_html( $row['label'] ); ?></span>
      <span class="dd-bar-chart__track" aria-hidden="true"><span class="dd-bar-chart__fill" style="inline-size: <?php echo (float) $row['pct']; ?>%"></span></span>
      <span class="dd-bar-chart__value"><?php echo esc_html( $row['value'] ); ?></span>
    </li>
    <?php endforeach; ?>
  </ul>
</figure>
```
