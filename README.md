# Local AI Manager

> **⚠️ BETA SOFTWARE ⚠️**
> 
> This is personal tooling that evolved into something shareable. It works for my daily use case but YMMV.
> 
> **Current Status:**
> - **Windows + Git Bash**: I use this daily. It works for me.
> - **Windows + PowerShell**: Should work, tested occasionally  
> - **Linux/macOS**: Code exists, completely untested. Good luck!

A Python-based management system for local LLM inference with automatic model discovery and Steam game integration.

Built because I was tired of PowerShell and wanted something cleaner.

## What This Actually Is

This is tooling I built for myself that:
- Auto-discovers GGUF models from `~/models`
- Manages llama-server lifecycle
- Pauses AI when I launch Steam games (saves VRAM)
- Has a config file instead of a million PowerShell scripts

I use it daily on Windows with Git Bash. It probably has bugs I haven't hit yet.

## Quick Start (What I Actually Test)

```bash
# Windows + Git Bash (this is what I use)
git clone https://github.com/jamesonBradfield/local-ai-manager.git
cd local-ai-manager
./Install-LocalAI-Manager.ps1

# If it works:
local-ai start --background
local-ai status
```

## Requirements

- Python 3.10+
- Windows (this is what I use)
- llama-server.exe somewhere in PATH or ~/bin
- Steam installed via Scoop (for the game detection)

Linux/macOS? The code is there but I've never run it. You're in uncharted territory.

## What Works

Based on my actual daily usage:

✅ **Starting/stopping llama-server** - Works  
✅ **Auto-detecting models** - Works  
✅ **Steam game detection** - Works with Scoop Steam  
✅ **Config file management** - Works  
✅ **Basic CLI** - Works  

🤷 **PowerShell** - Should work, I test it sometimes  
🤷 **Everything else** - Implemented but not tested  

## Installation

### Windows (Git Bash) - What I Use

```bash
git clone https://github.com/jamesonBradfield/local-ai-manager.git
cd local-ai-manager
./Install-LocalAI-Manager.ps1
```

### Windows (PowerShell)

```powershell
git clone https://github.com/jamesonBradfield/local-ai-manager.git
cd local-ai-manager
.\Install-LocalAI-Manager.ps1
```

### Linux/macOS

```bash
# Clone it
git clone https://github.com/jamesonBradfield/local-ai-manager.git
cd local-ai-manager

# Try the installer (I have no idea if this works)
./install.sh

# Let me know what breaks
```

## Usage

### Basic stuff that works

```bash
# List models it found
local-ai list-models

# Start with auto-selected model
local-ai start --background

# Check if it's running
local-ai status

# Stop it
local-ai stop

# Watch Steam and auto-manage AI
local-ai steam start
```

### Auto-start on login (Windows)

```bash
# This should work but admin rights needed
local-ai autostart enable
```

### Custom args

```bash
# Pass extra args to llama-server
local-ai start --extra-args "--repeat-penalty 1.1"
```

## Configuration

Config lives at `~/.config/local-ai/local-ai-config.json`:

```json
{
  "server": {
    "host": "127.0.0.1",
    "port": 8080,
    "models_dir": "~/models",
    "default_model": "nanbeige-3b"
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

## Troubleshooting

### Command not found

```bash
# Check if it's in PATH
which local-ai

# If not, add ~/.local/bin to PATH
export PATH="$PATH:$HOME/.local/bin"
```

### Server won't start

```bash
# Check logs
cat ~/.local/log/llama-server-*.log

# Try running llama-server directly to see the error
llama-server.exe --model ~/models/your-model.gguf
```

### Steam detection not working

Make sure Steam is installed via Scoop and logs to `~/scoop/apps/steam/current/logs/gameprocess_log.txt`

## What's Actually Tested

| Feature | Status | Notes |
|---------|--------|-------|
| Core server management | ✅ Works | Daily use |
| Git Bash integration | ✅ Works | Daily use |
| Model auto-discovery | ✅ Works | Daily use |
| Steam game detection | ✅ Works | With Scoop |
| Config file | ✅ Works | JSON-based |
| PowerShell | ⚠️ Sometimes | Tested occasionally |
| Autostart | ⚠️ Should work | Needs admin rights |
| Linux | ❓ Unknown | Code exists, never ran |
| macOS | ❓ Unknown | Code exists, never ran |

## Contributing

Found a bug? That's expected. Open an issue.

Want to fix Linux/macOS support? That would be awesome. PRs welcome.

Want to add features? Go for it, just don't break my daily workflow.

## Why I Built This

I had a dozen PowerShell scripts that were:
- Hard to maintain
- Scattered everywhere
- Required editing to change models
- Didn't handle Steam games well

Now I have:
- One config file
- A simple CLI
- Auto-detection of models
- Steam integration

It's not perfect but it's better than what I had.

## License

MIT - Do whatever you want. If it breaks, you get to keep both pieces.

## Support

This is a personal project I share because why not. I fix bugs when they annoy me. Use at your own risk.

If you want something production-ready with enterprise support, this isn't it.

---

**TL;DR:** Works for me on Windows with Git Bash. Everything else is bonus territory.
