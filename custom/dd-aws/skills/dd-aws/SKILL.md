---
name: dd-aws
description: Update, deploy, and maintain WordPress and Drupal sites hosted on AWS (EC2/RDS/CloudFront). Use whenever the user asks to update plugins, modules, or core; deploy code or config; run database operations; or otherwise maintain an AWS-hosted site. Trigger on mentions of AWS, EC2, RDS, SSM, CloudFront, Bitbucket Pipelines deploys, or a site name in this skill's sites.yml registry. If the site turns out to be Pantheon-hosted, use the dd-pantheon skill instead.
---

# dd-aws: AWS Site Updates

Safely update and deploy WordPress and Drupal sites on AWS. There is no platform CLI — access varies per site, so the site's `access` field in `sites.yml` determines everything. Never assume SSH access exists.

## Step 1: Identify the site

**Check the working directory for `.lando.yml` first.** A recipe like `drupal10`, `drupal11`, or `wordpress` identifies the CMS; hosting details come from `sites.yml`. Read `references/lando.md` for the local-first workflow. (A `recipe: pantheon` means this site belongs to the **dd-pantheon** skill — stop and use that instead.)

**Then read `sites.yml`** (in this skill's directory) for the access method, branch map, and AWS resource IDs.

- Site in registry → use that data, don't re-ask.
- Site not in registry → ask for CMS, access method, and environment details; offer to add it to `sites.yml`.

Load the CMS reference: `references/wordpress.md` or `references/drupal.md`.

**When a Lando project is present, prefer the local-first workflow**: sync prod data down, run the update locally, verify at the Lando URL, commit, deploy through the site's normal channel, then run post-deploy steps on the hosted env.

## Step 2: Access decision tree

Follow the site's `access` field:

- **`ssh`** — run commands over SSH:
  ```bash
  ssh -i <ssh_key> <ssh_host> 'echo ok'                    # preflight connectivity
  ssh -i <ssh_key> <ssh_host> 'cd <docroot> && <command>'
  ```
  Run wp-cli/drush as the web user; check file ownership after commands that write files (`chown` mismatches are the #1 post-update breakage on EC2).
- **`ssm`** — AWS SSM Session Manager:
  ```bash
  aws ssm start-session --target <instance_id> --profile <aws_profile>
  ```
  Prefer an interactive session for multi-step work over chained `send-command` calls.
- **`pipeline`** — code changes go through CI/CD ONLY. Never edit server files directly, even if SSH/SSM credentials work — the next deploy would wipe the changes. DB/content ops may still be allowed via `db_ops_access` if set.

## Step 3: Safety rules (every operation)

1. **Never update or run destructive operations directly on production.** Update locally or on staging first, verify, then promote.
2. **Back up before DB-touching operations** (RDS snapshot section below); confirm the backup completed before proceeding.
3. **Confirm before destructive actions** (DB imports over hosted envs, data deletion): state exactly what will run and where, wait for explicit confirmation.
4. **Preview where possible**: `composer update --dry-run`, `drush config:import --preview=diff`.
5. **Verify after every change**: HTTP 200 checks, CMS status checks, only-new-errors log review.
6. **One environment at a time** — staging verified before production.
7. **Echo the full command plan** before executing any multi-step operation.

## Pipeline deploy flow (CI/CD, e.g. Bitbucket Pipelines)

1. Clone the repo (`repo` in registry), create a working branch.
2. Make changes locally (composer updates, exported config, plugin updates via Lando).
3. Push and PR into the staging branch (`branch_map.staging`). Pipeline deploys on merge.
4. Run post-deploy steps on staging (updb/cim/cr or update-db/cache flush per the CMS reference) — unless the pipeline already runs them; check the pipeline config before double-running.
5. Verify staging → with user confirmation, merge to the production branch (`branch_map.production`) → verify production.

## Database backups (before any DB-touching op)

Prefer an RDS snapshot. Use the per-environment identifier from `sites.yml` (`rds_identifier.staging` vs `.production`):

```bash
aws rds create-db-snapshot --db-instance-identifier <rds_id> \
  --db-snapshot-identifier <site>-pre-update-$(date +%Y%m%d-%H%M) --profile <aws_profile>
aws rds describe-db-snapshots --db-snapshot-identifier <that-id> \
  --query 'DBSnapshots[0].Status' --profile <aws_profile>       # poll until "available"
```

Fallback on the server: `drush sql:dump` / `wp db export` / `mysqldump` to a timestamped file outside the docroot.

## Getting a DB dump to your local machine

- **SSH sites**: `scp -i <ssh_key> <ssh_host>:<dump-path> .`
- **SSM sites** (no direct file transfer — use an S3 hop):
  ```bash
  # in the SSM session:
  aws s3 cp <dump-file> s3://<s3_transfer_bucket>/tmp/<dump-file>
  # locally:
  aws s3 cp s3://<s3_transfer_bucket>/tmp/<dump-file> . --profile <aws_profile>
  aws s3 rm s3://<s3_transfer_bucket>/tmp/<dump-file> --profile <aws_profile>   # always clean up
  ```
  If no `s3_transfer_bucket` is set for the site, ask the user which bucket to use.

## Post-deploy cache invalidation

Clear the CMS cache first (`drush cr` / `wp cache flush`), then if `cloudfront_distribution` is set:

```bash
aws cloudfront create-invalidation --distribution-id <cloudfront_distribution> \
  --paths "/*" --profile <aws_profile>
```

Invalidating CloudFront without an origin cache clear just re-caches stale content.

## Verification

```bash
curl -sI https://<site-domain> | head -1                # expect 200
tail -50 /var/log/httpd/error_log                       # (or nginx equivalent) — NEW errors only
```

## Reporting

When done, report: what changed (versions before → after), environments touched, snapshot/backup IDs, and verification results.
