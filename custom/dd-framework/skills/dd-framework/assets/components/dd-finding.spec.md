# dd-finding

## Purpose
Renders a list of audit findings. Each item combines a severity badge (embedding `dd-badge`), a title, and optional evidence and fix details. An accent stripe reinforces the severity for quick visual scanning.

## Context
- Wraps in `dd-section`.
- For accessibility, SEO, and security audit reports where issues need clear priority.
- Order findings by severity when using the ordered-list form.

## Required parameters
| name | type | description |
|---|---|---|
| `items` | array | Each: `severity` (enum), `badge_label` (string), `title` (string), optional `evidence` (string), optional `fix` (string). |

## Optional parameters
| name | type | default | description |
|---|---|---|---|
| `heading` | string | — | Group heading above the list. Its level must continue the page outline. |
| `ordered` | boolean | `true` | `<ol>` when order communicates priority; `<ul>` when it does not. |
| `heading_level` | enum | `h4` | Heading tag for `heading`; pick the level that continues the outline without skipping. |

## Variants (per item)
| modifier | severity | stripe token | badge variant |
|---|---|---|---|
| `-critical` | Critical | `$c_error_*` | `-critical` |
| `-warning` | Warning | `$c_warning_*` | `-warning` |
| `-info` | Informational | `$c_info_*` | `-info` |
| `-pass` | Passing | `$c_success_*` | `-pass` |

## Canonical structure
```html
<div class="dd-finding">
  <h4 class="dd-finding__heading">{heading}</h4>
  <ol class="dd-finding__list"><!-- or <ul> when ordered=false -->
    <li class="dd-finding__item {severity}">
      <span class="dd-finding__badge"><span class="dd-badge {severity}"><span class="dd-badge__label">{badge_label}</span></span></span>
      <div class="dd-finding__body">
        <p class="dd-finding__title">{title}</p>
        <p class="dd-finding__evidence">{evidence}</p><!-- optional -->
        <p class="dd-finding__fix"><span class="dd-finding__fix-label">Fix:</span> {fix}</p><!-- optional -->
      </div>
    </li>
    <!-- repeat per item -->
  </ol>
</div>
```
- `{severity}` is the same modifier on both `__item` (stripe) and the embedded `dd-badge`.
- `__evidence` and `__fix` are emitted only when supplied.
See `dd-finding.html`.

## Accessibility
**WCAG criteria touched:** 1.3.1 Info and Relationships, 1.4.1 Use of Color, 2.4.6 Headings and Labels.

- **Real list semantics** (`<ol>` / `<ul>`) so assistive technology announces count and position (1.3.1). Use `<ol>` when order communicates priority, `<ul>` when it does not.
- **Severity is stated by the badge word**, not the stripe color alone (1.4.1). The accent stripe is redundant reinforcement.
- The `heading` level must **continue the page outline without skipping** levels (1.3.1 / 2.4.6). `h4` is the default because findings typically sit under an `h3` section — adjust to fit the actual outline.
- Inline links inside `__evidence` / `__fix` keep their underline and a visible focus indicator.
- `__fix-label` ("Fix:") is visible text, not an `aria-label`, so it is announced inline.

## Design tokens
| token | usage |
|---|---|
| `$c_error_*` | `-critical` stripe + badge |
| `$c_warning_*` | `-warning` stripe + badge |
| `$c_info_*` | `-info` stripe + badge |
| `$c_success_*` | `-pass` stripe + badge |
| `$c_text_primary` / `--dark` | title, evidence, fix text |

## JS hooks
None. Static list.

## Example params
```json
{
  "heading": "Priority findings",
  "ordered": true,
  "items": [
    { "severity": "-critical", "badge_label": "Critical", "title": "Missing <title> tag", "evidence": "No <title> in <head>.", "fix": "Add a unique 50–60 char title." },
    { "severity": "-pass", "badge_label": "Pass", "title": "Canonical tags present on all pages" }
  ]
}
```

## Platform translation
**Static HTML:** Choose `<ol>`/`<ul>` from `ordered`. Emit `__evidence` / `__fix` only when present. Use the same `{severity}` modifier on the item and the embedded badge.

**Drupal Twig (`dd-finding.html.twig`):**
```twig
<div class="dd-finding">
  {% if heading %}<{{ heading_level|default('h4') }} class="dd-finding__heading">{{ heading }}</{{ heading_level|default('h4') }}>{% endif %}
  <{{ ordered ? 'ol' : 'ul' }} class="dd-finding__list">
    {% for item in items %}
    <li class="dd-finding__item {{ item.severity }}">
      <span class="dd-finding__badge"><span class="dd-badge {{ item.severity }}"><span class="dd-badge__label">{{ item.badge_label }}</span></span></span>
      <div class="dd-finding__body">
        <p class="dd-finding__title">{{ item.title }}</p>
        {% if item.evidence %}<p class="dd-finding__evidence">{{ item.evidence }}</p>{% endif %}
        {% if item.fix %}<p class="dd-finding__fix"><span class="dd-finding__fix-label">Fix:</span> {{ item.fix }}</p>{% endif %}
      </div>
    </li>
    {% endfor %}
  </{{ ordered ? 'ol' : 'ul' }}>
</div>
```

**WordPress (block render.php):**
```php
<?php
$items   = $attributes['items'] ?? [];
$ordered = $attributes['ordered'] ?? true;
$tag     = $ordered ? 'ol' : 'ul';
$hl      = $attributes['heading_level'] ?? 'h4';
?>
<div class="dd-finding">
  <?php if ( ! empty( $attributes['heading'] ) ) : ?><<?php echo tag_escape( $hl ); ?> class="dd-finding__heading"><?php echo esc_html( $attributes['heading'] ); ?></<?php echo tag_escape( $hl ); ?>><?php endif; ?>
  <<?php echo $tag; ?> class="dd-finding__list">
    <?php foreach ( $items as $item ) : $sev = esc_attr( $item['severity'] ); ?>
    <li class="dd-finding__item <?php echo $sev; ?>">
      <span class="dd-finding__badge"><span class="dd-badge <?php echo $sev; ?>"><span class="dd-badge__label"><?php echo esc_html( $item['badge_label'] ); ?></span></span></span>
      <div class="dd-finding__body">
        <p class="dd-finding__title"><?php echo esc_html( $item['title'] ); ?></p>
        <?php if ( ! empty( $item['evidence'] ) ) : ?><p class="dd-finding__evidence"><?php echo esc_html( $item['evidence'] ); ?></p><?php endif; ?>
        <?php if ( ! empty( $item['fix'] ) ) : ?><p class="dd-finding__fix"><span class="dd-finding__fix-label">Fix:</span> <?php echo esc_html( $item['fix'] ); ?></p><?php endif; ?>
      </div>
    </li>
    <?php endforeach; ?>
  </<?php echo $tag; ?>>
</div>
```
