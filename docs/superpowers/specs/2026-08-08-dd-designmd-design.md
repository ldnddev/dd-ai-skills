# dd-designmd — Semantic Design System Extraction

**Date:** 2026-08-08  
**Status:** Approved  
**Skill name:** `dd-designmd`  
**Plugin root (proposed):** `custom/dd-designmd/`  
**Gold fixture:** `https://www.ldnddev.com`

---

## Decisions (locked from intake)

| # | Topic | Choice |
|---|--------|--------|
| 1 | Audience | **All of the above** — clients, engineers, designers (mixed-audience doc) |
| 2 | Crawl scope | **Single URL →** homepage + linked top nav (capped). **Multiple URLs →** user-provided list only |
| 3 | Evidence | **Default static HTML+CSS**; optional Playwright computed styles / screenshots |
| 4 | Depth | **Full DS lead brief** — foundations, semantic tokens, components, patterns, do/don’t, implementation notes |
| 5 | Output location | **CWD:** `{domain}-design.md` (plus token artifact per #7) |
| 6 | dd-framework | **Always both** — “as observed” + **Framework mapping** sections |
| 7 | Deliverables | **MD + machine-readable tokens** (`tokens.json` and/or CSS variables snippet) |
| 8 | Hard rules | Do **not** invent invisible brand guidelines; do **not** recommend a full rebrand; do **not** score a11y/SEO; do **not** overwrite existing design files without asking |
| 9 | Naming / triggers | `dd-designmd`; phrases: design system from URL, extract design tokens, semantic design system, `/dd-designmd` |
| 10 | Fixture | `www.ldnddev.com` for RED/GREEN skill tests |

---

## Goal

Given one or more website URLs, act as an **Expert Design System Lead**: collect visual/structural evidence, synthesize a **semantic design system** (named tokens + components + patterns + usage rules), and write:

1. `{domain}-design.md` — primary narrative / system brief  
2. `{domain}-tokens.json` (and/or `{domain}-tokens.css`) — portable token dump  

Suitable for client handoff, engineering rebuild, and design alignment without inventing brand fiction.

---

## Non-goals

- Accessibility scoring or remediation plans → `dd-a11y`  
- SEO / performance scoring → `dd-seo` / `dd-site-speed`  
- Full visual regression → `dd-vreg`  
- Authoring ldnddev Framework HTML as primary output → `dd-framework` (mapping only)  
- Inventing mission, voice, or palette not evidenced on the site  
- Rebrand proposals (“you should change to…”)  
- Silent overwrite of existing `{domain}-design.md` / token files  

---

## Domain naming

From the first / primary URL:

1. Parse netloc, lowercase  
2. Strip leading `www.`  
3. Sanitize for filesystem (keep `.` in domain; replace unsafe chars with `-`)  
4. Outputs:  
   - `acme.com-design.md`  
   - `acme.com-tokens.json`  
   - optional `acme.com-tokens.css`  

Override: `--output-dir` / `--basename` if implemented later; default remains CWD.

**Overwrite policy:** If either file exists, **ask** before replacing (or write dated variants only if user opts in — default is ask).

---

## Crawl rules

### Single URL provided

1. Fetch that URL (after normalizing `https://` if missing).  
2. Parse primary nav / header links (same registrable domain).  
3. Crawl up to **N additional pages** (default **8**, configurable) from top-nav candidates.  
4. Prefer unique templates: home, about, product/service, pricing, blog index, contact.

### Multiple URLs provided

1. Crawl **exactly** the user list (cap default **25**).  
2. Do not expand via nav unless user asks.

### Shared limits

- Same-origin / same eTLD+1 only by default  
- Timeouts, max HTML size, skip binary  
- Record every page scanned in the MD meta section  

---

## Evidence pipeline

### Default (always)

| Script (proposed) | Role |
|-------------------|------|
| `fetch_pages.py` | Fetch HTML, follow redirects, record final URL |
| `extract_css.py` | Collect inline + linked stylesheets (same-origin) |
| `extract_design_signals.py` | Parse colors, font families/sizes, spacing-ish values, radii, shadows, breakpoints from CSS + HTML |
| `emit_tokens.py` | Normalize raw values → candidate token tables (JSON) |

Stdlib-first where possible; document any required deps.

### Optional (`--playwright` / `--deep`)

| Script | Role |
|--------|------|
| `capture_ui.py` | Homepage + key templates screenshots; optional computed-style sampling for main CTAs / headings |

Deep mode **enhances** evidence; it does not invent tokens without measurement.

### LLM role (Design System Lead)

After scripts:

1. Read template + token naming reference.  
2. Promote raw values → **semantic** names (`color.bg.canvas`, `color.text.primary`, `space.section-lg`).  
3. Write Overview, Logo & brand mark, Layout & Spacing, Elevation & Shapes, Color usage rules, Interactive states, Content & copy patterns, and Focus & keyboard from evidence only.  
4. Inventory components & patterns with variants/states.  
5. Write do/don’t grounded in observation, including site-specific generation constraints.  
6. Produce **Framework mapping** (observed UI → nearest `dd-*` components / gaps) and **Agent instructions**.  
7. Mark unknowns as `Evidence: missing` — never fill with imagination.

---

## `{domain}-design.md` required sections

Template lives in `skills/dd-designmd/references/design-doc-template.md`.

1. **Meta** — primary URL, domain, date, pages scanned, evidence mode (static / deep), confidence  
2. **Overview** — product summary, brand style, brand tone (observed copy only), core visual principles. No invented mission/voice.  
3. **Logo & brand mark** — detected assets; usage rules only if on-site  
4. **Foundations**  
   - Color (raw palette + semantic map)  
   - Typography  
   - Motion (if observed)  
   - Breakpoints  
5. **Layout & Spacing** — grid systems, padding rules, container constraints  
6. **Elevation & Shapes** — surface layering, shadows, radii  
7. **Semantic tokens** — table: name | value | role | evidence  
8. **Color usage rules** — when to use each semantic color; forbidden combinations  
9. **Components** — anatomy, variants, notes (states live in Interactive states)  
10. **Interactive states** — shared hover / focus / active / disabled / loading / visited  
11. **Patterns / page templates**  
12. **Iconography & media**  
13. **Content & copy patterns** — heading case, CTA verbs, UI microcopy from samples  
14. **Focus & keyboard** — observed focus/outline facts only (no a11y scores)  
15. **Do / Don’t** — process rules plus site-specific generation constraints that stop common AI UI mistakes  
16. **Implementation notes** — inferred stack (CSS vars, utility classes, WP/theme, etc.) with confidence  
17. **ldnddev Framework mapping** — observed → Framework component / “no match” / gap  
18. **Agent instructions** — how a coding agent must interpret this file when writing UI  
19. **Open questions & missing evidence**  
20. **Appendix** — raw signal summary (optional, keep short)

Tone: professional Design System Lead; usable by non-designers and engineers.

---

## Token artifact(s)

### `{domain}-tokens.json` (required)

```json
{
  "meta": { "domain": "…", "source_url": "…", "generated": "…" },
  "color": { "bg.canvas": { "value": "#…", "evidence": "…" }, … },
  "font": { … },
  "space": { … },
  "radius": { … },
  "shadow": { … },
  "breakpoint": { … }
}
```

### `{domain}-tokens.css` (recommended companion)

```css
:root {
  --color-bg-canvas: #…;
  /* …
}
```

Only include tokens with evidence. Placeholder tokens forbidden.

---

## Framework mapping rules

Always include the **ldnddev Framework mapping** section:

| Observed pattern | Framework map |
|------------------|---------------|
| Hero / banner | `dd-hero` or gap |
| Card grid | `dd-card` |
| … | … |

- Map when structure/intent matches; do not force-fit.  
- Prefer linking to `dd-framework` skill for authoring details rather than duplicating full component specs.  
- If Framework has no analogue, say so and describe observed API.

---

## Hard rules (skill must enforce)

1. **Evidence-bound** — every token/component claim needs a source (CSS rule, computed sample, or screenshot note).  
2. **No invented brand** — no voice/mission/values not on-site.  
3. **No rebrand recommendations** — describe the system that *is*, not the one you wish.  
4. **No a11y/SEO scoring** — may note structural facts (“one H1”) without scores or skill-crossover audits.  
5. **No silent overwrite** — if `{domain}-design.md` or token files exist, ask first.  
6. **Violating the letter is violating the spirit** — “best guess” tokens without evidence = fail.

### Rationalizations to block

| Excuse | Reality |
|--------|---------|
| “Obvious brand color even if not in CSS” | Not evidenced → put under Open questions |
| “I’ll fill semantic names later without values” | Empty token tables are OK; invented values are not |
| “Rebrand would help the client” | Out of scope; describe only |
| “Quick a11y score while I’m here” | Use `dd-a11y` separately |
| “File exists, overwrite is fine” | Ask first |

---

## Agent workflow (SKILL.md summary)

1. Parse URL(s); determine single vs multi mode.  
2. Check for existing output files → ask if present.  
3. Run fetch + extract scripts (default static).  
4. If `--deep` / user asks: Playwright pass.  
5. Load references: template, token-naming, component inventory, Framework mapping guide.  
6. Synthesize MD + JSON (+ CSS).  
7. Self-check against hard rules + required sections.  
8. Report absolute paths of written files + short summary + open questions.

---

## Proposed package layout

```text
custom/dd-designmd/
├── .claude-plugin/plugin.json
├── install.sh
├── README.md
├── CLAUDE.md
├── skills/dd-designmd/
│   ├── SKILL.md
│   └── references/
│       ├── design-doc-template.md
│       ├── token-naming.md
│       ├── component-inventory.md
│       └── framework-mapping.md
└── scripts/
    ├── fetch_pages.py
    ├── extract_css.py
    ├── extract_design_signals.py
    ├── emit_tokens.py
    ├── run_designmd.py          # orchestrator
    └── (optional) capture_ui.py
```

Marketplace: add `dd-designmd` to `.claude-plugin/marketplace.json`.

---

## Testing plan (writing-skills TDD)

### RED (before skill exists)

Subagent: “Extract a design system from https://www.ldnddev.com” **without** skill.  
Expect failures: invented brand prose, missing sections, no tokens file, no Framework map, overwrite risk, a11y/SEO tangents.

### GREEN

With skill + scripts on fixture:  
- Files `ldnddev.com-design.md` + `ldnddev.com-tokens.json`  
- All required sections present  
- Tokens have evidence fields  
- Framework mapping section present  
- No invent/rebrand/a11y-score language  

### REFACTOR

Pressure tests: “just invent the palette”, “overwrite the old file”, “add SEO score while you’re at it”.

---

## Implementation phases (after approval)

1. Scaffold plugin + empty SKILL + references (template first)  
2. Scripts: fetch → CSS → signals → tokens JSON  
3. Orchestrator `run_designmd.py`  
4. SKILL.md agent workflow + hard rules  
5. Framework mapping reference  
6. Optional Playwright deep mode  
7. RED/GREEN subagent tests on ldnddev.com  
8. Marketplace + README + version  

---

## Open defaults (implementer may use unless you override)

| Knob | Default |
|------|---------|
| Single-URL nav expand | max **8** extra pages |
| Multi-URL cap | **25** |
| Domain | lowercase, strip `www.` |
| Token CSS companion | **yes** emit `{domain}-tokens.css` |
| Deep mode | off unless `--deep` or user asks |
| Existing files | **ask** before overwrite |

---

## Success criteria

1. On `https://www.ldnddev.com`, agent produces valid dual deliverables with full section depth.  
2. Mixed audience can use the MD without another skill.  
3. Engineers can paste tokens into a codebase starting point.  
4. Framework section is always present and honest about gaps.  
5. Hard rules hold under pressure scenarios.  
