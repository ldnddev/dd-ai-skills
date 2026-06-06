# Dashboard Fields

**Contract:** The comparison script and the generated dashboard **must include every field below for every analyzed URL/row**. This list is the source of truth (updated for v1.1).

Use the detailed table for implementation, display logic, and audit notes. "Lower better" / "Higher better" guidance helps the dashboard's "best value" highlighting.

## Required Field List (for quick contract checks)

- URL
- status_code
- response_time
- page_size
- total_page_load_size
- resource_count
- js_file_count
- css_file_count
- largest_item
- trackers
- title
- meta_description
- h1_count
- h2_count
- h3_count
- image_count
- images_missing_alt
- link_count
- external_link_count
- technologies
- keywords
- mobile_responsive
- has_favicon
- has_canonical
- json_ld_count
- final_url
- redirected
- word_count
- server
- powered_by
- error

## Detailed Reference

| Field                  | Type          | Description / Computation                                                                 | Notes / "Better" direction                  |
|------------------------|---------------|-------------------------------------------------------------------------------------------|---------------------------------------------|
| URL                    | str           | The exact user-supplied (normalized) URL. Never changed by redirects.                     | Display as-is; link to final if different. |
| status_code            | int \| null   | HTTP status from the homepage response (or the error response).                           | 2xx=good, 3xx=warn, 4xx/5xx=bad.           |
| response_time          | float \| null | Wall time (perf_counter) for the initial homepage request, in seconds.                    | Lower better (TTFB-ish).                   |
| page_size              | int \| null   | Bytes of the homepage response body.                                                      | —                                          |
| total_page_load_size   | int \| null   | page_size + bytes of successfully fetched direct resources (capped).                      | Lower better for perf comparison.          |
| resource_count         | int           | Count of successfully fetched sub-resources (images, css, js, media).                     | —                                          |
| js_file_count          | int           | Subset of resources with JS kind.                                                         | —                                          |
| css_file_count         | int           | Subset of resources with CSS kind.                                                        | —                                          |
| largest_item           | object\|null  | `{url, bytes}` of the single biggest item (homepage or any fetched resource).             | —                                          |
| trackers               | string[]      | Detected known trackers/pixels (GA, GTM, FB, Hotjar, TikTok, LinkedIn, generic 1x1, ...). | Lower usually better for privacy.          |
| title                  | string\|null  | `<title>` text (normalized whitespace).                                                   | —                                          |
| meta_description       | string\|null  | `name=description` or `property=og:description` (first non-empty).                        | —                                          |
| h1_count               | int           | Number of `<h1>` elements.                                                                | Higher often richer content.               |
| h2_count               | int           | Number of `<h2>` (new v1.1).                                                              | Higher often richer structure.             |
| h3_count               | int           | Number of `<h3>` (new v1.1).                                                              | —                                          |
| image_count            | int           | Number of `<img>` (including srcset entries counted separately for resources).            | —                                          |
| images_missing_alt     | int           | `<img>` elements with missing or empty `alt` (new v1.1).                                  | Lower better (a11y).                       |
| link_count             | int           | Total `<a>` elements.                                                                     | —                                          |
| external_link_count    | int           | `<a href>` whose host differs from the page's final host (new v1.1).                      | —                                          |
| technologies           | string[]      | Detected via patterns in HTML, inline scripts, src/href, and fetched text (WP, React, Shopify, jQuery, GA, etc. + headers). | — |
| keywords               | string[]      | Top ~15 scored 1-3 word phrases (title > meta/headings > body). Deterministic, no deps.   | —                                          |
| mobile_responsive      | bool \| null  | True if a viewport meta was seen (name=viewport).                                         | True preferred for modern sites.           |
| has_favicon            | bool          | `<link rel="icon"\|"shortcut icon"\|...>` present (new v1.1).                             | True = more polished.                      |
| has_canonical          | bool          | `<link rel="canonical">` present (new v1.1).                                              | True often good for SEO.                   |
| json_ld_count          | int           | `<script type="application/ld+json">` blocks (new v1.1).                                  | Higher = more structured data.             |
| final_url              | str           | The URL after following redirects (from response.geturl()).                               | Useful when it differs from URL.           |
| redirected             | bool          | `final_url != URL` (normalized) (new v1.1).                                               | —                                          |
| word_count             | int           | Rough token count from title + meta + paragraph/heading text (new v1.1).                  | Proxy for content depth.                   |
| server                 | str \| null   | `Server:` response header value, if present (new v1.1).                                   | —                                          |
| powered_by             | str \| null   | `X-Powered-By`, `X-Generator`, or similar informative header (new v1.1).                  | —                                          |
| error                  | str \| "None" | Error message for the row (or "None"/empty on success). Never drop the row.               | Present = investigate.                     |

**Implementation note:** All new v1.1 fields are populated from the homepage fetch + HTML parse + response headers already performed for the original 19 fields. No extra network round-trips for the core contract.

When extending, keep this file and the `FIELD_ORDER` list in the script in sync.
