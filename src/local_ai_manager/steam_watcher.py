"""Steam game watcher with AI lifecycle management."""

from __future__ import annotations

import re
import sys
import threading
import time
from pathlib import Path

import psutil
from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

from .models import SteamWatcherConfig, SystemConfig
from .server import LlamaServerManager


class SteamLogHandler(FileSystemEventHandler):
    """Handler for Steam log file changes."""
    
    PID_PATTERN = re.compile(r"adding PID (\d+) as a tracked process")
    
    def __init__(
        self,
        config: SteamWatcherConfig,
        server_manager: LlamaServerManager,
        on_game_launch: callable,
        on_game_exit: callable,
    ) -> None:
        self.config = config
        self.server_manager = server_manager
        self.on_game_launch = on_game_launch
        self.on_game_exit = on_game_exit
        self._file_position = 0
        self._running_games: dict[int, threading.Thread] = {}
    
    def on_modified(self, event) -> None:
        """Called when the log file is modified."""
        if not event.is_directory and event.src_path.endswith(self.config.log_file):
            self._process_new_lines(Path(event.src_path))
    
    def _process_new_lines(self, log_path: Path) -> None:
        """Process new lines added to the log file."""
        try:
            with open(log_path, "r", encoding="utf-8", errors="ignore") as f:
                f.seek(self._file_position)
                lines = f.readlines()
                self._file_position = f.tell()
        except Exception:
            return
        
        for line in lines:
            match = self.PID_PATTERN.search(line)
            if match:
                pid = int(match.group(1))
                self._handle_game_launch(pid)
    
    def _handle_game_launch(self, pid: int) -> None:
        """Handle a detected game launch."""
        if pid in self._running_games:
            return
        
        # Verify the process exists
        try:
            proc = psutil.Process(pid)
            proc_name = proc.name()
        except psutil.NoSuchProcess:
            return
        
        self.on_game_launch(pid, proc_name)
        
        # Start monitoring this game
        monitor_thread = threading.Thread(
            target=self._monitor_game_process,
            args=(pid,),
            daemon=True,
        )
        monitor_thread.start()
        self._running_games[pid] = monitor_thread
    
    def _monitor_game_process(self, pid: int) -> None:
        """Monitor a game process until it exits."""
        try:
            proc = psutil.Process(pid)
            proc.wait()
        except psutil.NoSuchProcess:
            pass
        finally:
            if pid in self._running_games:
                del self._running_games[pid]
                self.on_game_exit(pid)


