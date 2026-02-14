# Contributing to Local AI Manager

Thank you for your interest in contributing! This guide will help you add support for new platforms and features.

## Adding a New Platform

To add support for a new operating system (e.g., FreeBSD, OpenBSD):

### 1. Create Platform Implementation

Edit `src/local_ai_manager/platform.py` and add a new class:

```python
class FreeBSDPlatform(PlatformInterface):
    """FreeBSD platform implementation."""
    
    @property
    def name(self) -> str:
        return "freebsd"
    
    def get_default_models_dir(self) -> Path:
        return Path.home() / "models"
    
    def get_default_cache_dir(self) -> Path:
        return Path.home() / ".cache" / "local-ai"
    
    def get_default_log_dir(self) -> Path:
        return Path.home() / ".local" / "log"
    
    def get_default_config_dir(self) -> Path:
        return Path.home() / ".config" / "local-ai"
    
    def get_llama_server_path(self) -> Path:
        paths = [
            Path.home() / "bin" / "llama-server",
            Path("/usr/local/bin/llama-server"),
        ]
        for path in paths:
            if path.exists():
                return path
        return Path("llama-server")
    
    def enable_autostart(self, config, model: str = "auto") -> bool:
        # FreeBSD uses rc.d scripts
        pass
    
    def disable_autostart(self) -> bool:
        pass
    
    def is_autostart_enabled(self) -> bool:
        pass
    
    def get_steam_logs_path(self) -> Path | None:
        # FreeBSD Steam (via Wine/Linuxulator)
        pass
    
    def kill_processes(self, process_names: list[str]) -> None:
        import subprocess
        for name in process_names:
            try:
                subprocess.run(["killall", name], capture_output=True)
            except FileNotFoundError:
                pass
```

### 2. Register Platform

Update the `get_platform()` factory function:

```python
def get_platform() -> PlatformInterface:
    system = platform.system().lower()
    
    if system == "linux":
        return LinuxPlatform()
    elif system == "darwin":
        return MacPlatform()
    elif system == "windows":
        return WindowsPlatform()
    elif system == "freebsd":
        return FreeBSDPlatform()
    else:
        raise RuntimeError(f"Unsupported platform: {system}")
```

### 3. Test Platform Detection

```bash
python3 -c "from local_ai_manager.platform import platform_instance; print(platform_instance().name)"
```

### 4. Add Installer Script

Create `install-freebsd.sh`:

```bash
#!/bin/sh
# FreeBSD-specific installation

pkg install -y python3 py311-pip
# ... rest of installation
```

## Adding a New Package Manager

### Homebrew (macOS/Linux)

Already implemented in `packaging/homebrew/`. Update formula with new releases.

### APT (Debian/Ubuntu)

Create `packaging/debian/`:

```
packaging/debian/
├── control          # Package metadata
├── rules            # Build rules
├── changelog        # Version history
└── local-ai-manager.install  # Files to install
```

### Pacman (Arch Linux)

Create `packaging/arch/PKGBUILD`:

```bash
# Maintainer: Your Name <email@example.com>
pkgname=local-ai-manager
pkgver=2.0.0
pkgrel=1
pkgdesc="Extensible local AI management system"
arch=('any')
url="https://github.com/user/local-ai-manager"
license=('MIT')
depends=('python>=3.10' 'python-pydantic' 'python-typer')
source=("$pkgname-$pkgver.tar.gz::$url/archive/v$pkgver.tar.gz")
sha256sums=('SKIP')

package() {
    cd "$pkgname-$pkgver"
    python setup.py install --root="$pkgdir" --optimize=1
}
```

## Adding New Features

### Example: Adding Discord Notifications

1. Add config option in `models.py`:

```python
class SystemConfig(BaseModel):
    # ... existing fields ...
    discord_webhook: str | None = Field(default=None)
```

2. Create notification module:

```python
# src/local_ai_manager/notifications.py
import httpx
from .config import load_config

def notify_discord(message: str) -> bool:
    config = load_config()
    if not config.discord_webhook:
        return False
    
    httpx.post(config.discord_webhook, json={"content": message})
    return True
```

3. Use in Steam watcher:

```python
from .notifications import notify_discord

# In steam_watcher.py
def _on_game_launch(self, pid: int, proc_name: str) -> None:
    notify_discord(f"🎮 Game started: {proc_name}")
```

## Testing

### Unit Tests

```bash
# Run all tests
pytest

# Run specific test
pytest tests/test_platform.py -v

# Run with coverage
pytest --cov=local_ai_manager --cov-report=html
```

### Platform Testing

Test on clean VMs:

```bash
# Create test environment
docker run -it ubuntu:22.04 bash

# Inside container
apt-get update && apt-get install -y curl python3
./install.sh
local-ai --version
```

## Code Style

```bash
# Format code
black src/

# Lint
ruff check src/

# Type check
mypy src/
```

## Submitting Changes

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/amazing-feature`
3. Make your changes
4. Run tests and linting
5. Commit with clear messages
6. Push to your fork
7. Create a Pull Request

## Release Checklist

Before creating a new release:

- [ ] Version bumped in `__init__.py`
- [ ] CHANGELOG.md updated
- [ ] All tests passing
- [ ] Documentation updated
- [ ] CI/CD pipeline green
- [ ] Tested on all platforms:
  - [ ] Windows 10/11
  - [ ] Ubuntu 22.04
  - [ ] macOS Intel
  - [ ] macOS Apple Silicon
- [ ] Docker image builds successfully
- [ ] Homebrew formula tested

## Questions?

- Open an issue for bugs
- Start a discussion for features
- Join our Discord for real-time chat (link coming soon)

Thank you for contributing! 🚀
