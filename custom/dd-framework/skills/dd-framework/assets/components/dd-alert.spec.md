# dd-alert

## Purpose
Inline message banner for status feedback — informational, success confirmation, warning, or error.

## Context
- Wraps in `dd-section`.
- Placed inline with content flow, NOT as a global toast/overlay.
- For dismissible toasts/snackbars, use a different component (not in current dd-framework set).

## Required parameters
| name | type | description |
|---|---|---|
| `heading` | string | Short summary line. |
| `copy` | string (HTML) | Body message. May include inline links. |

## Optional parameters
| name | type | default | description |
|---|---|---|---|
| `variant` | enum | — | `-info` `-success` `-warning` `-error`. Default (no modifier) is neutral. |
| `aos` | string | `fade-in` | AOS animation. |
| `dynamic` | boolean | `false` | `true` when alert is injected after page load. Controls whether `role="alert"` / `role="status"` is emitted. See Accessibility. |
| `focus_id` | string | — | If set, emits this `id` + `tabindex="-1"` so server-rendered form-error alerts can receive focus on submit. |

## Variants and live-region mapping
| modifier | tone | role (when `dynamic=true`) | role (when `dynamic=false`) |
|---|---|---|---|
| (none) | Neutral / default | `status` | — |
| `-info` | Informational | `status` | — |
| `-success` | Success confirmation | `status` | — |
| `-warning` | Warning | `alert` | `alert` |
| `-error` | Error / destructive | `alert` | `alert` |

**Why:** `role="alert"` implies `aria-live="assertive"` AND fires an announcement when the element is inserted or its contents change. Emitting it for every server-rendered informational alert on page load floods AT with stale "alerts." Reserve `role="alert"` for `-warning` / `-error` (where assertive intrusion is warranted) and use `role="status"` (polite) for `-info` / `-success` dynamic alerts. Non-dynamic info/success alerts emit no role — they're inline messaging, not status updates.

## Canonical structure
```html
<!-- role attribute computed by variant + dynamic per table above -->
<div class="dd-alert {variant}" {role_attr} {focus_attrs} data-aos="{aos}">
  <div class="dd-alert__content dd-g">
    <div class="dd-u-1-1">
      <div class="l-box">
        <div class="dd-alert__heading">
          <span class="-scrn-reader-only">{severity_label}: </span>{heading}
        </div>
        <div class="dd-alert__copy">{copy}</div>
      </div>
    </div>
  </div>
</div>
```
Where:
- `{role_attr}` is `role="alert"`, `role="status"`, or empty per the variant table.
- `{focus_attrs}` is `id="{focus_id}" tabindex="-1"` when `focus_id` is set, else empty.
- `{severity_label}` is `"Error"` / `"Warning"` / `"Success"` / `"Info"` / `""` (skip span when empty). Satisfies 1.4.1 (color not the sole cue) for SR users.
See `dd-alert.html` for variant examples (default, -info, -success, -warning, -error).

## Accessibility
**WCAG criteria touched:** 1.3.1, 1.4.1 Use of Color, 1.4.3, 1.4.11, 2.4.6, 4.1.3 Status Messages.

- **Role choice is driven by variant + dynamic flag** (see table above). `role="alert"` implies `aria-live="assertive"` AND `aria-atomic="true"` — do NOT add explicit `aria-live` on the same element (contradictory). `role="status"` implies polite.
- **Critical for SR users:** Dynamic alerts must be inserted into a live-region container that exists in the DOM at page load. Mutating the container's text (or replacing a child) reliably announces; creating the container itself does not.
- Do NOT rely on color alone (1.4.1). The SR-only `severity_label` span carries the cue ("Error: ", "Warning: ") for colorblind / SR users. Visible severity icons can be added without changing the SR contract.
- Contrast: heading + copy must meet 4.5:1 against the variant surface color in both light and dark mode. `-warning` (yellow tones) is highest-risk — verify against `$c_text_primary`.
- Non-text contrast (1.4.11): border / accent stripe (if present) must meet 3:1 against page surface.
- Focus: inline links inside `dd-alert__copy` retain default focus outline.
- Avoid auto-dismiss for `-error`. Errors require user acknowledgment.
- For form-submission errors: set `focus_id`, place alert ABOVE the form, link `aria-describedby` from offending fields to `focus_id`, and call `document.getElementById(focus_id).focus()` after submit.

