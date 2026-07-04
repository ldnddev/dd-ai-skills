# dd-aws — AWS Site Updates Skill

Safely update, deploy, and maintain **WordPress and Drupal sites hosted on AWS** (EC2/RDS/CloudFront). There is no platform CLI — access varies per site, so the site's `access` field in `sites.yml` determines everything. Never assume SSH access exists. Local-first via Lando when a `.lando.yml` is present; deploys commonly run through Bitbucket Pipelines.

## Install — Claude Code plugin

```bash
/plugin marketplace add ldnddev/dd-ai-skills
/plugin install dd-aws@dd-skills
```

## Install — Codex skill

`bash install.sh` from this directory — mirrors `skills/dd-aws/` into `${CODEX_HOME:-~/.codex}/skills/dd-aws`. See [root README](../../README.md) for context.

## Requirements

- [AWS CLI](https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html) + SSM Session Manager plugin (per-site, as `sites.yml` dictates)
- [Lando](https://docs.lando.dev/) (optional) for the local-first workflow

## Trigger phrases

- "update plugins / modules / core on <site>"
- "deploy code / config to <site>"
- mentions of AWS, EC2, RDS, SSM, CloudFront, or Bitbucket Pipelines deploys
- a site name listed in this skill's `sites.yml`

> If the site turns out to be Pantheon-hosted, use the **dd-pantheon** skill instead.

## Layout

```
skills/dd-aws/
├── SKILL.md              # workflow — identify site, update, deploy
├── sites.yml             # per-site registry (access method, branch map, AWS IDs)
└── references/
    ├── lando.md          # local-first Lando workflow
    ├── drupal.md         # Drupal update/deploy specifics
    └── wordpress.md      # WordPress update/deploy specifics
```
