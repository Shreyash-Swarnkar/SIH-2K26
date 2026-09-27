#!/usr/bin/env bash
# Push the SIH-2K26 project to GitHub using Git Credential Manager (browser sign-in).
# Run:  bash scripts/_push.sh
cd "$(dirname "$0")/.."

echo "==> Making sure remote points at HTTPS (no embedded token)"
git remote set-url origin https://github.com/Shreyash-Swarnkar/SIH-2K26.git

echo "==> Ensuring git identity is set for this repo"
git config user.name  "Shreyash-Swarnkar" 2>/dev/null || true
git config user.email "shreyash@users.noreply.github.com" 2>/dev/null || true

echo "==> Pushing main -> origin/main"
echo "    (A GitHub sign-in window will open in your browser — accept it.)"
git push -u origin main
echo "==> Done (exit $?)"