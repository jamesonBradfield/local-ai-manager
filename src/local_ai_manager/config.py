"""Configuration management."""

from __future__ import annotations

import json
from pathlib import Path

from .defaults import DEFAULT_MODELS
from .models import SystemConfig
from .platform import platform_instance


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
    """Save configuration to file."""
    if config_path is None:
        config_path = get_config_path()
    
    config_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(config_path, "w", encoding="utf-8") as f:
        json.dump(config.model_dump(mode="json"), f, indent=2)


def create_default_config() -> SystemConfig:
    """Create a default configuration."""
    config = SystemConfig(models=list(DEFAULT_MODELS))
    config.server.models_dir = Path.home() / "models"
    config.server.default_model = "nanbeige-3b"
    return config
