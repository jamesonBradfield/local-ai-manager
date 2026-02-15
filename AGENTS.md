# Local AI Manager - Agent Instructions

Guidelines for AI agents working on this Python CLI application for managing local LLMs.

## Build, Test & Lint Commands

```bash
# Install development dependencies
pip install -e ".[dev]"

# Run all tests
pytest

# Run a single test file
pytest tests/test_platform.py

# Run a specific test
pytest tests/test_platform.py::test_linux_platform -v

# Run with coverage
pytest --cov=local_ai_manager --cov-report=html

# Format code
black src/

# Lint
ruff check src/

# Type check
mypy src/

# Build package
python -m build

# Run the CLI locally
python -m local_ai_manager --help
```

## Code Style Guidelines

### Imports
- Always use `from __future__ import annotations` as the first import
- Order: standard library, third-party, local (alphabetical within groups)
- Use TYPE_CHECKING for imports only needed for type hints

```python
from __future__ import annotations

import re
from pathlib import Path
from typing import TYPE_CHECKING

from pydantic import BaseModel
from rich.console import Console

from .models import ModelDefinition

if TYPE_CHECKING:
    from .config import SystemConfig
```

### Type Hints
- Required for all function parameters and return types
- Use modern syntax: `str | None` instead of `Optional[str]`
- Use `list[str]` instead of `List[str]`
- Use `Path | None` for optional paths

### Naming Conventions
- Classes: PascalCase (e.g., `LlamaServerManager`)
- Functions/variables: snake_case (e.g., `get_default_models_dir`)
- Constants: UPPER_SNAKE_CASE
- Private methods/attributes: single underscore prefix `_internal_method`
- Module names: snake_case (e.g., `system_platform.py`)

### Docstrings
- Use triple double quotes `"""`
- All modules have a brief description
- All classes have docstrings
- All public functions have docstrings

```python
"""Brief module description."""

class MyClass:
    """Class description."""
    
    def my_method(self, param: str) -> bool:
        """Short description.
        
        Longer description if needed.
        
        Args:
            param: Description of param
            
        Returns:
            Description of return value
        """
```

### Formatting
- Line length: 100 characters (configured in pyproject.toml)
- Use double quotes for strings
- Trailing commas in multi-line structures
- Black formatter is mandatory

### Error Handling
- Always catch specific exceptions, not bare `except:`
- Common pattern for process iteration:

```python
for proc in psutil.process_iter(["name"]):
    try:
        if proc.info["name"] and "target" in proc.info["name"]:
            # do something
            pass
    except (psutil.NoSuchProcess, psutil.AccessDenied):
        pass
```

### Pydantic Models
- Use `Field()` with descriptions for all fields
- Use validators for complex validation logic
- Use `default_factory=list` for mutable defaults

```python
class ModelDefinition(BaseModel):
    """Definition of a GGUF model."""
    
    id: str = Field(..., description="Unique identifier")
    name: str = Field(..., description="Human-readable name")
    tags: list[str] = Field(default_factory=list)
```

### CLI Commands (Typer)
- Use type annotations; Typer auto-generates options
- Group related commands with sub-typers
- Use Rich for formatted output (tables, panels)

```python
@app.command()
def my_command(
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Show detailed info"),
) -> None:
    """Brief description shown in help."""
    console.print("[green]Success![/green]")
```

### Architecture Patterns
- Platform abstraction: Extend `PlatformInterface` for new OS support
- Registry pattern: `ModelRegistry` handles model discovery
- Manager pattern: `LlamaServerManager` handles process lifecycle

## Technology Stack
- **CLI**: Typer + Rich
- **Models**: Pydantic v2
- **Process management**: psutil
- **HTTP**: httpx
- **Testing**: pytest + pytest-asyncio
- **Formatting**: Black (line-length 100)
- **Linting**: Ruff
- **Type checking**: MyPy (strict)
- **Build**: Hatchling

## Project Structure
```
src/local_ai_manager/
├── __init__.py         # Version info
├── __main__.py         # Entry point
├── cli.py              # Typer CLI commands
├── models.py           # Pydantic configuration models
├── config.py           # Config loading/saving
├── system_platform.py  # Platform abstraction (Linux/Mac/Windows)
├── server.py           # Llama server lifecycle management
├── registry.py         # Model discovery and selection
├── steam_watcher.py    # Steam integration
└── autostart.py        # Windows autostart management
```

## Common Tasks

### Adding a new CLI command
1. Add function in `cli.py` with `@app.command()` decorator
2. Use type hints for all parameters
3. Use Rich `console.print()` for output
4. Add docstring for help text

### Adding a new configuration option
1. Add field to appropriate model in `models.py`
2. Use `Field()` with description
3. Add validator if needed with `@field_validator` or `@model_validator`
4. Update `create_default_config()` in `config.py`

### Adding platform support
1. Create new class inheriting from `PlatformInterface`
2. Implement all abstract methods
3. Register in `get_platform()` factory function
4. Add platform-specific process names to `processes_to_kill`
