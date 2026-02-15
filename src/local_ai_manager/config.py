"""Configuration management."""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path

from .defaults import DEFAULT_MODELS
from .models import SystemConfig
from .system_platform import platform_instance


CONFIG_FILENAME = "local-ai-config.json"


def get_config_path() -> Path:
    """Get the path to the configuration file."""
    return platform_instance().get_default_config_dir() / CONFIG_FILENAME


def load_config(config_path: Path | None = None) -> SystemConfig:
    """Load configuration from file or create default."""
    if config_path is None:
        config_path = get_config_path()

    if config_path.exists():
        with open(config_path, encoding="utf-8") as f:
            data = json.load(f)
        return SystemConfig(**data)

    return create_default_config()


def save_config(config: SystemConfig, config_path: Path | None = None) -> None:
    """Save configuration to file atomically to prevent corruption.

    Writes to a temporary file first, then atomically renames it to the target.
    This ensures the config file is never in a partially-written state.
    """
    if config_path is None:
        config_path = get_config_path()

    config_path.parent.mkdir(parents=True, exist_ok=True)

    # Write to temporary file in the same directory (required for atomic rename on Windows)
    temp_fd = None
    temp_path = None
    try:
        temp_fd, temp_path = tempfile.mkstemp(
            dir=config_path.parent, suffix=".tmp", prefix=".local-ai-config-"
        )

        with os.fdopen(temp_fd, "w", encoding="utf-8") as f:
            json.dump(config.model_dump(mode="json"), f, indent=2)
            f.flush()
            os.fsync(f.fileno())  # Ensure data is written to disk

        temp_fd = None  # File is closed by context manager

        # Atomic rename (on Windows, this requires the target to not exist or be replaceable)
        if os.name == "nt":  # Windows
            # On Windows, os.replace works like atomic rename if target exists
            os.replace(temp_path, config_path)
        else:
            # On Unix, os.rename is atomic
            os.replace(temp_path, config_path)

    except Exception:
        # Clean up temp file on error
        if temp_fd is not None:
            os.close(temp_fd)
        if temp_path and os.path.exists(temp_path):
            os.unlink(temp_path)
        raise


def create_default_config() -> SystemConfig:
    """Create a default configuration."""
    config = SystemConfig(models=list(DEFAULT_MODELS))
    config.server.models_dir = Path.home() / "models"
    config.server.default_model = "nanbeige-3b"
    return config
