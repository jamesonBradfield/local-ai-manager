"""Platform abstraction layer for Local AI Manager."""

from __future__ import annotations

import platform
import sys
from abc import ABC, abstractmethod
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .models import ServerConfig, SystemConfig


class PlatformInterface(ABC):
    """Abstract base class for platform-specific implementations."""
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Platform name (linux, darwin, windows)."""
        pass
    
    @abstractmethod
    def get_default_models_dir(self) -> Path:
        """Get default directory for models."""
        pass
    
    @abstractmethod
    def get_default_cache_dir(self) -> Path:
        """Get default directory for cache."""
        pass
    
    @abstractmethod
    def get_default_log_dir(self) -> Path:
        """Get default directory for logs."""
        pass
    
    @abstractmethod
    def get_default_config_dir(self) -> Path:
        """Get default directory for configuration."""
        pass
    
    @abstractmethod
    def get_llama_server_path(self) -> Path:
        """Get path to llama-server executable."""
        pass
    
    @abstractmethod
    def enable_autostart(self, config: ServerConfig, model: str = "auto") -> bool:
        """Enable auto-start on login."""
        pass
    
    @abstractmethod
    def disable_autostart(self) -> bool:
        """Disable auto-start on login."""
        pass
    
    @abstractmethod
    def is_autostart_enabled(self) -> bool:
        """Check if auto-start is enabled."""
        pass
    
    @abstractmethod
    def get_steam_logs_path(self) -> Path | None:
        """Get path to Steam logs directory."""
        pass
    
    @abstractmethod
    def kill_processes(self, process_names: list[str]) -> None:
        """Kill processes by name."""
        pass


class LinuxPlatform(PlatformInterface):
    """Linux platform implementation."""
    
    @property
    def name(self) -> str:
        return "linux"
    
    def get_default_models_dir(self) -> Path:
        return Path.home() / "models"
    
    def get_default_cache_dir(self) -> Path:
        return Path.home() / ".cache" / "local-ai"
    
    def get_default_log_dir(self) -> Path:
        return Path.home() / ".local" / "log"
    
    def get_default_config_dir(self) -> Path:
        return Path.home() / ".config" / "local-ai"
    
    def get_llama_server_path(self) -> Path:
        # Try common locations
        paths = [
            Path.home() / "bin" / "llama-server",
            Path("/usr/local/bin/llama-server"),
            Path("/usr/bin/llama-server"),
        ]
        for path in paths:
            if path.exists():
                return path
        return Path("llama-server")  # Fallback to PATH
    
    def enable_autostart(self, config, model: str = "auto") -> bool:
        """Enable systemd user service."""
        import subprocess
        
        service_dir = Path.home() / ".config" / "systemd" / "user"
        service_dir.mkdir(parents=True, exist_ok=True)
        
        service_content = f"""[Unit]
Description=Local AI Manager
After=network.target

[Service]
Type=simple
ExecStart={config.llama_server_path} --model auto --background
ExecStop=pkill -f llama-server
Restart=on-failure

[Install]
WantedBy=default.target
"""
        
        service_file = service_dir / "local-ai.service"
        service_file.write_text(service_content)
        
        try:
            subprocess.run(["systemctl", "--user", "daemon-reload"], check=True)
            subprocess.run(["systemctl", "--user", "enable", "local-ai.service"], check=True)
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            return False
    
    def disable_autostart(self) -> bool:
        """Disable systemd user service."""
        import subprocess
        
        try:
            subprocess.run(["systemctl", "--user", "disable", "local-ai.service"], check=True)
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            return False
    
    def is_autostart_enabled(self) -> bool:
        """Check if systemd service is enabled."""
        import subprocess
        
        try:
            result = subprocess.run(
                ["systemctl", "--user", "is-enabled", "local-ai.service"],
                capture_output=True,
                text=True
            )
            return result.returncode == 0 and "enabled" in result.stdout
        except FileNotFoundError:
            return False
    
    def get_steam_logs_path(self) -> Path | None:
        """Get Steam logs path on Linux."""
        # Steam on Linux is usually in ~/.local/share/Steam
        steam_dir = Path.home() / ".local" / "share" / "Steam"
        logs_dir = steam_dir / "logs"
        if logs_dir.exists():
            return logs_dir
        
        # Flatpak Steam
        flatpak_dir = Path.home() / ".var" / "app" / "com.valvesoftware.Steam" / ".local" / "share" / "Steam"
        logs_dir = flatpak_dir / "logs"
        if logs_dir.exists():
            return logs_dir
        
        return None
    
    def kill_processes(self, process_names: list[str]) -> None:
        """Kill processes by name on Linux."""
        import subprocess
        
        for name in process_names:
            try:
                subprocess.run(["pkill", "-f", name], capture_output=True)
            except FileNotFoundError:
                pass


class MacPlatform(PlatformInterface):
    """macOS platform implementation."""
    
    @property
    def name(self) -> str:
        return "darwin"
    
    def get_default_models_dir(self) -> Path:
        return Path.home() / "models"
    
    def get_default_cache_dir(self) -> Path:
        return Path.home() / "Library" / "Caches" / "local-ai"
    
    def get_default_log_dir(self) -> Path:
        return Path.home() / "Library" / "Logs" / "local-ai"
    
    def get_default_config_dir(self) -> Path:
        return Path.home() / "Library" / "Application Support" / "local-ai"
    
    def get_llama_server_path(self) -> Path:
        paths = [
            Path.home() / "bin" / "llama-server",
            Path("/usr/local/bin/llama-server"),
            Path("/opt/homebrew/bin/llama-server"),  # Apple Silicon
        ]
        for path in paths:
            if path.exists():
                return path
        return Path("llama-server")
    
    def enable_autostart(self, config, model: str = "auto") -> bool:
        """Enable launchd agent."""
        import subprocess
        
        plist_dir = Path.home() / "Library" / "LaunchAgents"
        plist_dir.mkdir(parents=True, exist_ok=True)
        
        plist_content = f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.localai.manager</string>
    <key>ProgramArguments</key>
    <array>
        <string>{config.llama_server_path}</string>
        <string>--model</string>
        <string>{model}</string>
        <string>--background</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
</dict>
</plist>
"""
        
        plist_file = plist_dir / "com.localai.manager.plist"
        plist_file.write_text(plist_content)
        
        try:
            subprocess.run(["launchctl", "load", str(plist_file)], check=True)
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            return False
    
    def disable_autostart(self) -> bool:
        """Disable launchd agent."""
        import subprocess
        
        plist_file = Path.home() / "Library" / "LaunchAgents" / "com.localai.manager.plist"
        
        try:
            if plist_file.exists():
                subprocess.run(["launchctl", "unload", str(plist_file)], check=True)
                plist_file.unlink()
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            return False
    
    def is_autostart_enabled(self) -> bool:
        """Check if launchd agent is loaded."""
        import subprocess
        
        try:
            result = subprocess.run(
                ["launchctl", "list", "com.localai.manager"],
                capture_output=True
            )
            return result.returncode == 0
        except FileNotFoundError:
            return False
    
    def get_steam_logs_path(self) -> Path | None:
        """Get Steam logs path on macOS."""
        steam_dir = Path.home() / "Library" / "Application Support" / "Steam"
        logs_dir = steam_dir / "logs"
        if logs_dir.exists():
            return logs_dir
        return None
    
    def kill_processes(self, process_names: list[str]) -> None:
        """Kill processes by name on macOS."""
        import subprocess
        
        for name in process_names:
            try:
                subprocess.run(["pkill", "-f", name], capture_output=True)
            except FileNotFoundError:
                pass


