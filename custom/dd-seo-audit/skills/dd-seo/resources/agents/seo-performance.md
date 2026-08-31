---
name: seo-performance
description: >
  Do not measure Core Web Vitals here. Speed, CWV, and Lighthouse audits are
  dd-site-speed. If invoked from an SEO audit, point to that skill and skip PSI.
tools: Read
---

Core Web Vitals are **not** part of dd-seo. Do not run `pagespeed.py`, call the PageSpeed Insights API, or invent LCP/INP/CLS values.

If the user asked for speed, CWV, Lighthouse, or "make the site faster", use **dd-site-speed**.

If this agent was opened during an SEO audit, add one line to the SEO report: measure CWV with **dd-site-speed**. Then stop.
