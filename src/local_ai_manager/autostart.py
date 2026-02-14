"""Windows startup task management."""

from __future__ import annotations

import subprocess
from pathlib import Path


def get_startup_task_name() -> str:
    """Get the name of the startup task."""
    return "LocalAI-AutoStart"


def enable_autostart(model: str = "auto", background: bool = True) -> bool:
    """Enable auto-start on Windows login using Task Scheduler."""
    task_name = get_startup_task_name()
    
    # Get Python executable path
    venv_dir = Path.home() / "bin" / "local-ai-venv"
    python_exe = venv_dir / "Scripts" / "python.exe"
    
    if not python_exe.exists():
        return False
    
    # Build command
    cmd = f'"{python_exe}" -m local_ai_manager start --model {model}'
    if background:
        cmd += " --background"
    
    # Use schtasks to create a task that runs on login
    create_cmd = [
        "schtasks",
        "/create",
        "/tn", task_name,
        "/tr", cmd,
        "/sc", "onlogon",
        "/rl", "highest",  # Run with highest privileges
        "/f",  # Force overwrite
    ]
    
    try:
        result = subprocess.run(create_cmd, capture_output=True, text=True, check=False)
        return result.returncode == 0
    except Exception:
        return False


def disable_autostart() -> bool:
    """Disable auto-start on Windows login."""
    task_name = get_startup_task_name()
    
    delete_cmd = [
        "schtasks",
        "/delete",
        "/tn", task_name,
        "/f",
    ]
    
    try:
        result = subprocess.run(delete_cmd, capture_output=True, text=True, check=False)
        return result.returncode == 0
    except Exception:
        return False


def is_autostart_enabled() -> bool:
    """Check if auto-start is enabled."""
    task_name = get_startup_task_name()
    
    query_cmd = [
        "schtasks",
        "/query",
        "/tn", task_name,
    ]
    
    try:
        result = subprocess.run(query_cmd, capture_output=True, text=True, check=False)
        return result.returncode == 0
    except Exception:
        return False
