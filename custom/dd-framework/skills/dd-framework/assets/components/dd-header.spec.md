# dd-header

## Purpose
Site **banner** region — the masthead carrying the logo, primary navigation, and optional search / mobile-menu toggles. One per page, at the top of `<body>`.

## Context
- Standalone region. Does NOT wrap in `dd-section`.
- Uses the native `<header>` element, which is the `banner` landmark when it is a top-level page header.
- Pairs with `dd-footer` (`contentinfo`). Styling + menu/search behaviour come from the framework (`main.min.js`).

## Required parameters
None — the header renders with whatever sub-parts the page needs.

## Optional parameters
| name | type | default | description |
|---|---|---|---|
| `logo_href` | string | `/` | Home link wrapping the logo. |
| `logo_src` / `logo_alt` | string | — | Logo image + its alt text (name the destination, e.g. "Company home"). |
| `nav_items` | array | — | Primary nav links (label + href, optional children for `sub-menu`). |
| `nav_label` | string | `Primary` | Accessible name for the primary `<nav>`. |
| `search` | boolean | `false` | Emit the search toggle + `.dd-search` overlay. |
| `menu_toggle` | boolean | `true` | Emit the mobile `.dd-menu__toggle` button. |

## Sub-parts (BEM)
| element | role |
|---|---|
| `.dd-header__top` | main bar row |
| `.dd-header__logo` | logo cell (wraps an `<a>` + `<picture>`/`<img>`) |
| `.dd-header__navigation` | primary nav cell (contains a named `<nav>`) |
| `.dd-header__search-icon` | search toggle button cell (optional) |
| `.dd-header__menu-icon` | mobile menu toggle button cell |
| `.dd-search` | search overlay (optional) |

## Canonical structure
```html
<header class="dd-header">
  <div class="dd-header__top">
    <div class="dd-g -y-center">
      <div class="dd-header__logo dd-u-18-24 dd-u-lg-4-24">
        <a href="{logo_href}">
          <picture>
            <source srcset="{logo_dark}" media="(prefers-color-scheme: dark)">
            <img src="{logo_src}" alt="{logo_alt}" class="dd-img">
          </picture>
        </a>
      </div>
      <div class="dd-header__navigation navigation -main-menu dd-u-1-1 dd-u-lg-16-24 -y-center">
        <nav id="primary-nav" aria-label="{nav_label}">
          <!-- Close is an action button: NO aria-expanded. Glyph is a child, aria-hidden. -->
          <button class="dd-menu__close" aria-controls="primary-nav"><i class="fa-regular fa-times" aria-hidden="true"></i><span class="visually-hidden">Close menu</span></button>
          <ul class="menu">
            <li class="menu-item"><a href="/" class="navigation__link">Home</a></li>
            <!-- repeat per nav item -->
          </ul>
        </nav>
      </div>
      <div class="dd-header__menu-icon dd-u-3-24 -y-center -x-center">
        <!-- Toggle owns the disclosure state. Resting (mobile) = collapsed. -->
        <button class="dd-menu__toggle" aria-expanded="false" aria-controls="primary-nav"><i class="fa-regular fa-bars" aria-hidden="true"></i><span class="visually-hidden">Menu</span></button>
      </div>
    </div>
  </div>
</header>
```
See `dd-header.html`.

## Accessibility
**WCAG criteria touched:** 1.1.1 Non-text Content, 1.3.1 Info and Relationships, 2.4.1 Bypass Blocks, 2.5.3 Label in Name, 4.1.2 Name/Role/Value.

- **`<header>` is the `banner` landmark** when it is a direct child of `<body>` (not nested inside `<main>`/`<article>`/`<section>`). Do not add `role="banner"` explicitly.
- **Name the `<nav>`.** When a page has more than one navigation landmark (header + footer), each `<nav>` must have a distinct accessible name (`aria-label` / `aria-labelledby`). Header nav → "Primary".
- **Icon-only buttons must keep a visually-hidden text label** as the accessible name (`<span class="visually-hidden">…</span>`). Never remove it (2.5.3 / 4.1.2).
- **The icon glyph must be a separate child element with `aria-hidden="true"`** (e.g. `<i class="fa-regular fa-bars" aria-hidden="true"></i>`). Do NOT put the `fa-*` classes on the `<button>` itself — FontAwesome injects the glyph as `::before` pseudo-content, which some AT (notably VoiceOver) append to the accessible name, so the button announces the label plus a stray glyph. You cannot fix that by hiding the button.
- **`aria-expanded` lives ONLY on `.dd-menu__toggle`** — `false` when collapsed, flipped to `true` by the framework JS on open. The `.dd-menu__close` button must NOT carry `aria-expanded`; it is a plain action button (optionally `aria-controls="primary-nav"`). Two controls reporting state for one region is contradictory.
- **`aria-controls` on the toggle references the nav's `id`** (`primary-nav`), which is required and must be unique on the page.
- **Resting state + focus (JS contract):** on load (mobile) the nav is collapsed and the toggle is `aria-expanded="false"`; opening moves focus into the nav (Close button), closing (or `Esc`) returns focus to the toggle. On desktop the nav is always visible and the toggle/close are hidden.
- **Logo alt** names the destination ("Company home"), not the file. If an adjacent visible site name already labels the link, the image may be `alt=""`.
- Provide a **skip link** (`<a href="#main-content" class="skip-link">`) before the header so keyboard users can bypass the nav (2.4.1). The header component does not include it — the page owns it.

## Design tokens
Region colors/spacing come from the framework header styles. No component-specific token contract here.

## JS hooks
`source/js/components/_dd_navigation.js` — `.dd-menu__toggle` opens/closes `.dd-header__navigation`, toggling `aria-expanded`.
`source/js/components/_dd_search.js` — `.dd-search__toggle` / `.dd-search__close` drive the `.dd-search` overlay (when `search=true`).

## Example params
```json
{ "logo_href": "/", "logo_src": "/assets/imgs/logo.svg", "logo_alt": "Company home",
  "nav_label": "Primary",
  "nav_items": [{"label":"Home","href":"/"},{"label":"About","href":"/about"}] }
```

## Platform translation
**Static HTML:** Emit the structure above; keep every icon button's `visually-hidden` label and the toggle `aria-expanded`/`aria-controls`.

**Drupal Twig / WordPress:** Loop `nav_items` into the `.menu`. In WordPress this is typically the `wp_nav_menu()` output wrapped in `.dd-header__navigation`; keep the named `<nav>` and the icon-button labels intact.
