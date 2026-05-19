# dd-cookie-consent

## Purpose
Google tracking consent banner with accept/decline controls. Drives `gtag('consent', ...)` updates.

## Context
- **Standalone.** Typically rendered at end of `<body>` and shown via JS after checking stored consent state.
- Requires accompanying JS: `handleCookieConsent(action)` to persist choice and `dd_cookie_consent()` to refresh tracking state.
- htmx-compatible via `hx-on::after-request="dd_cookie_consent()"`.

## Required parameters
None at HTML level. Drives consent via JS handlers — supply your own implementation of `handleCookieConsent` and `dd_cookie_consent`.

## Optional parameters
| name | type | default | description |
|---|---|---|---|
| `message` | string | `We use cookies to enhance your experience. Do you consent to Google tracking?` | Prompt copy. |
| `accept_text` | string | `Accept` | Accept button label. |
| `decline_text` | string | `Decline` | Decline button label. |
| `accept_class` | string | `accept dd-button` | Accept button class list. |
| `decline_class` | string | `decline dd-button-secondary` | Decline button class list. |
| `region` | string | — | If serving multiple regions, label like `EU`, `US` for storage namespacing. |

## Variants
None.

## Canonical structure
```html
<div id="cookie-consent"
     class="l-box"
     style="display: none;"
     role="region"
     aria-label="Cookie consent"
     hx-on::after-request="dd_cookie_consent()">
  <p id="cookie-consent-message">{message}</p>
  <button class="{accept_class}" type="button" onclick="handleCookieConsent('accept')">{accept_text}</button>
  <button class="{decline_class}" type="button" onclick="handleCookieConsent('decline')">{decline_text}</button>
</div>
```
**Note:** the static reference (`dd-cookie-consent.html`) omits `role`/`aria-label` and the `type="button"` attribute. Canonical structure above is the accessible target.

`role="region"` is correct for a non-modal consent banner. Do NOT use `role="dialog"` with `aria-modal="false"` — that pairing misleads AT (the element is announced as a dialog despite not behaving as one). Reserve `role="dialog"` / `role="alertdialog"` for modal variants that capture focus and block background interaction (use `dd-modal` for those).

## Accessibility
**WCAG criteria touched:** 1.3.1, 2.1.1, 2.4.3, 2.4.6, 2.4.11 Focus Not Obscured (Minimum), 2.5.8 Target Size (Minimum), 3.2.1 On Focus, 3.2.2 On Input, 4.1.2.

- Banner is a NON-MODAL region. Use `role="region"` + `aria-label="Cookie consent"`. Do not use `role="dialog"` with `aria-modal="false"` — AT announces a "dialog" that doesn't behave like one.
- Buttons MUST be `type="button"` to prevent accidental form submission when banner sits inside a form.
- **Focus management:**
  - On initial page load: DO NOT move focus to the banner. Stealing focus mid-task violates 3.2.1 and disorients keyboard/SR users. Let the banner announce passively via the region landmark.
  - When summoned by an explicit user action (e.g. a "Manage cookies" link / footer button): THEN move focus to the first banner button.
  - On dismissal: return focus to the element that summoned it (or leave focus where it was if banner appeared on load).
- Banner must not obscure focused content (2.4.11). Position at bottom and avoid fixed full-screen overlay; or ensure focused page content scrolls into view above the banner.
- Decline must be equally prominent — no dark patterns. Contrast and target size parity with Accept (2.5.8: 24×24 CSS px minimum).
- Choice must persist (server-side or `localStorage`). Re-prompting after explicit decline within the storage period violates 3.2.2.
- Keyboard: Tab moves between Accept and Decline. Esc behavior — ONLY close the banner if your storage model has an "ask again later" state. NEVER map Esc to silent Decline; that changes user state without consent (3.2.2 violation).

## Design tokens
| token | usage |
|---|---|
| `$c_text_primary` / `--dark` | message text |
| `$c_primary_action_*` | Accept button states |
| `$c_secondary_action_*` | Decline button states |
| `$c_support_overlay` / `--dark` | optional backdrop |
| `$c_support_border` / `--dark` | banner border |
| `$c_support_focus` / `--dark` | button focus outline |
| `l-box` | inner padding |

## JS hooks
- `onclick="handleCookieConsent('accept'|'decline')"` — your handler persists choice and updates `gtag('consent', 'update', {...})`.
- `hx-on::after-request="dd_cookie_consent()"` — htmx callback fired after consent server round-trip (optional).
- Initial visibility: JS reads stored consent on page load and toggles `display`.

### Reference JS contract
```js
function handleCookieConsent(action) {
  const granted = action === 'accept';
  localStorage.setItem('dd-cookie-consent', granted ? 'granted' : 'denied');
  gtag('consent', 'update', {
    ad_storage: granted ? 'granted' : 'denied',
    analytics_storage: granted ? 'granted' : 'denied'
  });
  document.getElementById('cookie-consent').style.display = 'none';
}
function dd_cookie_consent() {
  if (!localStorage.getItem('dd-cookie-consent')) {
    document.getElementById('cookie-consent').style.display = 'block';
  }
}
```

## Example params
```json
{
  "message": "We use cookies for analytics. Accept tracking?",
  "accept_text": "Accept all",
  "decline_text": "Reject all"
}
```

## Platform translation
**Static HTML:** Include component + JS contract verbatim. Wire `gtag` to GA4 measurement ID.

**Drupal Twig:** Embed in `page.html.twig` near `</body>`. Pair with a Drupal module exposing consent state via `drupalSettings`. JS belongs in a library declared in `*.libraries.yml` and attached globally.

**WordPress:** Echo from `wp_footer` action. Use a plugin like Complianz or Cookie Notice if already installed — disable this component to avoid double-prompting. Wire `gtag` via Site Kit or manual `wp_head` script.
