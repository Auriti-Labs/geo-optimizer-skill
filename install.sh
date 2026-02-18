#!/usr/bin/env bash
# GEO Optimizer — Installation Script
# https://github.com/auriti-web-design/geo-optimizer-skill
#
# Usage:
#   curl -sSL https://raw.githubusercontent.com/auriti-web-design/geo-optimizer-skill/main/install.sh | bash
#   OR: bash install.sh [--dir /custom/path]
#
# NOTE: --dir cannot be used with curl | bash (the flag goes to bash, not this script).
# To install to a custom path, download first:
#   curl -sSL https://raw.githubusercontent.com/auriti-web-design/geo-optimizer-skill/main/install.sh -o install.sh
#   bash install.sh --dir /custom/path

set -e

REPO_URL="https://github.com/auriti-web-design/geo-optimizer-skill.git"
DEFAULT_DIR="$HOME/geo-optimizer-skill"

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

ok()   { echo -e "${GREEN}✅ $1${NC}"; }
warn() { echo -e "${YELLOW}⚠️  $1${NC}"; }
err()  { echo -e "${RED}❌ $1${NC}"; exit 1; }
info() { echo -e "   $1"; }

INSTALL_DIR="$DEFAULT_DIR"

# Parse args
while [[ $# -gt 0 ]]; do
  case "$1" in
    --dir=*) INSTALL_DIR="${1#*=}"; shift ;;
    --dir)   shift; INSTALL_DIR="$1"; shift ;;
    *)       shift ;;
  esac
done

echo ""
echo "🤖 GEO Optimizer — Installation"
echo "================================"
echo ""

# Check git
command -v git >/dev/null 2>&1 || err "git is required. Install it first: https://git-scm.com"
ok "git found"

# Check Python
command -v python3 >/dev/null 2>&1 || err "Python 3 is required. Install it first: https://python.org"
PYTHON_VER=$(python3 --version 2>&1)
ok "Python found: $PYTHON_VER"

# Clone or update
if [ -d "$INSTALL_DIR/.git" ]; then
  echo ""
  echo "📂 Existing installation found at: $INSTALL_DIR"
  echo "   Running update instead..."
  cd "$INSTALL_DIR"
  git pull origin main
  ok "Updated to latest version"
else
  echo ""
  echo "📥 Cloning repository to: $INSTALL_DIR"
  git clone "$REPO_URL" "$INSTALL_DIR"
  ok "Repository cloned"
fi

# Install Python dependencies in a virtual environment
echo ""
echo "📦 Setting up Python virtual environment..."
python3 -m venv "$INSTALL_DIR/.venv"
ok "Virtual environment created"

echo "   Installing dependencies..."
"$INSTALL_DIR/.venv/bin/pip" install -r "$INSTALL_DIR/requirements.txt" -q
ok "Dependencies installed (requests, beautifulsoup4, lxml)"

# Create ./geo wrapper so users don't need to activate the venv manually
cat > "$INSTALL_DIR/geo" << 'WRAPPER'
#!/usr/bin/env bash
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec "$DIR/.venv/bin/python3" "$@"
WRAPPER
chmod +x "$INSTALL_DIR/geo"
ok "Wrapper script created: ./geo"

# Done
echo ""
echo "================================"
ok "Installation complete!"
echo ""
echo "🚀 Quick start:"
echo "   cd $INSTALL_DIR"
echo "   ./geo scripts/geo_audit.py --url https://yoursite.com"
echo ""
echo "   (or activate the venv manually: source .venv/bin/activate)"
echo ""
echo "🔄 To update in the future:"
echo "   bash $INSTALL_DIR/update.sh"
echo ""
echo "📖 Full docs: https://github.com/auriti-web-design/geo-optimizer-skill"
echo ""
