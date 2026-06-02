#!/bin/bash
set -e
cd /home/guinevere/code/guinevere
source .venv/bin/activate

# Get guinevere_core password from SOPS using the approved age key path.
PW=$(SOPS_AGE_KEY_FILE=/home/guinevere/secrets/age-key.txt sops --decrypt /home/guinevere/secrets/db-passwords.yaml | grep -oP 'guinevere_core:\s*\K.*')
if [ -z "$PW" ]; then
  echo "ERROR: guinevere_core password not found" >&2
  exit 1
fi
export GUINEVERE_DB_PASSWORD="$PW"

echo "=== Current revision ==="
alembic current 2>&1

echo ""
echo "=== Generating autogenerate revision ==="
alembic revision --autogenerate -m 'add_search_vector_do_not_recall' 2>&1

echo ""
echo "=== Migration files ==="
ls -la alembic/versions/ | tail -5

echo ""
echo "=== Upgrade head ==="
alembic upgrade head 2>&1

echo ""
echo "=== Done ==="