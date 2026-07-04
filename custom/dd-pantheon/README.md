# dd-pantheon — Pantheon Site Updates Skill

Safely update, deploy, and maintain **WordPress and Drupal sites hosted on Pantheon**. All remote operations go through `terminus` with the `<site>.<env>` identifier format. Local-first via Lando when a `.lando.yml` with a `pantheon` recipe is present. A per-site `sites.yml` registry drives environment names, multidev policy, and repo URLs.

## Install — Claude Code plugin

```bash
/plugin marketplace add ldnddev/dd-ai-skills
/plugin install dd-pantheon@dd-skills
```

## Install — Codex skill

`bash install.sh` from this directory — mirrors `skills/dd-pantheon/` into `${CODEX_HOME:-~/.codex}/skills/dd-pantheon`. See [root README](../../README.md) for context.

## Requirements

- [`terminus`](https://docs.pantheon.io/terminus/install) for remote Pantheon operations
- [Lando](https://docs.lando.dev/) (optional) for the local-first workflow

## Trigger phrases

- "update plugins / modules / themes / core on <site>"
- "deploy code / config to <site>"
- mentions of Pantheon, terminus, multidev, or `*.pantheonsite.io`
- a `.lando.yml` with `recipe: pantheon`
- a site name listed in this skill's `sites.yml`

> If the site turns out to be AWS-hosted, use the **dd-aws** skill instead.

## Layout

```
skills/dd-pantheon/
├── SKILL.md              # workflow — identify site, update, deploy
├── sites.yml             # per-site registry (envs, multidev policy, repo)
└── references/
    ├── lando.md          # local-first Lando workflow
    ├── drupal.md         # Drupal update/deploy specifics
    └── wordpress.md      # WordPress update/deploy specifics
```
