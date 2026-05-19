# dd-banner

## Purpose
Full-width image banner — single responsive image with no overlay copy. For decorative or content-bearing imagery breaks between sections.

## Context
- **Standalone.** Renders edge-to-edge.
- If banner needs headline/CTA over the image, use `dd-hero` or `dd-cta` instead.

## Required parameters
| name | type | description |
|---|---|---|
| `image_src` | string (URL) | Largest/default image. |
| `image_alt` | string | Alt text. `""` only if purely decorative AND no semantic content lives in image. |

## Optional parameters
| name | type | default | description |
|---|---|---|---|
| `srcset` | string | — | Responsive `srcset` values. |
| `sizes` | string | `(max-width: 1024px) 100vw 1024px` | Image `sizes` attr. |
| `bg_url` | string (URL) | `image_src` | Inline-style `background-image`. Match `image_src` to avoid double-load. |
| `aos` | string | `fade-in` | AOS animation. |

## Variants
None.

## Canonical structure
```html
<div class="dd-banner" data-aos="{aos}"{% if bg_url %} style="background-image: url({bg_url});"{% endif %}>
  <div class="dd-banner__image">
    <img sizes="{sizes}" srcset="{srcset}" src="{image_src}" class="dd-img" alt="{image_alt}" />
  </div>
</div>
```
See `dd-banner.html`.

**`bg_url` is opt-in.** Setting both an inline `background-image` AND an `<img>` of the same asset typically double-loads the image. Use one or the other based on use case:
- `<img>` only (default): the image is content. SR reads alt text. CSS can render at any size.
- `background-image` only: image is decorative. Add `aria-hidden="true"` to the banner div and drop the `<img>` (use a separate parameterization or a different component).

## Accessibility
**WCAG criteria touched:** 1.1.1, 1.3.1, 1.4.5 Images of Text.

- `image_alt` MUST describe meaningful image content. If text appears IN the image (e.g., a poster), the alt text must include that text verbatim, OR replace with real HTML text rendered over image (1.4.5).
- Decorative banners: `alt=""`. The `background-image` carries no separate semantic — screen readers don't announce it.
- Both `background-image` inline style AND `<img>` should resolve to the same asset to avoid duplicate downloads. Prefer just the `<img>` and remove inline `background-image` if no styling depends on it.
- No interactive descendants. If you need clickable banner, wrap the whole component in `<a aria-label="{descriptive label}">` AND set the inner `<img alt="">` (the anchor's `aria-label` IS the accessible name; non-empty image alt would cause double-announcement).
- AOS fade-in respects reduced motion.

## Design tokens
None applied to banner surface itself (image fills frame). Focus outline on wrapping `<a>` (if clickable) uses `$c_support_focus` / `--dark`.

## JS hooks
- `data-aos` — AOS scroll animation.

## Example params
```json
{
  "image_src": "/assets/imgs/banner-1440.webp",
  "image_alt": "Team gathered around laptops in a sunlit workspace",
  "srcset": "/assets/imgs/banner-720.webp 720w, /assets/imgs/banner-1440.webp 1440w",
  "sizes": "(max-width: 1024px) 100vw 1024px"
}
```

## Platform translation
**Static HTML:** Direct substitution.

**Drupal Twig:**
```twig
<div class="dd-banner" data-aos="{{ aos|default('fade-in') }}"{% if bg_url %} style="background-image: url({{ bg_url }});"{% endif %}>
  <div class="dd-banner__image">
    <img {% if sizes %}sizes="{{ sizes }}"{% endif %} {% if srcset %}srcset="{{ srcset }}"{% endif %} src="{{ image_src }}" class="dd-img" alt="{{ image_alt }}" />
  </div>
</div>
```

**WordPress (block render.php):**
```php
<div class="dd-banner" data-aos="fade-in">
  <div class="dd-banner__image">
    <img src="<?php echo esc_url( $attributes['image_src'] ); ?>"
         alt="<?php echo esc_attr( $attributes['image_alt'] ); ?>"
         <?php if ( ! empty( $attributes['srcset'] ) ) : ?>srcset="<?php echo esc_attr( $attributes['srcset'] ); ?>"<?php endif; ?>
         class="dd-img" />
  </div>
</div>
```
