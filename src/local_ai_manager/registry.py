"""Model registry for automatic GGUF discovery and management."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .models import ModelDefinition, SystemConfig


class ModelRegistry:
    """Registry for managing available GGUF models."""

    def __init__(self, config: SystemConfig) -> None:
        self.config = config
        self._available: dict[str, tuple[ModelDefinition, Path]] = {}
        self._scan()

    def _scan(self) -> None:
        """Scan models directory for available GGUF files."""
        models_dir = self.config.server.models_dir

        if not models_dir.exists():
            return

        for model_def in self.config.models:
            match = self._find_matching_file(model_def, models_dir)
            if match is not None:
                self._available[model_def.id] = (model_def, match)

    def _find_matching_file(self, model_def: ModelDefinition, directory: Path) -> Path | None:
        """Find a GGUF file matching the model definition."""
        for gguf_file in directory.glob("*.gguf"):
            if model_def.matches_file(gguf_file):
                return gguf_file.resolve()
        return None

    def get_available_models(self) -> list[tuple[str, ModelDefinition, Path]]:
        """Get list of available models with their paths."""
        return [
            (model_id, model_def, path) for model_id, (model_def, path) in self._available.items()
        ]

    def get_model_by_id(self, model_id: str) -> tuple[ModelDefinition, Path] | None:
        """Get a model definition and path by ID."""
        if model_id in self._available:
            return self._available[model_id]
        return None

    def get_auto_selected_model(self) -> tuple[str, ModelDefinition, Path] | None:
        """Auto-select the best available model."""

        # 1. Check configured default model first
        default_id = self.config.server.default_model
        if default_id and self.is_model_available(default_id):
            model_def, path = self._available[default_id]
            return (default_id, model_def, path)

        # 2. Fallback to priority sort
        available = self.get_available_models()
        if not available:
            return None

        # Sort by priority (lower = better)
        available.sort(key=lambda x: x[1].priority)
        return available[0]

    def is_model_available(self, model_id: str) -> bool:
        """Check if a model is available."""
        return model_id in self._available

    def refresh(self) -> None:
        """Re-scan the models directory."""
        self._available.clear()
        self._scan()

    def get_cache_path(self, model_id: str) -> Path:
        """Get the cache file path for a model."""
        cache_dir = self.config.server.cache_dir
        return cache_dir / f"{model_id}.cache"
