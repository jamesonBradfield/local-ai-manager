#!/usr/bin/env python3
"""Migration script from PowerShell to Python Local AI Manager."""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path


def migrate() -> None:
    """Perform migration from PowerShell scripts to Python."""
    print("Local AI Manager Migration Tool")
    print("=" * 40)
    
    bin_dir = Path.home() / "bin"
    ps_scripts = [
        "Start-LocalAI.ps1",
        "Start-SteamWatcher.ps1",
        "Watch-SteamGames.ps1",
        "Stop-LocalAI.ps1",
        "Enter-GamingMode.ps1",
        "Exit-GamingMode.ps1",
    ]
    
    # Check for existing PowerShell scripts
    existing = [s for s in ps_scripts if (bin_dir / s).exists()]
    
    if existing:
        print(f"\nFound {len(existing)} PowerShell scripts to backup")
        
        # Create backup directory
        backup_dir = bin_dir / "ps-backup"
        backup_dir.mkdir(exist_ok=True)
        
        for script in existing:
            src = bin_dir / script
            dst = backup_dir / script
            shutil.copy2(src, dst)
            print(f"  Backed up: {script}")
        
        print(f"\nBackups saved to: {backup_dir}")
    
    # Install Python package
    print("\nInstalling Python package...")
    pkg_dir = bin_dir / "local-ai-manager"
    
    if pkg_dir.exists():
        print("  Package directory already exists")
    
    # Create virtual environment
    venv_dir = bin_dir / "local-ai-venv"
    if not venv_dir.exists():
        print("  Creating virtual environment...")
        subprocess.run([sys.executable, "-m", "venv", str(venv_dir)], check=True)
    
    # Install package
    pip = venv_dir / "Scripts" / "pip.exe"
    print("  Installing dependencies...")
    subprocess.run(
        [str(pip), "install", "-e", str(pkg_dir)],
        check=True,
        capture_output=True,
    )
    
    # Create wrapper scripts
    print("\nCreating wrapper scripts...")
    create_wrappers(bin_dir, venv_dir)
    
    # Initialize config
    print("\nInitializing configuration...")
    python = venv_dir / "Scripts" / "python.exe"
    subprocess.run(
        [str(python), "-m", "local_ai_manager", "config-init"],
        check=True,
    )
    
    print("\n" + "=" * 40)
    print("Migration complete!")
    print("\nNew commands:")
    print("  start-local-ai      - Start the AI server")
    print("  local-ai-server     - Server management")
    print("  local-ai-steam      - Steam watcher")
    print("\nOr use the full CLI:")
    print("  local-ai --help")


def create_wrappers(bin_dir: Path, venv_dir: Path) -> None:
    """Create Windows batch wrappers for convenience."""
    python = venv_dir / "Scripts" / "python.exe"
    
    wrappers = {
        "start-local-ai.bat": f'@"{python}" -m local_ai_manager start %*',
        "stop-local-ai.bat": f'@"{python}" -m local_ai_manager stop %*',
        "local-ai-status.bat": f'@"{python}" -m local_ai_manager status',
        "start-steam-watcher.bat": f'@"{python}" -m local_ai_manager steam start',
        "stop-steam-watcher.bat": f'@"{python}" -m local_ai_manager steam stop',
    }
    
    for name, content in wrappers.items():
        wrapper_path = bin_dir / name
        with open(wrapper_path, "w") as f:
            f.write(content + "\n")
        print(f"  Created: {name}")


if __name__ == "__main__":
    try:
        migrate()
    except KeyboardInterrupt:
        print("\n\nMigration cancelled")
        sys.exit(1)
    except Exception as e:
        print(f"\nError: {e}")
        sys.exit(1)
