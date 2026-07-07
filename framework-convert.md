# Converting a dashboard to the ldnddev Framework

A reusable playbook for migrating a self-contained HTML dashboard to the ldnddev
Framework component system. Derived from the `dd-seo-audit` dashboard conversion.
Apply it to `dd-a11y`, `dd-site-compare`, and `dd-vreg`.

**Strategy used ("full framework"):** drop the dashboard's bespoke inline CSS/theme,
link the framework build (`style.min.css` + `main.min.js`) from the report bundle's
root `assets/`, and rebuild the UI from framework components + the 24-col grid.
Trade-off: you lose the bespoke theme **and** the manual light/dark toggle (the
framework themes by system `prefers-color-scheme` only).

---

## 1. Framework facts (memorize these)

| Thing | Value |
|---|---|
| Stylesheet | `assets/css/style.min.css` (compiled from `source/scss/style.scss`) |
| JS bundle | `assets/js/main.min.js` (concat of `source/js/components/*.js` + `main.js`) |
| Grid | 24-column: `dd-g` (row) + `dd-u-{n}-{d}` fractions, responsive `dd-u-lg-6-24` etc. |
| Dark mode | `@media (prefers-color-scheme: dark)` per-rule. **No `.dark`/`data-theme` class, no manual toggle.** |
| Tokens | SCSS `$c_*` variables, **compiled away** — NOT CSS custom properties at runtime. Custom shell CSS cannot reference them. |
| Inner-box padding | `.l-box` (and `.ll-box`) |
| SR-only class | `.visually-hidden` (framework-provided) |
| Unstyled list | `.-nostyle` |
| Buttons | `<button class="dd-button -primary">` (variants `-default -primary -secondary -tertiary -ghost`); usable on `<a>` too |
| Inputs | bare `<input>` + associated `<label for>` (no wrapper class) |
| htmx | NOT required by `main.min.js` — omit it unless the dashboard needs it |

**Framework JS modules that "just work" once `main.min.js` is linked:**
`dd_data_table` (column sort + `aria-sort` updates + scroll-region a11y on overflow),
`dd_navigation` (menu toggle), `dd_search`, `dd_tabs`, `dd_modal`, `dd_slider`,
`dd_milestones`, cookie consent, scrolltop. They are defensive (null-guarded) so
absent elements don't error.

---

## 2. Component map (dashboard primitive → framework component)

The dd-framework skill (`custom/dd-framework`, v1.2.0, 24 components) is the contract.
Fetch a spec/example with:
`python3 custom/dd-framework/.../scripts/dd_framework_helper.py get dd-<name>`

| You have | Use | Notes |
|---|---|---|
| status pill / badge (`data-severity`) | **dd-badge** | `-critical -warning -info -pass`; meaning in `__label` text, not color |
| data/results table | **dd-data-table** | caption + `th scope` + `__td`/`__th` on **every** cell; sort/scroll from framework JS |
| horizontal bar chart | **dd-bar-chart** | figure/group named by caption; label+value text is the truth; bars decorative |
| radial score / gauge / donut | **dd-score-ring** | figure form (`svg role=img`) or `-link` form (`<a>` owns name, svg `aria-hidden`) |
| issue / finding list | **dd-finding** | `<ol>`/`<ul>` semantics; severity badge + accent stripe |
| collapsible section | **dd-accordion** | `__items > details.__item > summary.__header > .__title` + `.__copy`; omit `name=` for independent panels |
| card grid | **dd-card** | image/title/copy/links; `-horizontal` |
| stats grid | **dd-milestones** | animated counters |
| masthead | **dd-header** | region; keep OUT of `<main>` |
| page footer | **dd-footer** | region; **sibling of `<main>`**, not nested |
| section wrapper | **dd-section** | `__content > __title + __items.dd-g > __item` nesting required |
| alerts, tabs, modal, slider, hero, banner, blockquote, cta, timeline, filmstrip, spacer | same-named components | see `list` |

**No framework component for** app-shell bits like a summary label/value readout,
a sticky rail, or a table-of-contents beyond a plain named `<nav>`. Keep those as a
small inline `<style>` block using CSS **system colors** (`Canvas`, `CanvasText`,
`GrayText`) so they adapt to light/dark without tokens. Prefix such classes with
something non-`dd-` (e.g. `app-summary`) so they don't masquerade as framework
components (the validator flags unknown `dd-*` roots).

---

## 3. Conversion steps (order matters)

A dashboard render is usually **template + Python builders + inline JS**. All three
convert together or the output renders half-styled.

### 3a. The template (`templates/*.html`)
1. **Head:** replace the entire inline design system with:
   ```html
   <link rel="stylesheet" href="assets/css/style.min.css">
   <script src="assets/js/main.min.js" defer></script>
   ```
   Keep the favicon block. Add `<title>{{TITLE}} — {{AGENCY}}</title>`. Drop any
   theme-preset script and the manual toggle button.
