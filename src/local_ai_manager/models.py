"""Pydantic models for Local AI Manager configuration."""

from __future__ import annotations

import re
from enum import Enum
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator, model_validator

from .system_platform import platform_instance


class QuantizationType(str, Enum):
    """GGUF quantization types."""

    Q4_0 = "Q4_0"
    Q4_1 = "Q4_1"
    Q4_K_M = "Q4_K_M"
    Q4_K_S = "Q4_K_S"
    Q5_0 = "Q5_0"
    Q5_1 = "Q5_1"
    Q5_K_M = "Q5_K_M"
    Q5_K_S = "Q5_K_S"
    Q6_K = "Q6_K"
    Q8_0 = "Q8_0"
    F16 = "F16"
    F32 = "F32"


class ComputeBackend(str, Enum):
    """Compute backends for llama.cpp."""

    CPU = "cpu"
    CUDA = "cuda"
    VULKAN = "vulkan"
    METAL = "metal"
    OPENCL = "opencl"


class ModelDefinition(BaseModel):
    """Definition of a GGUF model with configuration."""

    # Identification
    id: str = Field(..., description="Unique identifier for the model")
    name: str = Field(..., description="Human-readable name")
    description: str = Field(default="", description="Optional description")

    # File matching
    filename: str | None = Field(default=None, description="Exact filename to match")
    filename_pattern: str | None = Field(
        default=None, description="Regex pattern to match filename"
    )

    # llama-server configuration
    ctx_size: int = Field(default=8192, description="Context size in tokens")
    n_gpu_layers: int = Field(default=99, description="Number of layers to offload to GPU")
    threads: int = Field(default=8, description="Number of CPU threads")
    batch_size: int = Field(default=4096, description="Batch size for prompt processing")
    ubatch_size: int = Field(default=1024, description="Micro-batch size")

    # Memory & performance
    flash_attn: bool = Field(default=True, description="Enable flash attention")
    mlock: bool = Field(default=True, description="Lock model in memory")
    mmap: bool = Field(default=True, description="Use memory mapping")
    cont_batching: bool = Field(default=True, description="Enable continuous batching")
    cache_type_k: str | None = Field(
        default=None, description="KV cache type for K (f16, q8_0, q4_0)"
    )
    cache_type_v: str | None = Field(
        default=None, description="KV cache type for V (f16, q8_0, q4_0)"
    )
    # Sampling parameters
    temperature: float = Field(default=0.6, ge=0.0, le=2.0)
    top_p: float = Field(default=0.95, ge=0.0, le=1.0)
    top_k: int = Field(default=40, ge=0)

    # Prompt caching
    cache_dir: str | None = Field(default=None, description="Directory for prompt cache")
    save_cache_on_exit: bool = Field(default=True, description="Save cache when stopping")

    # Priority for auto-selection (lower = higher priority)
    priority: int = Field(default=5, ge=1, le=10)

    # Tags for filtering/grouping
    tags: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_filename_or_pattern(self) -> "ModelDefinition":
        """Ensure either filename or filename_pattern is set."""
        if self.filename is None and self.filename_pattern is None:
            raise ValueError("Either 'filename' or 'filename_pattern' must be set")
        return self

    def matches_file(self, filepath: Path) -> bool:
        """Check if this definition matches a given file path."""
        if self.filename is not None:
            return filepath.name == self.filename
        if self.filename_pattern is not None:
            return bool(re.search(self.filename_pattern, filepath.name, re.IGNORECASE))
        return False

    def estimate_vram_gb(self) -> float:
        """Estimate VRAM usage in GB."""
        # Rough estimation based on context size
        # Model weights + KV cache
        kv_cache_gb = (self.ctx_size * 2 * 128 * 32) / (1024**3)  # Rough estimate
        return kv_cache_gb + 2.0  # Base model estimate


class ServerConfig(BaseModel):
    """Configuration for llama-server."""

    host: str = Field(default="127.0.0.1")
    port: int = Field(default=8080, ge=1024, le=65535)

    # Paths - use platform-specific defaults
    llama_server_path: Path = Field(
        default_factory=lambda: platform_instance().get_llama_server_path()
    )
    models_dir: Path = Field(default_factory=lambda: platform_instance().get_default_models_dir())
    cache_dir: Path = Field(default_factory=lambda: platform_instance().get_default_cache_dir())
    log_dir: Path = Field(default_factory=lambda: platform_instance().get_default_log_dir())

    # Behavior
    auto_start: bool = Field(default=False, description="Auto-start server on boot")
    default_model: str | None = Field(default=None, description="Default model to use")

    @field_validator("models_dir", "cache_dir", "log_dir", "llama_server_path", mode="before")
    @classmethod
    def expand_path(cls, v: Any) -> Path:
        """Expand user paths."""
        if isinstance(v, str):
            return Path(v).expanduser()
        return v


