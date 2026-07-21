#!/usr/bin/env bash
set -euo pipefail

REPO_URL="https://github.com/IndrasishRay/secure-bloomberg-terminal-clone.git"
INSTALL_DIR="${HOME}/.bloomberg-terminal"

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

echo -e "${CYAN}"
echo "═══════════════════════════════════════════"
echo "  Secure Bloomberg Terminal — Installer"
echo "═══════════════════════════════════════════"
echo -e "${NC}"

if ! command -v python3 &>/dev/null; then
    echo "Error: python3 is required but not installed."
    echo "Install it from https://www.python.org/downloads/"
    exit 1
fi

PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
echo -e "  Python: ${GREEN}${PYTHON_VERSION}${NC}"

echo ""
echo "  Installing to: ${INSTALL_DIR}"

if [ -d "${INSTALL_DIR}" ]; then
    echo "  Updating existing installation..."
    cd "${INSTALL_DIR}" && git pull --ff-only 2>/dev/null || true
else
    echo "  Cloning repository..."
    if ! command -v git &>/dev/null; then
        echo "Error: git is required but not installed."
        exit 1
    fi
    git clone --depth=1 "${REPO_URL}" "${INSTALL_DIR}"
fi

echo ""
echo -e "${YELLOW}  Setting up virtual environment...${NC}"
cd "${INSTALL_DIR}"
python3 -m venv .venv
source .venv/bin/activate

echo -e "${YELLOW}  Installing dependencies...${NC}"
pip install -q -r requirements.txt

if [ ! -f .env ]; then
    cp .env.example .env
    echo -e "  ${GREEN}Created .env with defaults${NC}"
fi

cat > "${INSTALL_DIR}/bloomberg" << 'SCRIPT'
#!/usr/bin/env bash
cd "$(dirname "$0")"
source .venv/bin/activate 2>/dev/null || true
export DEV_MODE=1
exec python3 src/main.py "$@"
SCRIPT
chmod +x "${INSTALL_DIR}/bloomberg"

mkdir -p "${HOME}/.local/bin"
ln -sf "${INSTALL_DIR}/bloomberg" "${HOME}/.local/bin/bloomberg"

echo ""
echo -e "${GREEN}═══════════════════════════════════════════"
echo "  Installation complete!"
echo "═══════════════════════════════════════════${NC}"
echo ""
echo "  Run the terminal with:"
echo ""
echo -e "    ${CYAN}bloomberg${NC}"
echo ""
echo "  Or from the install directory:"
echo -e "    ${CYAN}${INSTALL_DIR}/bloomberg${NC}"
echo ""
echo "  ⚠  PROTOTYPE NOTICE: This is a demo/prototype."
echo "     No real bank details, no real trading."
echo "     All data stays local on your machine."
echo ""

if echo ":$PATH:" | grep -qv ":$HOME/.local/bin:"; then
    echo "  Add to your shell profile to use 'bloomberg' from anywhere:"
    echo "    export PATH=\"\$HOME/.local/bin:\$PATH\""
    echo ""
fi