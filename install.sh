#!/usr/bin/env bash
# install.sh - Universal installer for Local AI Manager
# Supports: Linux, macOS, Windows (Git Bash/WSL)

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
REPO_URL="https://github.com/user/local-ai-manager"
INSTALL_DIR="${INSTALL_DIR:-$HOME/.local/share/local-ai-manager}"
BIN_DIR="${BIN_DIR:-$HOME/.local/bin}"

# Detect OS
detect_os() {
    case "$(uname -s)" in
        Linux*)     OS=Linux;;
        Darwin*)    OS=Mac;;
        CYGWIN*|MINGW*|MSYS*) OS=Windows;;
        *)          OS="UNKNOWN"; echo "${RED}Unknown OS: $(uname -s)${NC}"; exit 1;;
    esac
    echo "${BLUE}Detected OS: $OS${NC}"
}

# Detect package manager (Linux only)
detect_pkg_manager() {
    if command -v apt-get &> /dev/null; then
        PKG_MANAGER="apt"
    elif command -v dnf &> /dev/null; then
        PKG_MANAGER="dnf"
    elif command -v pacman &> /dev/null; then
        PKG_MANAGER="pacman"
    elif command -v zypper &> /dev/null; then
        PKG_MANAGER="zypper"
    else
        PKG_MANAGER="unknown"
    fi
}

# Check dependencies
check_deps() {
    echo "${YELLOW}Checking dependencies...${NC}"
    
    # Python 3.10+
    if ! command -v python3 &> /dev/null; then
        echo "${RED}Python 3 not found. Installing...${NC}"
        install_python
    fi
    
    PYTHON_VERSION=$(python3 --version 2>&1 | grep -oP '\d+\.\d+' | head -1)
    MAJOR=$(echo $PYTHON_VERSION | cut -d. -f1)
    MINOR=$(echo $PYTHON_VERSION | cut -d. -f2)
    
    if [ "$MAJOR" -lt 3 ] || ([ "$MAJOR" -eq 3 ] && [ "$MINOR" -lt 10 ]); then
        echo "${RED}Python 3.10+ required, found $PYTHON_VERSION${NC}"
        install_python
    fi
    
    echo "${GREEN}✓ Python $PYTHON_VERSION found${NC}"
}

# Install Python based on OS
install_python() {
    case $OS in
        Linux)
            detect_pkg_manager
            case $PKG_MANAGER in
                apt)
                    sudo apt-get update
                    sudo apt-get install -y python3 python3-pip python3-venv
                    ;;
                dnf)
                    sudo dnf install -y python3 python3-pip
                    ;;
                pacman)
                    sudo pacman -S --noconfirm python python-pip
                    ;;
                *)
                    echo "${RED}Please install Python 3.10+ manually${NC}"
                    exit 1
                    ;;
            esac
            ;;
        Mac)
            if command -v brew &> /dev/null; then
                brew install python@3.12
            else
                echo "${RED}Please install Homebrew first: https://brew.sh${NC}"
                exit 1
            fi
            ;;
        Windows)
            echo "${RED}Please install Python 3.10+ from python.org${NC}"
            exit 1
            ;;
    esac
}

