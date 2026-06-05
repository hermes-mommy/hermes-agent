#!/bin/bash
set -euo pipefail

echo "=== CUTOVER START: $(date -u +%Y-%m-%dT%H:%M:%SZ) ==="

echo "=== Stopping guinevere-discord ==="
sudo systemctl stop guinevere-discord.service
echo "guinevere-discord STOPPED at $(date -u +%Y-%m-%dT%H:%M:%SZ)"

echo ""
echo "=== Starting hermes-gateway ==="
sudo systemctl start hermes-gateway.service
echo "hermes-gateway STARTED at $(date -u +%Y-%m-%dT%H:%M:%SZ)"

echo ""
echo "=== Waiting 10 seconds for startup ==="
sleep 10

echo ""
echo "=== hermes-gateway status ==="
systemctl status hermes-gateway.service 2>&1

echo ""
echo "=== Last 40 lines of hermes-gateway journal ==="
sudo journalctl -u hermes-gateway.service --no-pager -n 40 2>&1

echo ""
echo "=== guinevere-discord status (should be inactive) ==="
systemctl status guinevere-discord.service 2>&1 | head -5

echo ""
echo "=== CUTOVER END: $(date -u +%Y-%m-%dT%H:%M:%SZ) ==="
