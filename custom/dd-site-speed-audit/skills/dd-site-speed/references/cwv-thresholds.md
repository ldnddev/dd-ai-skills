# Core Web Vitals thresholds

<!-- Updated: 2026-07-15 -->

Use these thresholds when rating metrics. Prefer **field (CrUX)** when available; otherwise use **lab (Lighthouse)**.

## Core Web Vitals (ranking-relevant)

| Metric | Good | Needs improvement | Poor | Unit |
|--------|------|-------------------|------|------|
| **LCP** (Largest Contentful Paint) | ≤ 2.5s | ≤ 4.0s | > 4.0s | ms |
| **INP** (Interaction to Next Paint) | ≤ 200ms | ≤ 500ms | > 500ms | ms |
| **CLS** (Cumulative Layout Shift) | ≤ 0.1 | ≤ 0.25 | > 0.25 | score |

## Supporting metrics

| Metric | Good | Needs improvement | Poor | Unit |
|--------|------|-------------------|------|------|
| **FCP** | ≤ 1.8s | ≤ 3.0s | > 3.0s | ms |
| **TTFB** | ≤ 800ms | ≤ 1.8s | > 1.8s | ms |
| **SI** (Speed Index) | ≤ 3.4s | ≤ 5.8s | > 5.8s | ms |
| **TBT** (Total Blocking Time, lab) | ≤ 200ms | ≤ 600ms | > 600ms | ms |

## Performance score (Lighthouse)

| Score | Rating |
|-------|--------|
| 90–100 | Excellent |
| 70–89 | Good |
| 50–69 | Needs Improvement |
| 30–49 | Poor |
| 0–29 | Critical |

## Critical rules

1. **INP replaced FID** (Sept 2024). Never report or recommend around FID.
2. Field and lab will disagree — say so. Field is what Google uses for CWV assessment at origin level; lab is reproducible diagnostics.
3. Mobile is usually the stricter target; always report both when the skill runs `both` strategies.