class WindowsPlatform(PlatformInterface):
    """Windows platform implementation."""
    
    @property
    def name(self) -> str:
        return "windows"
    
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
            Path.home() / "bin" / "llama-server.exe",
            Path("llama-server.exe"),
        ]
        for path in paths:
            if path.exists():
                return path
        return Path("llama-server.exe")
    
    def enable_autostart(self, config, model: str = "auto") -> bool:
        """Enable Windows Task Scheduler task."""
        import subprocess
        
        task_name = "LocalAI-AutoStart"
        venv_dir = Path.home() / "bin" / "local-ai-venv"
        python_exe = venv_dir / "Scripts" / "python.exe"
        
        cmd = f'"{python_exe}" -m local_ai_manager start --model {model} --background'
        
        create_cmd = [
            "schtasks",
            "/create",
            "/tn", task_name,
            "/tr", cmd,
            "/sc", "onlogon",
            "/rl", "highest",
            "/f",
        ]
        
        try:
            result = subprocess.run(create_cmd, capture_output=True, check=False)
            return result.returncode == 0
        except Exception:
            return False
    
    def disable_autostart(self) -> bool:
        """Disable Windows Task Scheduler task."""
        import subprocess
        
        try:
            subprocess.run(
                ["schtasks", "/delete", "/tn", "LocalAI-AutoStart", "/f"],
                capture_output=True,
                check=False
            )
            return True
        except Exception:
            return False
    
    def is_autostart_enabled(self) -> bool:
        """Check if Windows Task Scheduler task exists."""
        import subprocess
        
        try:
            result = subprocess.run(
                ["schtasks", "/query", "/tn", "LocalAI-AutoStart"],
                capture_output=True,
                check=False
            )
            return result.returncode == 0
        except Exception:
            return False
    
    def get_steam_logs_path(self) -> Path | None:
        """Get Steam logs path on Windows."""
        # Scoop installation
        scoop_path = Path.home() / "scoop" / "apps" / "steam" / "current" / "logs"
        if scoop_path.exists():
            return scoop_path
        
        # Standard Steam installation
        steam_paths = [
            Path("C:/Program Files (x86)/Steam/logs"),
            Path("C:/Program Files/Steam/logs"),
        ]
        for path in steam_paths:
            if path.exists():
                return path
        
        return None
    
    def kill_processes(self, process_names: list[str]) -> None:
        """Kill processes by name on Windows."""
        import subprocess
        
        for name in process_names:
            try:
                subprocess.run(
                    ["taskkill", "/F", "/IM", f"{name}.exe"],
                    capture_output=True
                )
            except FileNotFoundError:
                pass


def get_platform() -> PlatformInterface:
    """Factory function to get the appropriate platform implementation."""
    system = platform.system().lower()
    
    if system == "linux":
        return LinuxPlatform()
    elif system == "darwin":
        return MacPlatform()
    elif system == "windows":
        return WindowsPlatform()
    else:
        raise RuntimeError(f"Unsupported platform: {system}")


# Singleton instance
_platform_instance: PlatformInterface | None = None


def platform_instance() -> PlatformInterface:
    """Get the singleton platform instance."""
    global _platform_instance
    if _platform_instance is None:
        _platform_instance = get_platform()
    return _platform_instance
