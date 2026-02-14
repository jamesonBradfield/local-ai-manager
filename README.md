# Local AI Manager

> **⚠️ CROSS-PLATFORM BETA NOTICE** ⚠️
> 
> This project is currently in **BETA** for cross-platform support.
> - **Windows**: ✅ Production ready - Fully tested and actively used
> - **Linux**: 🧪 Experimental - Code implemented but not tested
> - **macOS**: 🧪 Experimental - Code implemented but not tested
> 
> **The Windows version is battle-tested and used daily.** Linux and macOS implementations are functional but need community testing. If you use Linux or macOS, please report issues!

A cross-platform Python-based management system for local LLM inference with automatic model discovery, prompt caching, and Steam game integration.

Built to replace PowerShell scripts with a clean, extensible Python architecture.

## ⚡ Quick Start (Windows - Recommended)

```powershell
# Clone and install
git clone https://github.com/jamesonBradfield/local-ai-manager.git
cd local-ai-manager
.\Install-LocalAI-Manager.ps1

# Start using it immediately
local-ai start --background
local-ai status
```

## ✨ Features

- **Windows Native** - Fully tested on Windows 10/11 with Git Bash and PowerShell
- **Cross-Platform Foundation** - Linux and macOS support implemented (needs testing)
- **Automatic GGUF Discovery** - Automatically finds and configures models from `~/models`
- **JSON Configuration** - Define models, settings, and behaviors in a single config file
- **Prompt Caching** - Reduces Time To First Token (TTFT) by caching prompt state
- **Steam Integration** - Automatically stops AI when gaming (saves VRAM) and restores after
- **Smart Model Selection** - Priority-based auto-selection with nanbeige as primary
- **Rich CLI** - Beautiful terminal output with tables and panels
- **Auto-Start on Login** - Automatically start AI server when Windows boots
- **Custom llama.cpp Arguments** - Pass additional flags for advanced customization

## 📋 Requirements

**Windows (Tested & Supported):**
- Python 3.10+
- Windows 10/11
- llama-server.exe in PATH or `~/bin`

**Linux/macOS (Experimental - See warning above):**
- Python 3.10+
- Ubuntu 20.04+ / Fedora 35+ / macOS 12+
- llama-server binary in PATH or `~/bin`

## 🚀 Installation

### Windows (Git Bash) - RECOMMENDED

```bash
# Clone the repository
git clone https://github.com/jamesonBradfield/local-ai-manager.git
cd local-ai-manager

# Run installer
./Install-LocalAI-Manager.ps1

# Start using immediately
local-ai --help
```

### Windows (PowerShell)

```powershell
# Clone the repository
git clone https://github.com/jamesonBradfield/local-ai-manager.git
cd local-ai-manager

# Run installer
.\Install-LocalAI-Manager.ps1

# Start using (bat wrappers work immediately)
local-ai-start --background
```

### Linux / macOS (Experimental)

```bash
# Clone the repository
git clone https://github.com/jamesonBradfield/local-ai-manager.git
cd local-ai-manager

# Run installer (untested - please report issues!)
./install.sh

# Test basic functionality
local-ai --help
```

## 💻 Usage

### Basic Commands

```bash
# List available models
local-ai list-models --verbose

# Start server with auto-selected model
local-ai start --background

# Check status
local-ai status

# Stop server
local-ai stop

# Start Steam watcher (auto-manage AI when gaming)
local-ai steam start
```

### Enable Auto-Start on Login (Windows)

```bash
# Start now and enable auto-start
local-ai start --background --autostart

# Or manage separately
local-ai autostart enable --model nanbeige-3b
local-ai autostart status
```

### Custom llama.cpp Arguments

```bash
# Pass any llama-server argument
local-ai start --extra-args "--repeat-penalty 1.1 --seed 42"
```

## ⚙️ Configuration

Configuration is stored at:
- **Windows:** `%USERPROFILE%\.config\local-ai\local-ai-config.json`
- **Linux:** `~/.config/local-ai/local-ai-config.json`
- **macOS:** `~/Library/Application Support/local-ai/local-ai-config.json`

### Example Configuration

