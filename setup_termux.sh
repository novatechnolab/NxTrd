#!/data/data/com.termux/files/usr/bin/bash
# ╔══════════════════════════════════════════════════════╗
# ║   Nxtrd — Termux Automated Setup Script             ║
# ║   Run once after cloning the repository.             ║
# ╚══════════════════════════════════════════════════════╝

set -e
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
cd "$DIR"

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
RED='\033[0;31m'
NC='\033[0m'

info()    { echo -e "${GREEN}✅ $*${NC}"; }
warn()    { echo -e "${YELLOW}⚠️  $*${NC}"; }
error()   { echo -e "${RED}❌ $*${NC}"; exit 1; }
section() { echo -e "\n${CYAN}━━━ $* ━━━${NC}"; }

# ── 0. Verify Termux environment & Acquire Wake Lock ────────────────────────
if [ ! -d /data/data/com.termux ]; then
    warn "Not running inside Android Termux. You can run './nxtrd' directly on Linux/macOS."
fi

# Acquire wake lock to prevent Android OS from throttling CPU / network during setup
termux-wake-lock 2>/dev/null || true
info "Acquired Termux wake-lock to prevent background throttling."

# Make scripts executable
chmod +x "$DIR/nxtrd" "$DIR/setup_termux.sh" "$DIR/start_termux.sh" 2>/dev/null || true

section "Step 1: Updating Termux packages"
if ! (pkg update -y && pkg upgrade -y); then
    error "Termux package update failed. Ensure you are using Termux from F-Droid (not the deprecated Play Store build)."
fi

section "Step 2: Installing core packages & TUR repository"
# Enable Termux User Repository (TUR) for precompiled ARM64 packages
if ! pkg install -y tur-repo; then
    error "Failed to install tur-repo. Run 'termux-change-repo' to select a working mirror."
fi

pkg update -y

# Install Python, precompiled C-extensions (numpy, pandas, cryptography), git, and tmux
if ! pkg install -y python python-pip python-numpy python-pandas python-cryptography termux-api tmux git; then
    error "Failed to install core system packages."
fi
info "Core packages installed."

section "Step 3: Creating Python virtual environment"
if [ ! -d "$DIR/.venv" ]; then
    # Use --system-site-packages so venv inherits precompiled ARM64 numpy/pandas from Termux
    python3 -m venv --system-site-packages "$DIR/.venv"
    info "Created .venv with system site-packages."
else
    info ".venv already exists — skipping creation."
fi

source "$DIR/.venv/bin/activate"

section "Step 4: Upgrading pip and wheel"
pip install --upgrade pip wheel setuptools

section "Step 5: Installing Python dependencies"
pip install "uvicorn[standard]>=0.30.0" "websockets>=12.0"
pip install -r "$DIR/backend/requirements.txt"
info "Python dependencies installed."

section "Step 6: Initializing SQLite database schema"
python3 -c "import sys; sys.path.insert(0, '$DIR/backend'); from core.db import init_db; init_db()"
info "Database schema initialized with all dependent tables and indexes."

section "Step 7: Configuring global 'nxtrd' command"
# Create a symlink in Termux's $PREFIX/bin so typing 'nxtrd' anywhere works
PREFIX_BIN="/data/data/com.termux/files/usr/bin"
if [ -d "$PREFIX_BIN" ]; then
    ln -sf "$DIR/nxtrd" "$PREFIX_BIN/nxtrd"
    info "Linked global command: 'nxtrd' -> $PREFIX_BIN/nxtrd"
fi

# Ensure .env exists
if [ ! -f "$DIR/.env" ] && [ -f "$DIR/.env.example" ]; then
    cp "$DIR/.env.example" "$DIR/.env"
    info "Created default .env from .env.example"
fi

section "Setup Complete!"
echo -e "${GREEN}You can now start the server anytime simply by running:${NC}"
echo -e "  \033[1;33mnxtrd\033[0m   (from any folder)"
echo -e "  or"
echo -e "  \033[1;33m./nxtrd\033[0m (from inside this repo)"
echo ""