2. **Shell:** `<body class="dd-g">`; `dd-header` (out of `<main>`); `<main id="main-content" tabindex="-1">` containing a `dd-g` rail/canvas split (`dd-u-lg-8-24` + `dd-u-lg-16-24`); `dd-footer` as a **sibling after `</main>`**.
3. **Panels:** each `section.dd-section > .dd-section__content > (h2.dd-section__title.l-box + .dd-section__items.dd-g > .dd-section__item.dd-u-1-1.l-box)`. Put the real `<h2 id>` heading on the `.dd-section__title` class element (class = styling, `<h2>` = semantics).
4. **Component slots:** leave placeholders (`{{TASK_ROWS}}` etc.) inside the correct framework wrapper (e.g. `{{TASK_ROWS}}` inside `<tbody>` of a `dd-data-table`; ring cards inside `.dd-section__items.dd-g`; accordion items inside `.dd-accordion__items`).
5. **Minimal inline `<style>`:** only skip-link, the summary `<dl>`, sticky rail, `.muted`, `prefers-reduced-motion`, and a scoped rule for plain status tables inside accordions:
   ```css
   .dd-accordion__copy table { width:100%; border-collapse:collapse; }
   .dd-accordion__copy th,.dd-accordion__copy td { padding:.4rem .6rem; border-bottom:1px solid rgba(128,128,128,.25); text-align:start; }
   ```

### 3b. The Python builders (the HTML-emitting functions)
Add small DRY helpers once, then route every emit site through them:
- `_badge(severity, label)` → dd-badge span (map `critical/high→-critical`, `warning/medium→-warning`, `info/low→-info`, `pass→-pass`).
- `_finding_list(items)` → dd-finding `<ul>`/`<ol>` (items: `severity/title/evidence/fix`; titles are `<h4>`).
- `_ring_tone(score)` → `-good/-warn/-bad`.
- `_heading(text, level="h4")` → heading with any leading emoji wrapped in `<span aria-hidden="true">`.

Then convert each builder: category cards → `dd-score-ring -link` grid items;
chart data → server-rendered `dd-bar-chart__row` items (delete the client chart JS);
table rows → `dd-data-table__row` with `th scope="row"` first cell + `_badge` status
cells; download links → `<a class="dd-button -secondary" download>`; detail blocks →
`dd-accordion__item` (h3 summary title + score `_badge`); all inline issue markup →
`_finding_list` or a plain `<ul>` for non-severity recommendations.

**Cleanup while you're in there:** strip every `style="…var(--old-token)…"` (those
custom properties no longer exist — they render as default color, dead cruft) and
update the placeholder-substitution map (add new keys, remove dropped ones).

### 3c. Inline JS (keep only what the framework doesn't provide)
Drop the theme toggle and any client chart builder. Keep dashboard-specific behavior
(filter, CSV export) and **add**:
- a polite `role="status" aria-live="polite"` live region, updated on filter with a
  **debounced** count ("12 matching tasks");
- a `hashchange`/click handler that opens the target `<details>` and moves focus to
  it (in-page jumps into collapsed accordions otherwise dead-end).

Column sort, `aria-sort` updates, and scroll-region keyboard access come free from
`main.min.js` — don't reimplement them.

### 3d. Docs
Update the template README's placeholder/producer table and the styling section to
say "framework-driven."

---

## 4. Accessibility ruleset (bake into every conversion)

These are the findings from three accessibility-lead passes. Treat as a checklist.

**Landmarks & headings**
- `<html lang>` present; a real `<title>`.
- `<header class="dd-header">` and `<footer class="dd-footer">` are top-level → implicit `banner`/`contentinfo`. **Footer must be a sibling of `<main>`, never nested inside it** (nesting strips the landmark).
- Heading order unbroken: `h1` → section `h2` → accordion-summary `h3` → in-panel/finding `h4`. Do **not** author in-panel content headings at the same level as the panel summary.
- Skip link (`<a href="#main-content" class="skip-link">`) before the header; `<main id="main-content" tabindex="-1">`.

**Navigation**
- Every `<nav>` has a distinct accessible name when more than one exists (`aria-label="Primary"` / `"Footer"` / `"Social"`). Don't include the word "navigation."
- A named `<nav>` uses `aria-labelledby` to its visible heading OR `aria-label` — never both with different text.

**Icon-only controls**
- Keep a `visually-hidden` text label (the accessible name).
- The icon glyph must be a **child** element with `aria-hidden="true"` (`<i class="fa-…" aria-hidden="true"></i>`). Never put `fa-*` on the `<button>` itself — the pseudo-element glyph leaks into the name (VoiceOver).
- Disclosure state (`aria-expanded`) lives on **exactly one** control (the toggle); `aria-controls` references the controlled element's unique `id`. A "Close" button is a plain action — no `aria-expanded`.

**dd-score-ring**
- `-link` card form: the `<a>` owns the full accessible name **including** the visible label text (2.5.3 Label in Name — do NOT make it value-only) plus a purpose cue ("… View section"); the `<svg>` is `aria-hidden="true"`.
- Figure form: `svg role="img"` + `aria-label` with score/max; `__num` text `aria-hidden`.