## Design tokens
| token | usage |
|---|---|
| `$c_text_primary` / `--dark` | heading + copy |
| `$c_primary_subtle` / `--dark` | `-info` surface |
| `$c_support_*` (success palette) | `-success` surface |
| `$c_secondary_subtle` / `--dark` | `-warning` surface |
| `$c_tertiary_subtle` / `--dark` | `-error` surface |
| `$c_support_border` / `--dark` | left border / accent |
| `$c_support_focus` / `--dark` | focus outline on links inside |

## JS hooks
- `data-aos="fade-in"` — AOS scroll-in.
- No custom JS for static alerts.
- Dynamic injection: ensure the alert container exists at page load; toggle visibility / replace content rather than create/destroy DOM.

## Example params
```json
{
  "variant": "-error",
  "heading": "We couldn't save your changes",
  "copy": "<a href=\"/help\">Get help</a>.",
  "dynamic": true,
  "focus_id": "form-error"
}
```

## Platform translation
**Static HTML:** Substitute params into canonical structure. Compute `role` per variant table. Omit `role` entirely for non-dynamic neutral/info/success variants.

**Drupal Twig (`dd-alert.html.twig`):**
```twig
{% set is_assertive = variant in ['-warning', '-error'] %}
{% set role = is_assertive ? 'alert' : (dynamic ? 'status' : '') %}
{% set severity_label = {'-error':'Error','-warning':'Warning','-success':'Success','-info':'Info'}[variant] ?? '' %}
<div class="dd-alert{% if variant %} {{ variant }}{% endif %}"
     {% if role %}role="{{ role }}"{% endif %}
     {% if focus_id %}id="{{ focus_id }}" tabindex="-1"{% endif %}>
  <div class="dd-alert__content dd-g">
    <div class="dd-u-1-1">
      <div class="l-box">
        <div class="dd-alert__heading">
          {% if severity_label %}<span class="-scrn-reader-only">{{ severity_label }}: </span>{% endif %}{{ heading }}
        </div>
        <div class="dd-alert__copy">{{ copy|raw }}</div>
      </div>
    </div>
  </div>
</div>
```

**WordPress (block render.php):**
```php
<?php
$variant = $attributes['variant'] ?? '';
$dynamic = ! empty( $attributes['dynamic'] );
$is_assertive = in_array( $variant, [ '-warning', '-error' ], true );
$role = $is_assertive ? 'alert' : ( $dynamic ? 'status' : '' );
$severity_map = [ '-error'=>'Error', '-warning'=>'Warning', '-success'=>'Success', '-info'=>'Info' ];
$severity_label = $severity_map[ $variant ] ?? '';
$focus_id = $attributes['focus_id'] ?? '';
?>
<div class="dd-alert<?php echo $variant ? ' ' . esc_attr( $variant ) : ''; ?>"
     <?php echo $role ? 'role="' . esc_attr( $role ) . '"' : ''; ?>
     <?php echo $focus_id ? 'id="' . esc_attr( $focus_id ) . '" tabindex="-1"' : ''; ?>>
  <div class="dd-alert__content dd-g">
    <div class="dd-u-1-1">
      <div class="l-box">
        <div class="dd-alert__heading">
          <?php if ( $severity_label ) : ?><span class="-scrn-reader-only"><?php echo esc_html( $severity_label ); ?>: </span><?php endif; ?>
          <?php echo esc_html( $attributes['heading'] ); ?>
        </div>
        <div class="dd-alert__copy"><?php echo wp_kses_post( $attributes['copy'] ); ?></div>
      </div>
    </div>
  </div>
</div>
```
