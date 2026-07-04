---
name: dd-pantheon
description: Update, deploy, and maintain WordPress and Drupal sites hosted on Pantheon. Use whenever the user asks to update plugins, modules, themes, or core; deploy code or config; run database operations; or otherwise maintain a Pantheon-hosted site. Trigger on any mention of Pantheon, terminus, multidev, pantheonsite.io URLs, a .lando.yml with a pantheon recipe, or a site name in this skill's sites.yml registry. If the site turns out to be AWS-hosted, use the dd-aws skill instead.
---

# dd-pantheon: Pantheon Site Updates

Safely update and deploy WordPress and Drupal sites on Pantheon. All remote operations go through terminus with the site identifier format `<site>.<env>` (e.g., `my-site.dev`).

## Step 1: Identify the site

**Check the working directory for `.lando.yml` first.** A `recipe: pantheon` entry confirms the platform and provides `config.framework` (drupal | wordpress) and `config.site` (the terminus site name). `lando terminus`, `lando pull`, and `lando push` are available inside the app. Read `references/lando.md` for the local-first workflow.

**Then read `sites.yml`** (in this skill's directory) for environment names, multidev policy, and repo URL.

- Site in registry → use that data, don't re-ask.
- Site not in registry and no `.lando.yml` → ask for CMS and terminus site name; offer to add it to `sites.yml`.
- If `.lando.yml` shows a non-pantheon recipe or the registry shows the site is AWS-hosted → stop and use the **dd-aws** skill instead.

Load the CMS reference: `references/wordpress.md` or `references/drupal.md`. Wrap every wp-cli/drush command from those files: `terminus remote:wp <site>.<env> -- <cmd>` / `terminus remote:drush <site>.<env> -- <cmd>`.

**When a Lando project is present, prefer the local-first workflow**: pull live data down, run the update locally, verify at the Lando URL, commit, push via git, then run post-deploy steps on the hosted env. Skip local-first only for read-only checks or if the user explicitly asks to operate on a hosted environment.

## Step 2: Safety rules (every operation)

1. **Never update or run destructive operations directly on live.** Work in dev or a multidev, verify, then promote dev → test → live.
2. **Back up before changing anything**: `terminus backup:create <site>.<env> --element=all`, confirm with `terminus backup:list`.
3. **Confirm before destructive actions** (DB overwrites, env:clone-content, force-push): state exactly what will run against which environment and wait for explicit user confirmation.
4. **Preview where possible**: `composer update --dry-run`, `drush config:import --preview=diff`.
5. **Verify after every change**: HTTP 200 on homepage + a key page, CMS status checks, no new errors in logs.
6. **One environment at a time** — verify before promoting.
7. **Echo the full command plan** before executing any multi-step operation.

## Preflight

```bash
terminus auth:whoami                      # if not logged in: terminus auth:login
terminus env:info <site>.<env>
terminus connection:info <site>.<env> --fields=git_command
```

Deployment is **git-based** — confirm connection mode is `git`. If the env is in SFTP mode:

```bash
terminus env:diffstat <site>.dev          # must be EMPTY before switching modes
terminus connection:set <site>.dev git
```

If diffstat shows uncommitted changes, STOP and ask whether to commit them (`terminus env:commit <site>.dev`) or discard.

## Code deployment flow (git mode)

1. Clone/pull the Pantheon repo (from `sites.yml` or `connection:info`).
2. Commit locally; `git push origin master` (Pantheon dev tracks `master`).
3. `terminus workflow:wait <site>.dev` (or `terminus build:workflow:wait` on build-tools sites).
4. Promote:

```bash
terminus env:deploy <site>.test --sync-content --cc --note="<description>"
# verify test, then with user confirmation:
terminus env:deploy <site>.live --cc --note="<description>"
```

`--sync-content` pulls live's DB/files into test so you test against real content. Never on the live deploy.

## Multidev for risky updates

For major core updates or large dependency bumps (when `multidev_ok: true`):

```bash
terminus multidev:create <site>.live <branch>    # clones live code+db+files; branch: ≤11 chars, lowercase alnum + dashes
# ...update and verify on <site>.<branch>...
terminus multidev:merge-to-dev <site>.<branch>
terminus multidev:delete <site>.<branch> --delete-branch
```

## Upstream updates (Pantheon-managed core)

```bash
terminus upstream:updates:status <site>.dev
terminus upstream:updates:apply <site>.dev --updatedb
```

Composer-managed Drupal sites typically take core via composer, not upstream — check the site's workflow first; if unsure, ask.

## Database/content ops

```bash
terminus backup:create <site>.<env> --element=db               # always first
terminus env:clone-content <site>.<target> --from-env=live     # overwrites target — confirm with user
terminus backup:get <site>.<env> --element=db                  # download a dump URL
```

## Cache and verification

```bash
terminus env:clear-cache <site>.<env>
terminus env:code-log <site>.<env>
curl -sI https://<env>-<site>.pantheonsite.io | head -1        # expect 200
```

## Reporting

When done, report: what changed (versions before → after), environments touched, backup timestamps, and verification results.
