# dd-skills

Custom Claude Code plugin marketplace by [ldnddev](https://ldnddev.com). Single git repo, multiple installable plugins, each independently versioned and selectable.

## What's in here

| Plugin | Skill name | Purpose | Deps |
|---|---|---|---|
| [dd-a11y](custom/dd-a11y-audit/) | `dd-a11y` | WCAG 2.2 accessibility audit (Playwright + axe-core), single + multi-page | npm |
| [dd-blogs](custom/dd-blogs/) | `dd-blogs` | ldnddev brand-tone blog copywriting + deliverables | — |
| [dd-framework](custom/dd-framework/) | `dd-framework` | ldnddev Framework component authoring (`dd-hero`, `dd-card`, etc.) | — |
| [dd-seo](custom/dd-seo-audit/) | `dd-seo` | LLM-first SEO audits (sites, blog posts, GitHub repos) — 30+ scripts | python |
| [dd-vreg](custom/dd-vreg-audit/) | `dd-vreg` | Two-site screenshot diff reporter (Playwright + pixelmatch) | npm |

## Install

Add this marketplace once, then install plugins independently.

```bash
/plugin marketplace add jlyvers/dd-ai-skills
/plugin install dd-a11y@dd-skills
/plugin install dd-seo@dd-skills
/plugin install dd-vreg@dd-skills
# ...etc
```

Update later:

```bash
/plugin marketplace update dd-skills
/plugin update dd-a11y@dd-skills
```

Remove:

```bash
/plugin uninstall dd-a11y@dd-skills
```

## Codex install (legacy)

Each plugin ships its own `install.sh` for Codex CLI. Run from the plugin's directory:

```bash
bash custom/dd-a11y-audit/install.sh    # → ~/.codex/skills/dd-a11y/
bash custom/dd-blogs/install.sh         # → ~/.codex/skills/dd-blogs/
bash custom/dd-framework/install.sh     # → ~/.codex/skills/dd-framework/
bash custom/dd-seo-audit/install.sh     # → ~/.codex/skills/dd-seo/
bash custom/dd-vreg-audit/install.sh    # → ~/.codex/skills/dd-vreg/
```

Override install root with `CODEX_HOME=/path` env var.

## Repo layout

```
dd-ai-skills/
├── .claude-plugin/marketplace.json   ← lists every plugin in this repo
├── LICENSE
├── README.md                          ← you are here
├── contrib/                           ← (placeholder, third-party contributions)
└── custom/
    ├── dd-a11y-audit/                 ← plugin root
    │   ├── .claude-plugin/plugin.json
    │   ├── skills/dd-a11y/SKILL.md    ← canonical skill body
    │   ├── hooks/{hooks.json, *.sh}
    │   ├── scripts/, templates/, package.json
    │   ├── install.sh                 ← Codex install path
    │   └── README.md
    ├── dd-blogs/                      ← (same pattern)
    ├── dd-framework/
    ├── dd-seo-audit/
    └── dd-vreg-audit/
```

## How a plugin is wired

Each `custom/<plugin>/` is self-contained:

- `.claude-plugin/plugin.json` — declares `name`, `skills`, optional `hooks`
- `skills/<skill-name>/SKILL.md` — canonical skill body. Frontmatter `name:` is the trigger identifier
- `hooks/hooks.json` (optional) — uses `${CLAUDE_PLUGIN_ROOT}` for portable paths
- `package.json` (optional) — npm deps; `postinstall` may pull browsers
- `install.sh` — Codex install path; promotes `skills/<name>/SKILL.md` to install root and renders `settings.json` from `hooks/hooks.json`

`${CLAUDE_PLUGIN_ROOT}` resolves per-plugin, so plugins do not collide. `node_modules`, sentinels (`.dd-*-bootstrap.ok`), and hook state are isolated.

## First-session bootstrap

`dd-a11y` and `dd-vreg` use a `SessionStart` hook (`hooks/bootstrap.sh`) that runs `npm ci` (or `npm install`) on first session — and Playwright Chromium download. Idempotent. Subsequent sessions short-circuit on a sentinel file.

Skip browser download:

```bash
DD_A11Y_SKIP_BROWSER=1   # for dd-a11y
DD_VREG_SKIP_BROWSER=1   # for dd-vreg
```

## Adding a new plugin to this marketplace

1. `mkdir -p custom/<new-plugin>/{.claude-plugin,skills/<skill-name>}`
2. Write `custom/<new-plugin>/.claude-plugin/plugin.json`:
   ```json
   {
     "name": "dd-<short>",
     "version": "1.0.0",
     "description": "...",
     "skills": ["./skills/<skill-name>"]
   }
   ```
3. Write `custom/<new-plugin>/skills/<skill-name>/SKILL.md` with frontmatter `name: <skill-name>` + description.
4. (Optional) Add `hooks/hooks.json`, `package.json`, `install.sh`.
5. Append entry to root `.claude-plugin/marketplace.json` `plugins[]`.
6. Commit + push. Users run `/plugin marketplace update dd-skills` to see it.

## CI / local validation

GitHub Actions runs on every push + PR via `.github/workflows/validate.yml`. It validates:

- Marketplace + plugin manifests (`scripts/validate_marketplace.py` — stdlib only, no install needed)
- Shell script syntax (`shellcheck --severity=error` over every `install.sh` and `hooks/*.sh`)
- JSON files parse (`jq`)
- npm lockfiles consistent with package.json (`npm ci --ignore-scripts` per plugin)

Run locally before committing:

```bash
python3 scripts/validate_marketplace.py
```

The validator enforces:

- Plugin name matches `dd-<short>` regex
- Plugin name in marketplace == name in plugin.json == skill `name:` in SKILL.md frontmatter
- Each declared skill path resolves to a directory with a SKILL.md
- Hook commands use `${CLAUDE_PLUGIN_ROOT}` for portability (warn if not)
- npm dependencies pinned to exact versions (warn on `^`/`~`)
- package.json name == plugin name; package-lock.json name == package.json name
- License is `MIT` across `plugin.json` (required), `package.json` (required if file exists), and `SKILL.md` frontmatter (required if `license:` declared)
- bash syntax of install.sh + hook scripts

## Conventions

- Plugin name: `dd-<short>` (e.g. `dd-a11y`, `dd-seo`)
- Skill name (inside `SKILL.md`): matches the plugin name. All skills use the `dd-` prefix.
- Codex install dir = skill name (matches Codex's `~/.codex/skills/<skill-name>` lookup)
- One canonical `SKILL.md` per skill, lives at `skills/<skill-name>/SKILL.md`. `install.sh` copies it to install root for Codex.
- Pin npm deps to exact versions (no `^`/`~`). Pinning `playwright` pins Chromium revision transitively.
- Hook scripts use `${CLAUDE_PLUGIN_ROOT}` (Claude Code) or fall back to `$(dirname $0)/..` (Codex).

## License

[MIT](LICENSE)

## Author

Jared Lyvers · [ldnddev.com](https://ldnddev.com) · jared@ldnddev.com