**dd-data-table**
- `<caption>` (may be `.visually-hidden`), `th scope="col"`/`scope="row"`, status cells embed `dd-badge`. Sortable headers = native `<button>` + `aria-sort` on the `<th>` (framework JS keeps exactly one non-`none`). Don't hard-code the scroll region's `tabindex`/`role` — the JS toggles them on overflow.

**dd-bar-chart / dd-badge / dd-finding**
- Bars/tracks/fills are decorative (`aria-hidden`); label+value text carries meaning.
- Badge severity is the **word**, not color alone (1.4.1).
- Findings use real list semantics; titles are headings that continue the outline.

**Controls & motion**
- Filter/export controls associated with their target via `aria-controls`.
- CSV/download links: visible text is a **substring** of the accessible name (2.5.3), and the format label matches the actual file (don't say "PDF" for a `.docx`).
- Emoji in headings: wrap in `<span aria-hidden="true">` or drop.
- Live region announces filter/sort changes (polite, debounced 300–500ms).
- In-page jump handler opens collapsed `<details>` and moves focus.
- `prefers-reduced-motion` block present.

**Lives in the framework CSS/JS, not the template — verify in `framework.ldnddev.com`, don't re-fix per dashboard:**
- Interactive control **border contrast ≥ 3:1** (inputs, buttons) — WCAG 1.4.11.
- **Focus-ring** visibility/thickness (aim 2px, offset, no negative insets) — 2.4.7/2.4.13.
- `.visually-hidden` is actually defined (caption/label/live-region rely on it).
- All text/badge/ring contrast passes in **both** light and dark renderings.

---

## 5. Verification workflow (run every time)

1. **Contract validate** the rendered output:
   `python3 custom/dd-framework/skills/dd-framework/scripts/dd_framework_helper.py validate <out.html> --human`
   Target: **0 errors**. (Unknown non-`dd-` shell classes are fine; unknown `dd-*` roots mean a typo or an unregistered component.)
2. **Smoke-render** with synthetic data: import the report module, call its
   `generate_html(...)` with fake `data/scores/rows/artifacts`, write the HTML, and
   assert: no unreplaced `{{PLACEHOLDER}}`, no old classes (`priority-pill`,
   `issue-item`, `category-card`, `section-detail`), no dead `var(--…)` tokens, and
   each expected `dd-*` component present.
3. **`py_compile`** the changed script.
4. **accessibility-lead review** of the *rendered* file (not the skeleton) — it reads
   the real output and confirms the ruleset above. Watch for test-fixture false
   alarms (e.g. a fake artifact labeled "PDF" pointing at a `.docx`).
5. If you touched the dd-framework skill itself, run its `pytest`.

---

## 6. Per-dashboard notes

Scope each the same way; differences are in which primitives appear.

- **dd-a11y** — audit dashboard much like dd-seo: findings lists, severity badges,
  a results table, per-rule collapsibles, maybe category scores. Map findings →
  `dd-finding`, the WCAG results table → `dd-data-table`, rule sections →
  `dd-accordion`, severity → `dd-badge`. Same live-region + hash-reveal JS.
- **dd-site-compare** — comparison dashboard: multi-site metrics table → `dd-data-table`
  (many columns → the scroll region matters), per-metric bars → `dd-bar-chart`, any
  "winner"/score gauges → `dd-score-ring`, site cards → `dd-card`. Keyword/quantitative
  signal rows are good `dd-bar-chart` or `dd-data-table` candidates.
- **dd-vreg** (visual regression) — likely image-diff pairs and pass/fail status:
  status → `dd-badge`, diff/result rows → `dd-data-table`, per-comparison detail →
  `dd-accordion`; before/after images belong in `dd-card` or `dd-alternating`. Ensure
  every image has meaningful `alt` (or `alt=""` if purely decorative and described
  in adjacent text).

For each: find the render script's HTML-emitting functions
(`grep -nE 'class="|def _render|def render'`), find the placeholder-substitution map,
then follow §3. Run §5 before committing.

---

## 7. Gotchas

- **Tokens aren't CSS variables** — any custom shell CSS must use system colors or
  hardcoded values, not `$c_*`/`var(--…)`.
- **dd-section requires the full nesting** (`__content > __items.dd-g > __item`); a bare
  `<section class="dd-section">` fails the validator and won't be styled.
- **dd-data-table styles cells via `__td`/`__th` classes**, not bare `td/th`. For many
  simple static tables inside accordions it's lighter to keep plain `<table>` + a
  scoped CSS rule than to plumb per-cell classes.
- **dd-accordion `name=` makes panels mutually exclusive** — omit it for a dashboard
  where users open several sections.
- **Register new regions/components in the dd-framework manifest** (+ example HTML +
  spec.md + validator exemption if it has no `__items`/`__content` + bump version +
  update SKILL.md and tests) rather than shipping unregistered `dd-*` classes.
