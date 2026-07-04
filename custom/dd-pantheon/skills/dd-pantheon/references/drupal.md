# Drupal Reference (composer + drush)

All sites are composer-managed. Code changes (core/module updates) happen in the **git repo via composer**, never by running update commands on the server. Drush handles DB updates, config, and cache. On Pantheon, wrap drush: `terminus remote:drush <site>.<env> -- <command>`.

## Status checks (read-only)

```bash
composer outdated "drupal/*"              # in the repo
drush status
drush pm:security                          # security-only module report
drush core:requirements --severity=2      # errors only
```

## Update sequence (the canonical flow)

1. **In the repo**, on a working branch:
   ```bash
   composer update "drupal/<module>" --with-dependencies --dry-run   # preview
   composer update "drupal/<module>" --with-dependencies
   # core: composer update "drupal/core-recommended" --with-dependencies
   git add composer.json composer.lock && git commit
   ```
2. **Deploy** to dev/staging per the platform reference (Pantheon git push / AWS pipeline).
3. **On the target environment**, run the post-deploy sequence in this exact order:
   ```bash
   drush updb -y          # database updates
   drush cr               # cache rebuild
   drush cex --diff       # check: did the update change config?
   ```
4. **Config decision point** — if `cex` shows differences after `updb`, the update modified active config. Export it, commit it to the repo, and redeploy — otherwise the next `cim` will revert the update's config changes. This is the most common Drupal update mistake; when in doubt, show the user the diff and ask.

## Config management (deploying config changes)

Standard flow for "push my config changes":

```bash
# locally / on source env:
drush cex -y && git add config/ && git commit
# deploy code, then on target env:
drush cim --preview=diff        # show the user what will change
drush cim -y                    # after confirmation
drush cr
```

Never run `cim` on an environment that has uncommitted config drift without showing the diff first — it silently deletes config that isn't in the sync directory.

## Gotchas

- **Patches**: check `composer.json` for `extra.patches` before updating a patched module — the patch may not apply to the new version. If `composer update` fails on a patch, report it rather than removing the patch.
- **updb before cim vs cim before updb**: default is `updb` → `cim` on deploys (matches most CI setups), but check the site's deploy script — consistency with the pipeline matters more than the general rule. `drush deploy` runs the full canonical sequence (updr, updb, cim, cr) if available.
- **Major core jumps** (e.g., 10→11): run upgrade_status checks first; this is a project, not a routine update — flag it.
- **Multisite**: add `--uri=<site>` to every drush command.

## Database/content ops

```bash
drush sql:dump --result-file=../backup-$(date +%Y%m%d).sql --gzip   # AWS backup (Pantheon: terminus backup)
drush sql:sync @prod @staging      # if aliases configured — confirm with user, overwrites target
drush sql:query "..."              # read queries fine; write queries need confirmation
```

## Verification after updates

```bash
drush core:requirements --severity=2      # should show no new errors
drush watchdog:show --count=20            # look for new errors post-update
curl -sI <homepage> | head -1             # expect 200
```