```json
{
  "version": "2.0.0",
  "server": {
    "host": "127.0.0.1",
    "port": 8080,
    "models_dir": "~/models",
    "default_model": "nanbeige-3b"
  },
  "steam": {
    "enabled": true,
    "stop_ai_on_game": true,
    "restart_ai_after_game": true
  },
  "models": [
    {
      "id": "nanbeige-3b",
      "name": "Nanbeige 3B",
      "filename_pattern": "(?i)Nanbeige.*3B.*Q4_K_M.*\\.gguf$",
      "ctx_size": 131072,
      "priority": 1
    }
  ]
}
```

## 🐛 Troubleshooting

### 'local-ai' Command Not Found

**Git Bash:**
```bash
# Shell scripts should work immediately
which local-ai

# If not in PATH, add manually
export PATH="$PATH:$HOME/.local/bin"
```

**PowerShell:**
```powershell
# Use bat wrappers (work immediately)
local-ai-start --help

# Or restart terminal for PATH to update
```

### Server Won't Start

```bash
# Check logs
cat ~/.local/log/llama-server-*.log

# Verify model exists
local-ai list-models --verbose

# Test without background
local-ai start
```

### Steam Watcher Not Detecting Games

**Windows (Scoop):**
```bash
# Verify Steam log path exists
ls ~/scoop/apps/steam/current/logs/gameprocess_log.txt

# Check logs are being written
tail -f ~/scoop/apps/steam/current/logs/gameprocess_log.txt
```

## 🏗️ Architecture

```
local-ai-manager/
├── src/local_ai_manager/
│   ├── __init__.py              # Package initialization
│   ├── models.py                # Pydantic configuration models
│   ├── defaults.py              # Default model configurations
│   ├── config.py                # Config file I/O
│   ├── registry.py              # GGUF discovery & ModelRegistry
│   ├── server.py                # LlamaServerManager
│   ├── steam_watcher.py         # SteamLogHandler & SteamWatcher
│   ├── platform.py              # Cross-platform abstraction layer
│   └── cli.py                   # Typer CLI with Rich output
├── install.sh                   # Linux/macOS installer (experimental)
├── Install-LocalAI-Manager.ps1  # Windows installer (tested)
├── Dockerfile                   # Docker support
├── docker-compose.yml           # Docker Compose
└── README.md                    # This file
```

## 🚧 Platform Support Status

| Platform | Status | Notes |
|----------|--------|-------|
| **Windows 10/11** | ✅ Production | Fully tested, actively used daily |
| **Linux (systemd)** | 🧪 Experimental | Code ready, needs community testing |
| **macOS (launchd)** | 🧪 Experimental | Code ready, needs community testing |

### Why the Experimental Status?

The Windows implementation has been running daily for months. The Linux/macOS implementations:
- Share the same Python codebase
- Have platform-specific abstractions implemented
- Use systemd/launchd for autostart
- **Need real-world testing and bug reports**

If you use Linux or macOS, please test and [open an issue](https://github.com/jamesonBradfield/local-ai-manager/issues) with your findings!

## 🤝 Contributing

We need help testing Linux and macOS! If you'd like to contribute:

1. **Test on Linux/macOS** - Try the install script and report issues
2. **Fix platform bugs** - Help debug platform-specific issues
3. **Add package managers** - Create packages for apt/dnf/pacman/Homebrew
4. **Documentation** - Help improve cross-platform docs

See [CONTRIBUTING.md](CONTRIBUTING.md) for details.

## 📦 Package Managers (Future)

Planned distribution methods:
- **Windows:** Scoop, Chocolatey
- **macOS:** Homebrew
- **Linux:** apt, dnf, pacman, AUR

## 📝 License

MIT License - See [LICENSE](LICENSE) file

## 🙏 Acknowledgments

- Built for personal use and shared with the community
- Uses [llama.cpp](https://github.com/ggerganov/llama.cpp) for inference
- Inspired by the need to escape PowerShell hell

## 💬 Support

- **Issues:** [GitHub Issues](https://github.com/jamesonBradfield/local-ai-manager/issues)
- **Discussions:** [GitHub Discussions](https://github.com/jamesonBradfield/local-ai-manager/discussions)

---

**Note:** This is a personal project that evolved into something shareable. Windows users can use it confidently. Linux/macOS users, please help us make it rock-solid on your platform!
