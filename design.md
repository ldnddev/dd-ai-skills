# Design — dd-site-compare Dashboard Template

Locked design system. Future Hallmark runs read this file first; the dashboard template and generated reports defer to it. Amend intentionally — the file is the rule.

## System
- Genre · modern-minimal
- Macrostructure · Workbench (adapted for data comparison "workbench")
- Theme · Quiet (system-native restraint, mono ink as accent, tiny focus blue)
- Axes · light / system-native sans + mono label / neutral

## Tokens (canonical · the embedded :root in the template is the source of truth)
```css
:root {
  --color-paper:    oklch(100% 0 0);
  --color-paper-2:  oklch(98.5% 0 0);
  --color-paper-3:  oklch(96% 0 0);
  --color-rule:     oklch(91% 0 0);
  --color-rule-2:   oklch(82% 0 0);
  --color-muted:    oklch(50% 0 0);  /* darkened from 55% for AA: ≥4.5:1 small text on all paper surfaces */
  --color-neutral:  oklch(40% 0 0);
  --color-ink-2:    oklch(28% 0 0);
  --color-ink:      oklch(15% 0 0);
  --color-accent:   oklch(15% 0 0);      /* mono — the data is the accent */
  --color-focus:    oklch(60% 0.10 240); /* tiny blue, keyboard only */

  /* Semantic for status (low chroma tints, Quiet spirit) */
  --color-good:     oklch(42% 0.09 145);
  --color-warn:     oklch(52% 0.09 85);
  --color-bad:      oklch(48% 0.09 25);
  --color-best:     oklch(45% 0.06 210); /* subtle for "winner" highlights */

  --font-display: "Inter", ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
  --font-body:    "Inter", ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
  --font-label:   ui-monospace, "SF Mono", Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace;
  --font-mono:    ui-monospace, "SF Mono", Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace;

  --display-weight: 500;
  --body-weight: 400;
  --label-weight: 500;

  --tracking-tight: -0.015em;
  --tracking-label: 0.04em;

  /* 4pt scale (named, not raw) */
  --space-3xs: 0.125rem;
  --space-2xs: 0.25rem;
  --space-xs:  0.5rem;
  --space-sm:  0.75rem;
  --space-md:  1rem;
  --space-lg:  1.5rem;
  --space-xl:  2rem;
  --space-2xl: 3rem;

  /* Type scale (ratios, clamp for responsive) */
  --text-xs:  0.6875rem;
  --text-sm:  0.75rem;
  --text-md:  0.8125rem;
  --text-lg:  0.9375rem;
  --text-xl:  1.0625rem;
  --text-2xl: 1.25rem;

  --text-value: clamp(1.125rem, 1.8vw, 1.375rem); /* for big numbers in rail */

  /* Easings + radius (Quiet square + soft pill) */
  --ease-out: cubic-bezier(0.16, 1, 0.3, 1);
  --dur-micro: 120ms;
  --dur-short: 220ms;

  --radius-card: 0;
  --radius-pill: 999px;
  --radius-input: 6px;
  --rule-card: 1px;

  /* Elevation (minimal, Quiet) */
  --shadow-card: none;
}

@media (prefers-color-scheme: dark) {
  :root {
    --color-paper:    oklch(14% 0 0);
    --color-paper-2:  oklch(18% 0 0);
    --color-paper-3:  oklch(22% 0 0);
    --color-rule:     oklch(30% 0 0);
    --color-rule-2:   oklch(40% 0 0);
    --color-muted:    oklch(62% 0 0);
    --color-neutral:  oklch(72% 0 0);
    --color-ink-2:    oklch(82% 0 0);
    --color-ink:      oklch(94% 0 0);
    --color-accent:   oklch(94% 0 0);
    --color-focus:    oklch(70% 0.10 240);

    --color-good:     oklch(55% 0.09 145);
    --color-warn:     oklch(62% 0.09 85);
    --color-bad:      oklch(58% 0.09 25);
    --color-best:     oklch(60% 0.06 210);

    --body-weight: 350; /* optical compensation for light on dark */
  }
}
```

## CTA voice
- Primary · small mono export buttons (pill border, paper bg, subtle hover to paper-3, focus ring)
- Secondary · same for the filter input and table interactions

## Motion stance
- minimal CSS transitions on interactive elements (bar fills, button hovers/presses, focus rings, row hovers)
- Reduced-motion fallback · ≤150 ms opacity crossfade.

## Exports
`tokens.css` (embedded :root in the template) is the source of truth. For Tailwind v4 `@theme`, DTCG `tokens.json`, or shadcn/ui CSS variables, ask *"extend design.md with Tailwind exports"* (or the format you want) — Hallmark will append them per export-formats.md.

## Provenance
Extracted from local file dd-site-compare-audit/templates/dashboard.html (user-owned template in the dd-site-compare-audit project, 2026-06-03). Tokens are exact from source CSS. Fonts are role-based with system stacks (no external @font-face). Rhythm from analysis of the source layout (rail + canvas asymmetry, panel framing, small functional labels). This DNA was previously applied via Hallmark redesign (Workbench macro + Quiet theme adaptations for data utility + semantic status tints).

## Notes
Anti-patterns to NOT carry over (flagged during study of the source and avoided in this DNA):
- Uniform equal cards / auto-fit grids without asymmetry (old summary was 5 equal cards; now vertical rail stats + framed panels).
- Heavy dark header bar as dominant element (now compact workbench-header).
- Generic system font (Arial) as sole display+body without mono outlier for data/labels.
- Linear sections without primary axis or rail/canvas split.
- Basic table without sort affordances or refined states.
- Overuse of shadows and heavy borders (Quiet is hairline + minimal elevation).

The template itself carries the Hallmark stamp in its <style> for future reference.

This system is locked for the dashboard template and generated comparison reports. Future Hallmark runs on this template or similar data dashboards should read this file first (inversion of diversification for consistency).
