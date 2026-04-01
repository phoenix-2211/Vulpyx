#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════════════════
#  VULPYX – Automated Setup Script for Kali Linux
#  Run once after git clone:   chmod +x setup.sh && ./setup.sh
# ═══════════════════════════════════════════════════════════════════

set -e  # exit on any error

# ── Colours ────────────────────────────────────────────────────────
RED='\033[1;31m'; YEL='\033[1;33m'; GRN='\033[1;32m'
CYN='\033[1;36m'; WHT='\033[1;37m'; DIM='\033[2m';  R='\033[0m'

print_ok()   { echo -e "  ${GRN}[✔]${R}  $1"; }
print_info() { echo -e "  ${CYN}[*]${R}  $1"; }
print_warn() { echo -e "  ${YEL}[!]${R}  $1"; }
print_err()  { echo -e "  ${RED}[✘]${R}  $1"; }
print_sep()  { echo -e "${CYN}$(printf '═%.0s' {1..70})${R}"; }

# ── Banner ─────────────────────────────────────────────────────────
clear
echo ""
echo -e "${RED} __   ___   _ _     _______  __${R}"
echo -e "${RED} \ \ / / | | | |   |  __ \ \/ /${R}"
echo -e "${YEL}  \ V /| | | | |   | |__) \  / ${R}"
echo -e "${YEL}   > < | | | | |   |  ___//  \ ${R}"
echo -e "${CYN}  / . \| |_| | |___| |   / /\ \\${R}"
echo -e "${CYN} /_/ \_\\\\___/|_____|_|  /_/  \_\\\\${R}"
echo ""
echo -e "${CYN}       AI-Powered Penetration Testing Assistant${R}"
echo -e "${DIM}              Setup Script  v2.0${R}"
echo ""
print_sep

# ── Root check ─────────────────────────────────────────────────────
if [[ $EUID -ne 0 ]]; then
    print_warn "Not running as root – some installs may require sudo."
fi

# ── System update ──────────────────────────────────────────────────
print_sep
print_info "Updating package lists..."
sudo apt-get update -qq

# ── Recon tools ────────────────────────────────────────────────────
print_sep
print_info "Installing recon tools..."

TOOLS=( nmap nikto gobuster ffuf sqlmap whatweb wpscan theharvester amass )

for tool in "${TOOLS[@]}"; do
    if command -v "$tool" &>/dev/null; then
        print_ok "$tool already installed"
    else
        print_info "Installing $tool ..."
        sudo apt-get install -y "$tool" -qq && print_ok "$tool installed" \
            || print_warn "$tool could not be installed (skipping)"
    fi
done

# nuclei – go-based, separate install
if ! command -v nuclei &>/dev/null; then
    print_info "Installing nuclei..."
    sudo apt-get install -y nuclei -qq 2>/dev/null || {
        print_warn "nuclei not in apt, trying go install..."
        if command -v go &>/dev/null; then
            go install -v github.com/projectdiscovery/nuclei/v3/cmd/nuclei@latest 2>/dev/null
            print_ok "nuclei installed via go"
        else
            print_warn "nuclei skipped (go not available)"
        fi
    }
else
    print_ok "nuclei already installed"
fi

# subfinder
if ! command -v subfinder &>/dev/null; then
    print_info "Installing subfinder..."
    sudo apt-get install -y subfinder -qq 2>/dev/null \
        || print_warn "subfinder skipped"
else
    print_ok "subfinder already installed"
fi

# ── Python deps ────────────────────────────────────────────────────
print_sep
print_info "Installing Python dependencies..."

# Detect if we're in a venv or system Python
if python3 -c "import sys; sys.exit(0 if hasattr(sys, 'real_prefix') or sys.base_prefix != sys.prefix else 1)" 2>/dev/null; then
    pip3 install -r requirements.txt --quiet
else
    # Kali uses system Python – use --break-system-packages
    pip3 install -r requirements.txt --break-system-packages --quiet 2>&1 | grep -v "already satisfied" \
        || pip3 install -r requirements.txt --quiet
fi
print_ok "Python dependencies installed"

# ── Ollama ─────────────────────────────────────────────────────────
print_sep
print_info "Checking Ollama..."

if ! command -v ollama &>/dev/null; then
    print_info "Ollama not found. Installing..."
    curl -fsSL https://ollama.com/install.sh | sh
    print_ok "Ollama installed"
else
    print_ok "Ollama already installed"
fi

# Start Ollama service in background if not running
if ! pgrep -x "ollama" &>/dev/null; then
    print_info "Starting Ollama service..."
    ollama serve &>/dev/null &
    OLLAMA_PID=$!
    sleep 4  # give it time to start
    print_ok "Ollama service started (PID: $OLLAMA_PID)"
else
    print_ok "Ollama service already running"
fi

# ── Pull AI Model ──────────────────────────────────────────────────
print_sep
print_info "Pulling AI model: qwen2.5-coder:1.5b"
print_info "This is a ~1 GB download. Please wait..."
echo ""

ollama pull qwen2.5-coder:1.5b

print_ok "Model ready: qwen2.5-coder:1.5b"

# ── Permissions ────────────────────────────────────────────────────
print_sep
chmod +x vulpyx.py
print_ok "vulpyx.py marked as executable"

# ── Final message ──────────────────────────────────────────────────
print_sep
echo ""
echo -e "  ${GRN}✔  VULPYX SETUP COMPLETE${R}"
echo ""
echo -e "  ${WHT}To run VULPYX:${R}"
echo -e "  ${CYN}  python3 vulpyx.py${R}"
echo -e "  ${DIM}  (ensure ollama serve is running in another terminal)${R}"
echo ""
print_sep
echo ""

# ── AD tools (optional, for Active Directory targets) ──────────────────────────
print_sep
print_info "Installing optional AD tools..."
sudo apt-get install -y crackmapexec ldap-utils enum4linux -qq 2>/dev/null \
    && print_ok "AD tools installed" || print_warn "Some AD tools skipped"