# Download latest release
download_release() {
    echo "${YELLOW}Downloading Local AI Manager...${NC}"
    
    # Create directories
    mkdir -p "$INSTALL_DIR"
    mkdir -p "$BIN_DIR"
    
    # For now, assume local copy exists (development mode)
    # In production, this would download from GitHub releases
    if [ -d "$(dirname "$0")/.git" ] || [ -f "$(dirname "$0")/pyproject.toml" ]; then
        echo "${BLUE}Using local development copy${NC}"
        SCRIPT_DIR="$(dirname "$0")"
        cp -r "$SCRIPT_DIR"/* "$INSTALL_DIR/"
    else
        echo "${YELLOW}Downloading from $REPO_URL...${NC}"
        # Download logic would go here
        curl -L "$REPO_URL/releases/latest/download/local-ai-manager.tar.gz" | tar -xz -C "$INSTALL_DIR"
    fi
    
    echo "${GREEN}✓ Downloaded to $INSTALL_DIR${NC}"
}

# Create virtual environment
setup_venv() {
    echo "${YELLOW}Setting up Python environment...${NC}"
    
    VENV_DIR="$INSTALL_DIR/.venv"
    
    if [ ! -d "$VENV_DIR" ]; then
        python3 -m venv "$VENV_DIR"
    fi
    
    # Install package
    "$VENV_DIR/bin/pip" install --upgrade pip
    "$VENV_DIR/bin/pip" install -e "$INSTALL_DIR"
    
    echo "${GREEN}✓ Virtual environment ready${NC}"
}

# Create shell wrappers
create_wrappers() {
    echo "${YELLOW}Creating command wrappers...${NC}"
    
    VENV_DIR="$INSTALL_DIR/.venv"
    
    # Main wrapper
    cat > "$BIN_DIR/local-ai" << 'EOF'
#!/bin/bash
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
INSTALL_DIR="${INSTALL_DIR:-$HOME/.local/share/local-ai-manager}"
VENV_DIR="$INSTALL_DIR/.venv"
"$VENV_DIR/bin/python" -m local_ai_manager "$@"
EOF
    chmod +x "$BIN_DIR/local-ai"
    
    # Convenience wrappers
    for cmd in start stop status; do
        cat > "$BIN_DIR/local-ai-$cmd" << EOF
#!/bin/bash
INSTALL_DIR="${INSTALL_DIR:-\$HOME/.local/share/local-ai-manager}"
VENV_DIR="\$INSTALL_DIR/.venv"
"\$VENV_DIR/bin/python" -m local_ai_manager $cmd "\$@"
EOF
        chmod +x "$BIN_DIR/local-ai-$cmd"
    done
    
    echo "${GREEN}✓ Wrappers created in $BIN_DIR${NC}"
}

# Setup shell completion
setup_completion() {
    echo "${YELLOW}Setting up shell completion...${NC}"
    
    SHELL_NAME=$(basename "$SHELL")
    
    case $SHELL_NAME in
        bash)
            COMPLETION_DIR="$HOME/.bash_completion.d"
            mkdir -p "$COMPLETION_DIR"
            # Generate completion script
            _LOCAL_AI_COMPLETE=bash_source local-ai > "$COMPLETION_DIR/local-ai" 2>/dev/null || true
            ;;
        zsh)
            COMPLETION_DIR="${ZSH_CUSTOM:-$HOME/.oh-my-zsh/custom}/completions"
            mkdir -p "$COMPLETION_DIR"
            _LOCAL_AI_COMPLETE=zsh_source local-ai > "$COMPLETION_DIR/_local-ai" 2>/dev/null || true
            ;;
        fish)
            COMPLETION_DIR="$HOME/.config/fish/completions"
            mkdir -p "$COMPLETION_DIR"
            _LOCAL_AI_COMPLETE=fish_source local-ai > "$COMPLETION_DIR/local-ai.fish" 2>/dev/null || true
            ;;
    esac
}

# Setup autostart for Linux (systemd)
setup_linux_autostart() {
    if [ "$OS" != "Linux" ]; then
        return
    fi
    
    echo "${YELLOW}Setting up systemd service...${NC}"
    
    mkdir -p "$HOME/.config/systemd/user"
    
    cat > "$HOME/.config/systemd/user/local-ai.service" << EOF
[Unit]
Description=Local AI Manager
After=network.target

[Service]
Type=simple
ExecStart=$INSTALL_DIR/.venv/bin/local-ai start --background
ExecStop=$INSTALL_DIR/.venv/bin/local-ai stop
Restart=on-failure

[Install]
WantedBy=default.target
EOF
    
    systemctl --user daemon-reload
    echo "${GREEN}✓ systemd service created${NC}"
    echo "${BLUE}Enable with: systemctl --user enable local-ai.service${NC}"
}

# Setup autostart for macOS (launchd)
setup_macos_autostart() {
    if [ "$OS" != "Mac" ]; then
        return
    fi
    
    echo "${YELLOW}Setting up launchd service...${NC}"
    
    LAUNCHD_DIR="$HOME/Library/LaunchAgents"
    mkdir -p "$LAUNCHD_DIR"
    
    cat > "$LAUNCHD_DIR/com.localai.manager.plist" << EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.localai.manager</string>
    <key>ProgramArguments</key>
    <array>
        <string>$INSTALL_DIR/.venv/bin/local-ai</string>
        <string>start</string>
        <string>--background</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>StandardOutPath</key>
    <string>$HOME/.local/log/local-ai.log</string>
    <key>StandardErrorPath</key>
    <string>$HOME/.local/log/local-ai.error.log</string>
</dict>
</plist>
EOF
    
    echo "${GREEN}✓ launchd plist created${NC}"
    echo "${BLUE}Enable with: launchctl load ~/Library/LaunchAgents/com.localai.manager.plist${NC}"
}

# Print final instructions
print_instructions() {
    echo ""
    echo "${GREEN}========================================${NC}"
    echo "${GREEN}  Installation Complete!${NC}"
    echo "${GREEN}========================================${NC}"
    echo ""
    echo "${YELLOW}Quick start:${NC}"
    echo "  local-ai --help              Show all commands"
    echo "  local-ai start --background  Start the server"
    echo "  local-ai status              Check server status"
    echo ""
    echo "${YELLOW}Configuration:${NC}"
    echo "  ~/.config/local-ai/local-ai-config.json"
    echo ""
    
    if [ "$OS" = "Linux" ]; then
        echo "${YELLOW}Autostart:${NC}"
        echo "  systemctl --user enable local-ai.service"
        echo "  systemctl --user start local-ai.service"
        echo ""
    elif [ "$OS" = "Mac" ]; then
        echo "${YELLOW}Autostart:${NC}"
        echo "  launchctl load ~/Library/LaunchAgents/com.localai.manager.plist"
        echo ""
    fi
    
    # Check if BIN_DIR is in PATH
    if [[ ":$PATH:" != *":$BIN_DIR:"* ]]; then
        echo "${YELLOW}IMPORTANT:${NC} Add to your shell profile:"
        echo "  export PATH=\"\$PATH:$BIN_DIR\""
        echo ""
    fi
}

# Main installation
main() {
    echo "${GREEN}Local AI Manager Installer${NC}"
    echo "${GREEN}==========================${NC}"
    echo ""
    
    detect_os
    check_deps
    download_release
    setup_venv
    create_wrappers
    setup_completion
    setup_linux_autostart
    setup_macos_autostart
    print_instructions
}

# Run main function
main "$@"
