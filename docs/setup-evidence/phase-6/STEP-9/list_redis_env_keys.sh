#!/bin/bash
set -euo pipefail
cd /home/guinevere/code/guinevere
for f in .env.core .env .env.hermes /home/guinevere/.hermes/.env; do
  if [ -f "$f" ]; then
    echo "FILE:$f"
    python3 - "$f" <<'PY'
from pathlib import Path
import sys
for line in Path(sys.argv[1]).read_text(encoding='utf-8', errors='replace').splitlines():
    if line.startswith('#') or '=' not in line:
        continue
    key = line.split('=', 1)[0]
    if 'REDIS' in key:
        print(f'{key}=<redacted>')
PY
  fi
done