class SteamWatcher:
    """Watches Steam games and manages AI lifecycle."""
    
    def __init__(self, system_config: SystemConfig) -> None:
        self.config = system_config
        self.steam_config = system_config.steam
        self.server_manager = LlamaServerManager(system_config.server)
        self._observer: Observer | None = None
        self._handler: SteamLogHandler | None = None
        self._log_file: Path | None = None
        self._last_model: str | None = None
    
    def _find_log_file(self) -> Path | None:
        """Find the Steam gameprocess_log.txt file."""
        primary = self.steam_config.steam_logs_dir / self.steam_config.log_file
        if primary.exists():
            return primary
        
        # Fallback: search scoop apps
        scoop_steam = Path.home() / "scoop" / "apps" / "steam"
        if scoop_steam.exists():
            for version_dir in scoop_steam.glob("*/logs"):
                candidate = version_dir / self.steam_config.log_file
                if candidate.exists():
                    return candidate
        
        return None
    
    def start(self) -> bool:
        """Start the Steam watcher."""
        self._log_file = self._find_log_file()
        if not self._log_file:
            return False
        
        # Ensure log directory exists
        log_dir = Path.home() / ".local" / "log"
        log_dir.mkdir(parents=True, exist_ok=True)
        
        self._handler = SteamLogHandler(
            config=self.steam_config,
            server_manager=self.server_manager,
            on_game_launch=self._on_game_launch,
            on_game_exit=self._on_game_exit,
        )
        
        # Process existing log content first
        self._handler._process_new_lines(self._log_file)
        
        self._observer = Observer()
        self._observer.schedule(
            self._handler,
            str(self._log_file.parent),
            recursive=False,
        )
        self._observer.start()
        
        return True
    
    def stop(self) -> None:
        """Stop the Steam watcher."""
        if self._observer:
            self._observer.stop()
            self._observer.join()
    
    def _on_game_launch(self, pid: int, proc_name: str) -> None:
        """Handle game launch - stop AI and save cache."""
        timestamp = time.strftime("%H:%M:%S")
        print(f"[{timestamp}] Game launched: {proc_name} (PID {pid})")
        
        if not self.steam_config.stop_ai_on_game:
            return
        
        # Save current model for later restoration
        if self.server_manager.is_running():
            self._last_model = self._get_current_model_id()
            
            # Save cache and stop server
            print(f"[{timestamp}] Saving prompt cache and stopping AI...")
            self.server_manager.stop(save_cache=True)
            
            # Kill other resource-heavy processes
            self._kill_cache_hogs()
            
            # Switch to cloud agent
            self._switch_agent("cloud")
    
    def _on_game_exit(self, pid: int) -> None:
        """Handle game exit - restore AI if no other games running."""
        timestamp = time.strftime("%H:%M:%S")
        print(f"[{timestamp}] Game closed (PID {pid})")
        
        if not self.steam_config.restart_ai_after_game:
            return
        
        # Check if any other games are still running
        if self._handler and self._handler._running_games:
            remaining = len(self._handler._running_games)
            print(f"[{timestamp}] Still have {remaining} game(s) running")
            return
        
        # Restore AI
        print(f"[{timestamp}] All games closed. Restoring AI...")
        self._restore_ai()
        self._switch_agent("local")
    
    def _get_current_model_id(self) -> str | None:
        """Get the ID of the currently running model."""
        status = self.server_manager.get_status()
        if status.get("details") and "model" in status["details"]:
            return status["details"]["model"]
        return self.config.server.default_model
    
    def _kill_cache_hogs(self) -> None:
        """Kill resource-heavy processes to free CPU cache."""
        for proc_name in self.steam_config.processes_to_kill:
            for proc in psutil.process_iter(["name"]):
                try:
                    if proc.info["name"] and proc_name.lower() in proc.info["name"].lower():
                        proc.kill()
                        print(f"  Killed {proc.info['name']}")
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass
    
    def _switch_agent(self, agent_type: str) -> None:
        """Switch Oh-My-Opencode agent configuration."""
        config_path = (
            self.config.opencode.config_dir / self.config.opencode.config_file
        )
        
        if not config_path.exists():
            return
        
        try:
            import json
            with open(config_path, encoding="utf-8") as f:
                data = json.load(f)
            
            agent_name = (
                self.config.opencode.local_agent_name
                if agent_type == "local"
                else self.config.opencode.cloud_agent_name
            )
            
            if data.get("default_agent") != agent_name:
                data["default_agent"] = agent_name
                with open(config_path, "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=2)
                print(f"  Switched default agent to '{agent_name}'")
        except Exception as e:
            print(f"  Failed to switch agent: {e}")
    
    def _restore_ai(self) -> None:
        """Restore the AI server after gaming."""
        from .config import load_config
        from .registry import ModelRegistry
        
        config = load_config()
        registry = ModelRegistry(config)
        
        # Determine which model to restore
        model_id = self._last_model or config.server.default_model
        
        if model_id and registry.is_model_available(model_id):
            model_def, model_path = registry.get_model_by_id(model_id)
        else:
            # Auto-select best available
            selection = registry.get_auto_selected_model()
            if not selection:
                print("  No models available to restore")
                return
            model_id, model_def, model_path = selection
        
        print(f"  Starting {model_def.name}...")
        
        # Start server with cache
        if self.server_manager.start(model_def, model_path, background=True):
            if self.server_manager.wait_for_ready(timeout=60):
                print(f"  AI restored successfully!")
            else:
                print(f"  AI started but health check failed")
        else:
            print(f"  Failed to start AI")
    
    def run(self) -> None:
        """Run the watcher until interrupted."""
        if not self.start():
            print("Failed to find Steam log file. Is Steam installed?")
            sys.exit(1)
        
        print(f"Steam Watcher started")
        print(f"  Monitoring: {self._log_file}")
        print(f"  Press Ctrl+C to stop")
        
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\nStopping Steam Watcher...")
        finally:
            self.stop()
