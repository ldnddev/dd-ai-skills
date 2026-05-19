# dd-hero

## Purpose
Full-width landing hero — single `<h1>` page introduction with responsive background image, headline, subtitle, body copy, and up to two CTAs.

## Context
- **Standalone.** Does NOT require `dd-section` wrapper. Renders edge-to-edge.
- One per page. Should be the first `<main>` child and contain the page's `<h1>`.
- Pair with `dd-spacer` below before subsequent content.

## Required parameters
| name | type | description |
|---|---|---|
| `id` | string | Unique element id (used by skip links, anchors). |
| `title` | string | H1 headline. Plain text or inline HTML. |
| `image_src` | string (URL) | Default/largest background image. |
| `image_alt` | string | Alt text. Empty string only if image is decorative AND background-image CSS carries no semantic info. |
| `aria_label` | string | Section label (e.g. `"Introduction"`). |

## Optional parameters
| name | type | default | description |
|---|---|---|---|
| `subtitle` | string | — | Rendered inside `<strong>`. Visually distinct from H1; not a separate heading level. |
| `body` | string (HTML) | — | Body copy paragraph(s). |
| `srcset` | string | — | Comma-separated `srcset` values for `<source>`. |
| `sizes` | string | `(max-width: 1440px) 100vw, 1440px` | `<source>` sizes attribute. |
| `bg_mobile_url` | string (URL) | `image_src` | CSS `background-image` for narrow viewports. |
| `bg_desktop_url` | string (URL) | `image_src` | CSS `background-image` ≥ 64em. |
| `primary_cta` | object | — | `{ text, href, target }`. Target ∈ `_self _blank _parent _top`. |
| `secondary_cta` | object | — | Same shape as `primary_cta`. Rendered with `-ghost` button modifier. |
| `aos` | string | `fade-in` | AOS animation. Honors `prefers-reduced-motion`. |

## Variants
None at root. Button children use `-primary` / `-ghost` modifiers.

## Canonical structure
```html
<section class="dd-hero" id="{id}" aria-label="{aria_label}">
  <div class="dd-hero__image">
    <!-- Use <img srcset> directly. <source> with only srcset (no media/type) is redundant. -->
    <img src="{image_src}" srcset="{srcset}" sizes="{sizes}" class="dd-img" alt="{image_alt}" />
  </div>
  <style>
    .dd-hero__image { background-image: url('{bg_mobile_url}'); }
    @media (min-width: 64em) {
      .dd-hero__image { background-image: url('{bg_desktop_url}'); }
    }
  </style>
  <div class="dd-hero__content dd-g" data-aos="{aos}">
    <div class="dd-hero__copy dd-u-1-1 dd-u-lg-12-24">
      <div class="dd-hero__title"><h1>{title}</h1></div>
      {% if subtitle %}<div class="dd-hero__subtitle"><strong>{subtitle}</strong></div>{% endif %}
      <div class="dd-hero__body">
        {body}
        {% if primary_cta or secondary_cta %}
        <div class="dd-hero__links dd-g">
          {% if primary_cta and primary_cta.href %}
          <div class="dd-hero__link">
            <a href="{primary_cta.href}" {% if primary_cta.target %}target="{primary_cta.target}"{% endif %} class="dd-button -primary">{primary_cta.text}</a>
          </div>
          {% endif %}
          {% if secondary_cta and secondary_cta.href %}
          <div class="dd-hero__link">
            <a href="{secondary_cta.href}" {% if secondary_cta.target %}target="{secondary_cta.target}"{% endif %} class="dd-button -ghost">{secondary_cta.text}</a>
          </div>
          {% endif %}
        </div>
        {% endif %}
      </div>
    </div>
  </div>
</section>
```
See `dd-hero.html` for static reference output.

**Gating:** Omit subtitle `<strong>` and CTA `<a>` when underlying values are absent. Empty conditional elements get announced by SR and create broken empty links.

## Accessibility
**WCAG criteria touched:** 1.1.1 Non-text Content, 1.3.1 Info and Relationships, 1.4.3 Contrast (Minimum), 1.4.11 Non-text Contrast, 2.4.6 Headings and Labels, 2.4.7 Focus Visible, 3.2.2 On Input.

- `<section>` with `aria-label` provides landmark naming. **Required:** `aria_label` must be unique and descriptive.
- Exactly one `<h1>`. Subtitle uses `<strong>`, not `<h2>` (avoids fake heading hierarchy).
- If background image carries meaning beyond decoration, `image_alt` must describe it. If purely decorative, set `image_alt=""` AND ensure no semantic content lives only in the image.
- CTA contrast: `-primary` button requires ≥ 4.5:1 text/surface in both light and dark mode (see Design tokens).
- CTA contrast against hero background: at minimum 3:1 for button outline (1.4.11); ensure background image overlay (if any) preserves text contrast ≥ 4.5:1 over the title region.
- Focus visible: 2px solid outline on CTAs, not removed by hover styles.
- `target="_blank"` CTAs MUST include `rel="noopener noreferrer"` and an indicator (visible icon + SR-only "opens in new tab") so the change of context is announced before activation (G201 technique, related to 3.2.2 On Input).
- AOS `fade-in` respects `prefers-reduced-motion: reduce` — verify via library config.

