#!/usr/bin/env bash
# Nightly Postgres backup -> Hetzner Object Storage, 14-day retention
# (CLAUDE.md §11). Run from /opt/leadkar. Suggested cron (host crontab):
#   15 2 * * *  cd /opt/leadkar && scripts/backup_db.sh >> logs/backup.log 2>&1
#
# Requires the AWS CLI on the host (S3-compatible) and S3_* in .env.
set -euo pipefail
cd "$(dirname "$0")/.."

# shellcheck disable=SC1091
set -a; source .env; set +a

STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
DUMP="leadkar_${STAMP}.sql.gz"
KEY="backups/${DUMP}"
RETENTION_DAYS=14

echo "[$(date -u)] dumping database -> $DUMP"
docker compose exec -T postgres pg_dump -U "$POSTGRES_USER" "$POSTGRES_DB" | gzip > "/tmp/${DUMP}"

echo "[$(date -u)] uploading -> s3://${S3_BUCKET}/${KEY}"
AWS_ACCESS_KEY_ID="$S3_ACCESS_KEY" AWS_SECRET_ACCESS_KEY="$S3_SECRET_KEY" \
  aws --endpoint-url "$S3_ENDPOINT" s3 cp "/tmp/${DUMP}" "s3://${S3_BUCKET}/${KEY}"
rm -f "/tmp/${DUMP}"

# Prune objects older than retention from the backups/ prefix.
echo "[$(date -u)] pruning backups older than ${RETENTION_DAYS} days"
CUTOFF="$(date -u -d "${RETENTION_DAYS} days ago" +%Y-%m-%d 2>/dev/null || date -u -v-${RETENTION_DAYS}d +%Y-%m-%d)"
AWS_ACCESS_KEY_ID="$S3_ACCESS_KEY" AWS_SECRET_ACCESS_KEY="$S3_SECRET_KEY" \
  aws --endpoint-url "$S3_ENDPOINT" s3 ls "s3://${S3_BUCKET}/backups/" | while read -r d _ _ name; do
    [[ -z "${name:-}" ]] && continue
    if [[ "$d" < "$CUTOFF" ]]; then
      AWS_ACCESS_KEY_ID="$S3_ACCESS_KEY" AWS_SECRET_ACCESS_KEY="$S3_SECRET_KEY" \
        aws --endpoint-url "$S3_ENDPOINT" s3 rm "s3://${S3_BUCKET}/backups/${name}"
    fi
  done

echo "[$(date -u)] backup complete"
