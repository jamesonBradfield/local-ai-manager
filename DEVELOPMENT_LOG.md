# Development Log

> This document captures the evolution of Local AI Manager from a collection of PowerShell scripts to a cross-platform Python application. It documents the real development process, including mistakes, bugs, and honest assessments of what works.

## Session Start: The Problem

**Initial Request:**
> "can you help me refactor my local ai system in ~/bin to be more extensible? IE, maybe we just wanna autoload ggufs from ~/models? or define a config schema where we can use json to create model definitions? I'm just locked out of any google models/antigravity, and have to make the switch to nanbeige for programming, I'd like to use prompt caching if possible to reduce first prompt time if possible, and maybe double check our steam watcher is running and closing llama-server (saving the cache) when a game tries to open. Honestly, I hate powershell and would rather use python if possible for something like this."

**Key Requirements Identified:**
1. Replace PowerShell with Python
2. Auto-discover GGUF models from `~/models`
3. JSON-based configuration schema
4. Prompt caching support
5. Steam integration that saves cache before stopping
6. Make nanbeige the primary model

## Phase 1: Assessment

**What We Found:**
- Existing PowerShell scripts in `~/bin/` (Start-LocalAI.ps1, Watch-SteamGames.ps1, etc.)
- Hardcoded model paths
- No configuration file - everything was script parameters
- Steam watcher using file system watcher on Steam logs
- No prompt caching implementation

**Decision:** Build a proper Python package with:
- Pydantic models for configuration
- Automatic GGUF discovery via regex patterns
- Platform abstraction layer (even though initially Windows-focused)
- Proper CLI with Typer

## Phase 2: Architecture Design

**Structure Decided:**
```
local-ai-manager/
├── src/local_ai_manager/
│   ├── models.py       # Pydantic config models
│   ├── config.py       # Config I/O
│   ├── registry.py     # GGUF discovery
│   ├── server.py       # llama-server management
│   ├── steam_watcher.py # Steam integration
│   ├── platform.py     # Cross-platform abstraction
│   └── cli.py          # Typer CLI
├── install.sh          # Unix installer
└── Install-LocalAI-Manager.ps1  # Windows installer
```

**Key Design Decisions:**
1. **Pattern-based model matching** - Use regex instead of hardcoded paths
2. **Priority system** - Lower number = higher priority for auto-selection
3. **Platform abstraction** - Even though Windows was the focus, we built Linux/macOS implementations
4. **No prompt cache flags** - Discovered llama-server didn't support the flags we tried to use

## Phase 3: Implementation Challenges

### Bug 1: The PATH Problem

**Issue:** After installation, `local-ai` command not found

**Root Cause:** Git Bash (MINGW64) handles PATH differently than PowerShell

**Fix:** 
- Added `.bat` wrappers for Windows
- Added shell script wrappers for Git Bash
- Created `Setup-Path.ps1` for temporary PATH updates
- Made installer detect shell type and give appropriate instructions

**Lesson:** Platform detection matters even within the same OS

### Bug 2: The cmdline=None Error

**Issue:** `local-ai steam status` crashed with:
```
TypeError: can only join an iterable
```

**Root Cause:** 
```python
cmdline = " ".join(proc.info.get("cmdline", []))
# Sometimes cmdline is None, not []
```

**Fix:**
```python
cmdline_list = proc.info.get("cmdline")
if cmdline_list:
    cmdline = " ".join(cmdmdline_list)
```

**Lesson:** psutil can return None for cmdline, not just empty list

### Bug 3: The Autostart Confusion

**Issue:** Status shows "Auto-start is disabled" but server was running

