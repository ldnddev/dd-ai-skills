# dd-footer

## Purpose
Site **contentinfo** region — the page footer carrying footer navigation, copyright, and optional company info / social links. One per page, at the bottom of `<body>`.

## Context
- Standalone region. Does NOT wrap in `dd-section`.
- Uses the native `<footer>` element, which is the `contentinfo` landmark **only when it is a top-level footer** (a direct child of `<body>`, not nested inside `<main>`/`<article>`/`<section>`).
- Pairs with `dd-header` (`banner`).

## Required parameters
None.

## Optional parameters
| name | type | default | description |
|---|---|---|---|
| `nav_items` | array | — | Footer nav links (label + href). |
| `nav_label` | string | `Footer` | Accessible name for the footer `<nav>`. |
| `copyright` | string | — | Copyright / legal line. |
| `social` | array | — | Social links (each an icon `<a>` with a `visually-hidden` label). |
| `logo_src` / `logo_alt` | string | — | Optional company logo. |

## Sub-parts (BEM)
| element | role |
|---|---|
| `.dd-footer__navigation` | footer nav cell (contains a named `<nav>`) |
| `.dd-footer__company-info` | logo + company name block (optional) |
| `.dd-footer__logo` / `.dd-footer__name` | company logo / name (optional) |
| `.dd-footer__copyright` | copyright line |

## Canonical structure
```html
<footer class="dd-footer">
  <div class="dd-g">
    <div class="dd-footer__navigation navigation -footer-menu dd-u-1-1 dd-u-lg-18-24 l-box">
      <nav aria-label="{nav_label}">
        <ul class="menu">
          <li class="menu-item"><a href="/privacy" class="navigation__link">Privacy</a></li>
          <!-- repeat per nav item -->
        </ul>
      </nav>
    </div>
  </div>
  <div class="dd-g">
    <div class="dd-footer__copyright dd-u-1-1">
      <div class="l-box">{copyright}</div>
    </div>
  </div>
</footer>
```
Optional social block (icon links keep a `visually-hidden` text name):
```html
<nav aria-label="Social">
  <ul class="menu">
    <li class="menu-item"><a href="https://…"><span class="visually-hidden">Facebook</span><i class="fa-brands fa-facebook" aria-hidden="true"></i></a></li>
  </ul>
</nav>
```
See `dd-footer.html`.

## Accessibility
**WCAG criteria touched:** 1.1.1, 1.3.1 Info and Relationships, 2.5.3 Label in Name, 4.1.2 Name/Role/Value.

- **`<footer>` is the `contentinfo` landmark only at top level.** It must be a sibling of `<main>`, NOT nested inside it — nesting suppresses the landmark. (This is the exact fix applied in the dd-seo-audit dashboard.)
- **Name each `<nav>`.** With multiple navigation landmarks on the page (header + footer + social), every `<nav>` needs a distinct accessible name — footer nav → "Footer", social nav → "Social".
- **Icon-only social links must carry a text name** via `visually-hidden` (2.5.3 / 4.1.2); the icon glyph (`<i class="fa-…">` / `<svg>`) is decorative and marked `aria-hidden="true"`.
- **Copyright** is plain text, not a heading.
- If a company logo is present, `alt` names the company (or `alt=""` if the company name is adjacent visible text).

## Design tokens
Region colors/spacing come from the framework footer styles. No component-specific token contract here.

## JS hooks
None required.

## Example params
```json
{ "nav_label": "Footer",
  "nav_items": [{"label":"Privacy","href":"/privacy"},{"label":"Terms","href":"/terms"}],
  "copyright": "© 2026 Company, LLC. All rights reserved.",
  "social": [{"label":"Facebook","href":"https://…","icon":"fa-facebook"}] }
```

## Platform translation
**Static HTML:** Emit the structure above as a sibling of `<main>`. Keep each `<nav>` named and every social icon link's `visually-hidden` label.

**Drupal Twig / WordPress:** Loop `nav_items` / `social` into the `.menu` lists (WordPress: `wp_nav_menu()` in the footer region). Keep the named `<nav>`s and icon-button labels intact.
