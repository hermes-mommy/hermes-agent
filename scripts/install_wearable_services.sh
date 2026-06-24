#!/usr/bin/env bash
set -euo pipefail

# Install Guinevere wearable health systemd services
# Usage: ./scripts/install_wearable_services.sh

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
SYSTEMD_DIR="/etc/systemd/system"

echo "=== Guinevere Wearable Service Installer ==="

# Copy service files
for unit in guinevere-wearable-sync.service guinevere-wearable-sync.timer \
            guinevere-wearable-analysis.service guinevere-wearable-analysis.timer; do
    echo "Installing $unit..."
    sudo install -m 0644 -o root -g root "$PROJECT_DIR/systemd/$unit" "$SYSTEMD_DIR/$unit"
done

# Secure .env.wearable permissions
if [ -f "$PROJECT_DIR/.env.wearable" ]; then
    echo "Securing .env.wearable permissions..."
    sudo chmod 0600 "$PROJECT_DIR/.env.wearable"
    sudo chown guinevere:guinevere "$PROJECT_DIR/.env.wearable" || true
fi

# Reload systemd
echo "Reloading systemd daemon..."
sudo systemctl daemon-reload

# Enable and start timers
echo "Enabling sync timer..."
sudo systemctl enable --now guinevere-wearable-sync.timer

echo "Enabling analysis timer..."
sudo systemctl enable --now guinevere-wearable-analysis.timer

# Verify
echo ""
echo "=== Service Status ==="
systemctl status guinevere-wearable-sync.timer --no-pager || true
echo ""
systemctl status guinevere-wearable-analysis.timer --no-pager || true

echo ""
echo "=== Next scheduled runs ==="
systemctl list-timers guinevere-wearable-* --no-pager || true

echo ""
echo "✅ Wearable services installed and timers active."