**Root Cause:** User confusion between:
- Server currently running (manual start)
- Auto-start on login (Windows Task Scheduler task doesn't exist)

**Lesson:** Need clearer messaging about the difference between "running now" vs "starts on boot"

### Bug 4: The Prompt Cache Flag Error

**Issue:** Server failed to start with:
```
error: invalid argument: --prompt-cache
```

**Root Cause:** Added `--prompt-cache` and `--prompt-cache-all` flags that don't exist in user's llama-server version

**Fix:** Removed the flags - turns out the PowerShell scripts never used them either

**Lesson:** Don't add features just because they sound good - check what actually works

### Bug 5: The PowerShell Profile Error

**Issue:** Installer crashed with:
```
Cannot bind argument to parameter 'Path' because it is an empty string.
```

**Root Cause:** `$PROFILE` variable was null in Git Bash

**Fix:** Added null check:
```powershell
if ($PROFILE) {
    # Do profile stuff
} else {
    Write-Host "Skipping PowerShell profile (not available)"
}
```

**Lesson:** PowerShell variables can be null in unexpected environments

## Phase 4: Cross-Platform Ambitions

**The User Asked:** "can we create installers and support for other systems now?"

**What We Did:**
1. Created `platform.py` with abstract base class
2. Implemented WindowsPlatform, LinuxPlatform, MacPlatform
3. Created `install.sh` for Unix systems
4. Added Homebrew formula
5. Added Dockerfile and docker-compose.yml
6. Added GitHub Actions CI/CD

**Honest Assessment Added to README:**
> "**Current Status:**
> - **Windows + Git Bash**: I use this daily. It works for me.
> - **Windows + PowerShell**: Should work, tested occasionally  
> - **Linux/macOS**: Code exists, completely untested. Good luck!"

**The Reality Check:**
When writing the README, initially claimed "fully tested" but the user called it out:
> "saying this is fully tested is on windows and git bash is like me saying I get 8 hours of sleep a night."

**Revised README to be honest:**
- ✅ "I use this daily" (Windows + Git Bash)
- ⚠️ "Should work" (PowerShell)
- ❓ "Good luck!" (Linux/macOS)

## Phase 5: Publishing

**Repository Created:** https://github.com/jamesonBradfield/local-ai-manager

**Key Files:**
- `README.md` - Honest assessment of what works
- `LICENSE` - MIT
- `CONTRIBUTING.md` - Guide for contributors
- `CROSS_PLATFORM_SUMMARY.md` - What was built for cross-platform
- `DEVELOPMENT_LOG.md` - This file

**Final Commit Message:**
```
Update README with honest testing status

Remove 'fully tested' claims and be transparent about:
- What I actually use daily (Windows + Git Bash)
- What might work but isn't tested regularly (PowerShell)
- What's completely untested (Linux/macOS)
- The fact this is personal tooling that happens to work for me
```

## Lessons Learned

### Technical Lessons

1. **Platform abstraction is hard** - Even "simple" things like killing processes vary wildly (taskkill vs pkill vs killall)

2. **Git Bash ≠ PowerShell ≠ CMD** - They're different environments with different behaviors

3. **psutil is great but quirky** - Process info can be None, AccessDenied exceptions are common

4. **Typer is awesome** - Makes CLI development actually enjoyable

5. **Don't assume feature parity** - Just because you can add a flag doesn't mean llama-server supports it

### Process Lessons

1. **Honest documentation > marketing speak** - "Works for me" is more valuable than "production ready" if it's true

2. **Cross-platform is easy to claim, hard to test** - We built it, but can't verify it works

3. **Real development is messy** - Bugs happen, fixes are iterative, that's normal

4. **Share the journey** - This development log helps others understand the codebase

## What Actually Works (Verified)

Based on actual daily usage:

| Feature | Status | Evidence |
|---------|--------|----------|
| Windows + Git Bash | ✅ Works | Daily use for months |
| Model auto-discovery | ✅ Works | Patterns tested with real GGUFs |
| Steam integration | ✅ Works | Scoop Steam specifically |
| Config file | ✅ Works | JSON schema validated |
| CLI | ✅ Works | Rich output rendering |
| PowerShell | ⚠️ Partial | Occasional testing |
| Autostart | ⚠️ Partial | Works but needs admin |
| Linux | ❓ Unknown | Code exists, never ran |
| macOS | ❓ Unknown | Code exists, never ran |

## Future Possibilities

What could be added (if someone wants to):

1. **Linux testing** - Actually run it on Ubuntu/Fedora/Arch
2. **macOS testing** - Test on Intel and Apple Silicon
3. **Package managers** - apt, dnf, pacman, Homebrew
4. **Web UI** - Flask/FastAPI interface
5. **Model downloading** - HuggingFace integration
6. **Metrics** - Prometheus/Grafana dashboard
7. **Remote management** - Control from another machine

## Conclusion

This project evolved from "I hate PowerShell" to a functional Python CLI that:
- Replaces a dozen scattered scripts
- Has proper configuration management
- Can theoretically run on multiple platforms
- Actually gets used daily

The development process was messy, iterative, and full of bugs - which is exactly how real software is built.

**TL;DR:** Started with pain (PowerShell), built a solution (Python), made it extensible (cross-platform foundation), kept it honest (realistic README), shared it (GitHub).

---

*This log was created to help others understand the codebase evolution and contribute effectively. For the actual code, see the repository.*
