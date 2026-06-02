#!/usr/bin/env bash
set -euo pipefail

VERIFY_SCRIPT="${1:-}"
if [[ -z "$VERIFY_SCRIPT" ]]; then
  echo "usage: scripts/run-discord-verify.sh tmp/verify-p2-004-guild-name.py" >&2
  exit 2
fi

case "$VERIFY_SCRIPT" in
  tmp/verify-p2-004-guild-name.py|tmp/verify-p2-004-audit-log.py|tmp/verify-p2-005-categories.py|tmp/verify-p2-006-channels.py|tmp/verify-p2-006-channels-rest.py|tmp/setup-p2-007-permissions.py|tmp/setup-p2-008-topics.py|tmp/verify-p2-007-permissions-rest.py|tmp/verify-p2-008-topics-rest.py|tmp/verify-p2-009-bot-permissions-rest.py|tmp/sync-p2-010-commands.py|tmp/verify-p2-010-commands-rest.py) ;;
  *) echo "invalid verifier: $VERIFY_SCRIPT" >&2; exit 2 ;;
esac

PROJECT_ROOT="/home/guinevere/code/guinevere"
SECRET_FILE="$PROJECT_ROOT/secrets/discord-secrets.yaml"
AGE_KEY_FILE="/home/guinevere/secrets/age-key.txt"
TEMP_SECRETS="$(mktemp /tmp/guinevere-discord-verify.XXXXXX.yaml)"

cleanup() {
  unset DISCORD_SECRETS_PATH || true
  shred -u "$TEMP_SECRETS" 2>/dev/null || rm -f "$TEMP_SECRETS"
}
trap cleanup EXIT

export SOPS_AGE_KEY_FILE="$AGE_KEY_FILE"
sops --decrypt "$SECRET_FILE" > "$TEMP_SECRETS"
chmod 600 "$TEMP_SECRETS"
export DISCORD_SECRETS_PATH="$TEMP_SECRETS"

cd "$PROJECT_ROOT"
"$PROJECT_ROOT/.venv/bin/python" "$VERIFY_SCRIPT"
