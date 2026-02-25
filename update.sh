#!/usr/bin/env bash
# GEO Optimizer — Update Script
# Pulls the latest version from GitHub and reinstalls dependencies.
#
# Usage: bash update.sh

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

GREEN='\033[0;32m'
NC='\033[0m'
ok() { echo -e "${GREEN}✅ $1${NC}"; }

echo ""
echo "🔄 GEO Optimizer — Updating..."
echo ""

cd "$SCRIPT_DIR"

# Check we're in a git repo
if [ ! -d ".git" ]; then
  echo "❌ Not a git repository. Was this installed with install.sh?"
  echo "   Re-install with: bash install.sh"
  exit 1
fi

# Show current version
CURRENT=$(git log --oneline -1)
echo "   Current: $CURRENT"

# Pull latest
git pull origin main

# Show new version
NEW=$(git log --oneline -1)
echo "   Latest:  $NEW"

# Update dependencies (use venv if present, otherwise system pip)
if [ -f ".venv/bin/pip" ]; then
  .venv/bin/pip install -r requirements.txt -q
  ok "Dependencies up to date (venv)"
elif command -v pip3 >/dev/null 2>&1; then
  pip3 install -r requirements.txt -q
  ok "Dependencies up to date"
elif command -v pip >/dev/null 2>&1; then
  pip install -r requirements.txt -q
  ok "Dependencies up to date"
fi

echo ""
ok "GEO Optimizer updated successfully!"
echo ""
echo "📖 Changelog: https://github.com/auriti-labs/geo-optimizer-skill/blob/main/CHANGELOG.md"
echo ""
