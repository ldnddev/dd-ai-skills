# WCAG 2.2 Checklist

Success criteria, levels, and names are `WCAG22` in `scripts/wcag_criteria.py`. The report uses that list.

## Checks the criterion name does not spell out

- 1.1.1: an informative image needs a text alternative. A decorative image uses `alt=""`. A complex image needs a description beyond a short alt. A CAPTCHA needs an alternative.
- 1.4.3: 4.5:1 for normal text.
- 1.4.4: text can resize to 200% without losing content or function.
- 1.4.6: 7:1.
- 1.4.10: content reflows at 400% zoom without a horizontal scrollbar at a 320px width.
- 1.4.11: 3:1 for user-interface components and meaningful graphics.

Target size is in `wcag-audit-rubric.md`: 2.5.8 is 24×24 CSS pixels or enough spacing, and 44×44 is 2.5.5 AAA.

## Mobile

- A complex gesture has a single-pointer alternative.
- A swipe can be done with one pointer.
- Pinch or zoom is not required for the task.
- Test portrait and landscape. Content is not locked to one orientation (1.3.4).

## Testing

- axe-core finds on average 57% of WCAG issues automatically. A passing scan is not a conformance claim.
- Leave best-practice and `wcag2a-obsolete` rules out of the scan.
- Manual checks still include keyboard, screen reader (NVDA, VoiceOver, JAWS), contrast, focus, and a phone or a narrow viewport.

## Legal

- ADA: WCAG 2.0/2.1 Level AA. Public accommodations and commercial facilities.
- Section 508: WCAG 2.0 Level AA. Federal agencies and contractors.
- AODA: WCAG 2.0 Level AA. Organizations in Ontario.
- EN 301 549: WCAG 2.1 Level AA. EU public sector.
