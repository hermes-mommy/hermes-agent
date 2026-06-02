#!/bin/bash
set -euo pipefail
read -r TOKEN
if [ -z "$TOKEN" ] || [ "${#TOKEN}" -lt 20 ]; then echo "TOKEN_INPUT_INVALID" >&2; exit 1; fi

export GIT_MASTER=1
REPO="/home/guinevere/code/guinevere"
ASKPASS="/tmp/git-askpass-p0-026.sh"

# SOPS encrypt
AGE_PUBKEY="age17cyg77cswk0du44k3r02g3l83x2f62crcnjnzv5cz5vtndve7yksck2zqj"
TMP_SECRET="$(mktemp)"
printf 'github_pat: "%s"\n' "$TOKEN" > "$TMP_SECRET"
mkdir -p /home/guinevere/secrets
sops --age "$AGE_PUBKEY" --encrypt "$TMP_SECRET" > /home/guinevere/secrets/github-pat.yaml
chown guinevere:guinevere /home/guinevere/secrets/github-pat.yaml
chmod 600 /home/guinevere/secrets/github-pat.yaml
TOKEN_SHA256="$(printf '%s' "$TOKEN" | sha256sum | cut -d' ' -f1)"
SECRET_SHA256="$(sha256sum /home/guinevere/secrets/github-pat.yaml | cut -d' ' -f1)"
rm -f "$TMP_SECRET"

# Git setup
sudo -u guinevere git -C "$REPO" branch -M main
sudo -u guinevere git -C "$REPO" remote remove origin >/dev/null 2>&1 || true
sudo -u guinevere git -C "$REPO" remote add origin "https://github.com/fazulfi/guinevere.git"

# Write askpass helper owned by guinevere
printf '#!/bin/bash\necho "%s"\n' "$TOKEN" > "$ASKPASS"
chown guinevere:guinevere "$ASKPASS"
chmod 700 "$ASKPASS"

# Push
sudo -u guinevere env GIT_ASKPASS="$ASKPASS" git -C "$REPO" -c credential.helper= push -u origin main

# Cleanup and verify
shred -u "$ASKPASS" 2>/dev/null || rm -f "$ASKPASS"
sudo -u guinevere env GIT_ASKPASS="$ASKPASS" git -C "$REPO" -c credential.helper= ls-remote --heads origin main >/tmp/p0-026-ls-remote.txt 2>/dev/null || true

echo "SOPS_FILE_OK"
echo "TOKEN_SHA256=$TOKEN_SHA256"
echo "SECRET_FILE_SHA256=$SECRET_SHA256"
echo "PUSH_OK"
cat /tmp/p0-026-ls-remote.txt 2>/dev/null || echo "LS_REMOTE_FAILED"