## Design tokens
| token | usage |
|---|---|
| `$c_text_primary` / `$c_text_primary--dark` | title, subtitle, body text |
| `$c_primary_action_default_*` | primary CTA surface/text/border |
| `$c_primary_action_hover_*` / `_pressed_*` / `_disabled_*` | CTA states |
| `$c_support_focus` / `--dark` | focus outline color |
| Grid: `dd-g`, `dd-u-1-1`, `dd-u-lg-12-24` | half-width copy on large viewports |
| Spacing: `l-box` not used at root (hero is edge-to-edge) |

## JS hooks
- `data-aos="{aos}"` — AOS library trigger on scroll.
- No required JS for component itself. CTAs are plain anchors.

## Example params
```json
{
  "id": "hero-home",
  "aria_label": "Introduction",
  "title": "Build better web pages, faster",
  "subtitle": "Component-driven framework for static sites, Drupal, and WordPress",
  "image_src": "/assets/imgs/hero-1920.webp",
  "image_alt": "",
  "srcset": "/assets/imgs/hero-720.webp 720w, /assets/imgs/hero-1440.webp 1440w, /assets/imgs/hero-1920.webp 1920w",
  "body": "<p>Ship pages your design system already approves.</p>",
  "primary_cta": { "text": "Get started", "href": "/start", "target": "_self" },
  "secondary_cta": { "text": "View components", "href": "/components", "target": "_self" }
}
```

## Platform translation
**Static HTML / vanilla:** Substitute params directly into the canonical structure. No build step required.

**Drupal (Twig template, `templates/components/dd-hero.html.twig`):**
```twig
<section class="dd-hero" id="{{ id }}" aria-label="{{ aria_label }}">
  <div class="dd-hero__image">
    <picture>
      {% if srcset %}<source srcset="{{ srcset }}" sizes="{{ sizes|default('(max-width: 1440px) 100vw, 1440px') }}">{% endif %}
      <img src="{{ image_src }}" class="dd-img" alt="{{ image_alt }}" />
    </picture>
  </div>
  <div class="dd-hero__content dd-g" data-aos="{{ aos|default('fade-in') }}">
    <div class="dd-hero__copy dd-u-1-1 dd-u-lg-12-24">
      <div class="dd-hero__title"><h1>{{ title }}</h1></div>
      {% if subtitle %}<div class="dd-hero__subtitle"><strong>{{ subtitle }}</strong></div>{% endif %}
      <div class="dd-hero__body">
        {{ body|raw }}
        {% if primary_cta or secondary_cta %}
        <div class="dd-hero__links dd-g">
          {% if primary_cta %}<div class="dd-hero__link"><a href="{{ primary_cta.href }}" class="dd-button -primary">{{ primary_cta.text }}</a></div>{% endif %}
          {% if secondary_cta %}<div class="dd-hero__link"><a href="{{ secondary_cta.href }}" class="dd-button -ghost">{{ secondary_cta.text }}</a></div>{% endif %}
        </div>
        {% endif %}
      </div>
    </div>
  </div>
</section>
```
Pair with `dd_hero.libraries.yml` for CSS/JS asset attachment.

**WordPress (block.json + render.php, or ACF Flexible Content row):**
```php
<?php
// render.php for block 'ldnddev/dd-hero'
$id = esc_attr( $attributes['id'] );
$title = wp_kses_post( $attributes['title'] );
$image_src = esc_url( $attributes['image_src'] );
$image_alt = esc_attr( $attributes['image_alt'] );
$aria_label = esc_attr( $attributes['aria_label'] );
?>
<section class="dd-hero" id="<?php echo $id; ?>" aria-label="<?php echo $aria_label; ?>">
  <div class="dd-hero__image">
    <img src="<?php echo $image_src; ?>" class="dd-img" alt="<?php echo $image_alt; ?>" />
  </div>
  <div class="dd-hero__content dd-g">
    <div class="dd-hero__copy dd-u-1-1 dd-u-lg-12-24">
      <div class="dd-hero__title"><h1><?php echo $title; ?></h1></div>
      <?php if ( ! empty( $attributes['subtitle'] ) ) : ?>
        <div class="dd-hero__subtitle"><strong><?php echo esc_html( $attributes['subtitle'] ); ?></strong></div>
      <?php endif; ?>
    </div>
  </div>
</section>
```
