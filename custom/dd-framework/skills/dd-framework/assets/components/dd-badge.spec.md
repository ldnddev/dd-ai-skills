# dd-badge

## Purpose
Compact, non-interactive pill that communicates a status or severity level at a glance — critical, warning, info, pass, or neutral. Color-coded surface pairs with a short text label for fast, scannable recognition.

## Context
- Does NOT wrap in `dd-section`. It is an inline element placed next to titles, inside table cells (`dd-data-table`), or inside list items (`dd-finding`).
- Non-interactive: no `role`, no `tabindex`, no focus, no click handler. For an interactive status control use a `<button>`, not a badge.
- Embedded by `dd-data-table` (status column) and `dd-finding` (severity marker).

## Required parameters
| name | type | description |
|---|---|---|
| `label` | string | Visible text; carries the meaning. Keep short and unambiguous. |

## Optional parameters
| name | type | default | description |
|---|---|---|---|
| `variant` | enum | — | `-critical` `-warning` `-info` `-pass`. Omit for the neutral variant. |
| `icon` | string (emoji/glyph) | — | Decorative leading glyph. Rendered `aria-hidden="true"`. Never the sole carrier of meaning. |

## Variants and severity mapping
| modifier | meaning | token family |
|---|---|---|
| (none) | Neutral / unclassified | `$c_ui_neutral_200` surface |
| `-info` | Informational | `$c_info_*` |
| `-pass` | Passing / healthy | `$c_success_*` |
| `-warning` | Cautionary | `$c_warning_*` |
| `-critical` | Most severe | `$c_error_*` |

Severity mapping matches `dd-alert` (critical→error, pass→success).

## Canonical structure
```html
<span class="dd-badge {variant}">
  {icon ? '<span class="dd-badge__icon" aria-hidden="true">{icon}</span>' : ''}<span class="dd-badge__label">{label}</span>
</span>
```
- `{variant}` is one of the modifiers or empty.
- `{icon}` span is emitted only when an icon is supplied, and is always `aria-hidden="true"`.
See `dd-badge.html` for all variants.

## Accessibility
**WCAG criteria touched:** 1.1.1 Non-text Content, 1.4.1 Use of Color, 1.4.3 Contrast.

- **Meaning is in the `__label` text, never color alone** (1.4.1). The badge reads correctly in greyscale and to color-blind users because the severity word ("Critical", "Warning") is spelled out.
- `__icon` is **decorative** — always `aria-hidden="true"`. It reinforces, never replaces, the label. Do not put the only status cue in an emoji.
- Non-interactive: emit **no** `role`, `tabindex`, or focus styling. A badge is not a button or a link.
- Contrast: `__label` text must meet 4.5:1 against the variant surface in both light and dark mode. `-warning` (yellow tones) is highest-risk — verify against `$c_warning_text`.
- The border is decorative (no interactive state), so 1.4.11 Non-text Contrast does not apply to it.

## Design tokens
| token | usage |
|---|---|
| `$c_ui_neutral_200` / `--dark` | neutral surface |
| `$c_info_surface` / `_border` / `_text` (+`--dark`) | `-info` |
| `$c_success_surface` / `_border` / `_text` (+`--dark`) | `-pass` |
| `$c_warning_surface` / `_border` / `_text` (+`--dark`) | `-warning` |
| `$c_error_surface` / `_border` / `_text` (+`--dark`) | `-critical` |
| `$c_support_border` / `--dark` | neutral border |
| `$c_text_primary` / `--dark` | neutral label |

## JS hooks
None. Fully static.

## Example params
```json
{ "variant": "-critical", "icon": "🔴", "label": "Critical" }
```

## Platform translation
**Static HTML:** Substitute into canonical structure. Emit the `__icon` span only when `icon` is set.

**Drupal Twig (`dd-badge.html.twig`):**
```twig
<span class="dd-badge{% if variant %} {{ variant }}{% endif %}">
  {% if icon %}<span class="dd-badge__icon" aria-hidden="true">{{ icon }}</span>{% endif %}<span class="dd-badge__label">{{ label }}</span>
</span>
```

**WordPress (block render.php):**
```php
<?php
$variant = $attributes['variant'] ?? '';
$icon    = $attributes['icon'] ?? '';
?>
<span class="dd-badge<?php echo $variant ? ' ' . esc_attr( $variant ) : ''; ?>">
  <?php if ( $icon ) : ?><span class="dd-badge__icon" aria-hidden="true"><?php echo esc_html( $icon ); ?></span><?php endif; ?><span class="dd-badge__label"><?php echo esc_html( $attributes['label'] ); ?></span>
</span>
```
