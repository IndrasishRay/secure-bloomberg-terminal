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

if ! command -v cargo &>/dev/null; then
    echo -e "${YELLOW}  Installing Rust (rustup)...${NC}"
    curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y
    . "$HOME/.cargo/env"
fi

. "$HOME/.cargo/env"
echo -e "  Rust: ${GREEN}$(rustc --version)${NC}"

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
echo -e "${YELLOW}  Building (release mode)...${NC}"
cd "${INSTALL_DIR}"
cargo build --release 2>&1 | tail -3

ln -sf "${INSTALL_DIR}/target/release/bloomberg-terminal" "${HOME}/.local/bin/bloomberg" 2>/dev/null || true
mkdir -p "${HOME}/.local/bin"
cp "${INSTALL_DIR}/target/release/bloomberg-terminal" "${HOME}/.local/bin/bloomberg"

echo ""
echo -e "${GREEN}═══════════════════════════════════════════"
echo "  Installation complete!"
echo "═══════════════════════════════════════════${NC}"
echo ""
echo "  Run the terminal with:"
echo ""
echo -e "    ${CYAN}bloomberg${NC}"
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