class SteamWatcherConfig(BaseModel):
    """Configuration for Steam game watcher."""

    enabled: bool = Field(default=True)

    # Steam paths - use platform-specific detection
    steam_logs_dir: Path = Field(
        default_factory=lambda: platform_instance().get_steam_logs_path() or Path.home() / ".steam"
    )
    log_file: str = Field(default="gameprocess_log.txt")

    # Behavior
    stop_ai_on_game: bool = Field(default=True, description="Stop AI when game launches")
    save_cache_on_stop: bool = Field(default=True, description="Save prompt cache before stopping")
    restart_ai_after_game: bool = Field(default=True, description="Restart AI after game closes")
    restore_model: str | None = Field(default=None, description="Model to restore after gaming")

    # Process cleanup - platform-specific process names
    processes_to_kill: list[str] = Field(
        default_factory=lambda: [
            "chrome",
            "firefox",
            "safari",
            "msedge",
            "discord",
            "slack",
            "teams",
        ]
    )

    @field_validator("steam_logs_dir", mode="before")
    @classmethod
    def expand_path(cls, v: Any) -> Path:
        """Expand user paths."""
        if isinstance(v, str):
            return Path(v).expanduser()
        return v


class OpencodeConfig(BaseModel):
    """Configuration for Oh-My-Opencode integration."""

    config_dir: Path = Field(
        default_factory=lambda: platform_instance().get_default_config_dir().parent / "opencode"
    )

    # Agent switching
    local_agent_name: str = Field(default="local")
    cloud_agent_name: str = Field(default="cloud")
    config_file: str = Field(default="oh-my-opencode.json")

    @field_validator("config_dir", mode="before")
    @classmethod
    def expand_path(cls, v: Any) -> Path:
        """Expand user paths."""
        if isinstance(v, str):
            return Path(v).expanduser()
        return v


class TextgradOptimizerType(str, Enum):
    """Optimizer types for textgrad workflows."""

    PROPOSITIONAL = "propositional"
    TREE_OF_THOUGHTS = "tree_of_thoughts"
    FEW_SHOT = "few_shot"
    CRITIC = "critic"
    MULTI_MODEL = "multi_model"


class TextgradWorkflow(BaseModel):
    """A textgrad optimization workflow configuration."""

    schema_version: str = Field(default="1.0.0")
    workflow_version: int = Field(default=1)

    # Identification
    id: str = Field(..., description="Unique workflow identifier")
    name: str = Field(..., description="Human-readable name")
    description: str = Field(default="", description="Optional description")

    # Model configuration
    forward_model_id: str = Field(..., description="Model ID for generation")
    backward_model_id: str | None = Field(
        default=None, description="Model ID for critique (None = use forward_model)"
    )
    optimizer_model_id: str | None = Field(
        default=None, description="Model ID for prompt updates (None = use forward_model)"
    )

    # Optimizer settings
    optimizer_type: TextgradOptimizerType = Field(default=TextgradOptimizerType.CRITIC)
    max_iterations: int = Field(default=10, ge=1, le=50)
    convergence_threshold: float = Field(default=0.9, ge=0.0, le=1.0)

    # Workflow state
    initial_prompt: str = Field(default="")
    optimized_prompt: str | None = Field(default=None)
    history: list[dict] = Field(default_factory=list)

    created_at: str = Field(default_factory=lambda: str(Path().stat().st_mtime))
    updated_at: str = Field(default_factory=lambda: str(Path().stat().st_mtime))

    @field_validator("schema_version")
    @classmethod
    def validate_version(cls, v: str) -> str:
        """Validate schema version."""
        if not v.startswith("1."):
            raise ValueError(f"Unsupported schema version: {v}")
        return v


class TextgradSettings(BaseModel):
    """Global textgrad configuration."""

    enabled: bool = Field(default=False)
    default_forward_model: str | None = Field(default=None)
    default_optimizer: TextgradOptimizerType = Field(default=TextgradOptimizerType.CRITIC)
    auto_save_workflows: bool = Field(default=True)
    max_iterations_default: int = Field(default=10, ge=1, le=100)


class SystemConfig(BaseModel):
    """Root configuration for Local AI Manager."""

    version: str = Field(default="2.0.0")

    # Sub-configs
    server: ServerConfig = Field(default_factory=ServerConfig)
    steam: SteamWatcherConfig = Field(default_factory=SteamWatcherConfig)
    opencode: OpencodeConfig = Field(default_factory=OpencodeConfig)
    textgrad: TextgradSettings = Field(default_factory=TextgradSettings)

    # Model definitions
    models: list[ModelDefinition] = Field(default_factory=list)

    # Saved workflows
    workflows: list[TextgradWorkflow] = Field(default_factory=list)

    # Global settings
    verbose: bool = Field(default=False)
    dry_run: bool = Field(default=False)
    auto_shutdown_on_exit: bool = Field(default=False)
