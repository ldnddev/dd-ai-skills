# dd-crawl

Whole-site **URL inventory** + **broken-link check**. Stdlib crawler; Framework dashboard with CSV/JSON downloads.

## Install

```bash
/plugin marketplace update dd-skills
/plugin install dd-crawl@dd-skills
```

Codex: `bash custom/dd-crawl-audit/install.sh`

## Quick start

```bash
python3 scripts/run_crawl.py https://example.com
# → web/example.com-crawl-YYYY-MM-DD/index.html
```

## Defaults

- Max pages: 500  
- Delay: **1.0s** between page fetches  
- External links checked  
- robots.txt respected (`--robots-override` to skip)  
- `--web` bundle under `web/`  

See `skills/dd-crawl/SKILL.md` for full options.
