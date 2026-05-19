# dd-spacer

## Purpose
Vertical whitespace utility with named size modifiers. Optionally renders a divider rule.

## Context
- Pure presentational. Insert between content blocks where CSS margins on the surrounding components are insufficient.
- Prefer adjusting component spacing tokens over scattering spacers. Use `dd-spacer` sparingly.

## Required parameters
| name | type | description |
|---|---|---|
| `size` | enum | One of `-sm -md -lg -xl -xxl -xxxl`. |

## Optional parameters
| name | type | default | description |
|---|---|---|---|
| `divider` | boolean | `false` | Render a horizontal rule centered in the spacer (`-divider` modifier). |

## Variants
| modifier | effect |
|---|---|
| `-sm` | Smallest vertical gap |
| `-md` | Small/medium |
| `-lg` | Large |
| `-xl` | Extra large |
| `-xxl` | 2x extra large |
| `-xxxl` | 3x extra large |
| `-divider` | Adds horizontal rule line |

## Canonical structure
```html
<div class="dd-spacer {size}{% if divider %} -divider{% endif %}" aria-hidden="true"></div>
```
See `dd-spacer.html` for all sizes.

## Accessibility
**WCAG criteria touched:** 1.3.1.

- Spacer is purely presentational. Add `aria-hidden="true"` so AT skips it.
- Do NOT use spacers to convey grouping. Use semantic landmarks/headings for structure.
- `-divider` renders a visual line — non-semantic. **MUST use `<hr>` when the intent is a thematic break** (end of one topic, start of another). `dd-spacer -divider` is for purely visual whitespace with a decorative line.

## Design tokens
| token | usage |
|---|---|
| `$c_support_border` / `--dark` | divider line color |
| Spacing scale tokens map size modifiers to CSS rem values |

## JS hooks
- None.

## Example params
```json
{ "size": "-xxl", "divider": true }
```

## Platform translation
**Static HTML:**
```html
<div class="dd-spacer -xxl -divider" aria-hidden="true"></div>
```

**Drupal Twig:**
```twig
<div class="dd-spacer {{ size }}{% if divider %} -divider{% endif %}" aria-hidden="true"></div>
```

**WordPress (block render.php):**
```php
<div class="dd-spacer <?php echo esc_attr( $attributes['size'] ); ?><?php echo ! empty( $attributes['divider'] ) ? ' -divider' : ''; ?>" aria-hidden="true"></div>
```
