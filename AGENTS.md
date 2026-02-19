# Local AI Manager - Agent Instructions

Python CLI application for managing local LLMs with Steam integration.

## Build, Test & Lint Commands

```bash
# Install development dependencies
pip install -e ".[dev]"

# Run tests
pytest                              # All tests
pytest tests/test_platform.py      # Single test file
pytest tests/test_platform.py::test_linux_platform -v  # Single test

# Code quality
black src/          # Format (line-length: 100)
ruff check src/     # Lint
mypy src/           # Type check (strict)

# Build & run
python -m build
python -m local_ai_manager --help
```

## Code Style Guidelines

### Imports
- Always start with `from __future__ import annotations`
- Order: stdlib → third-party → local (alphabetical within groups)
- Use `TYPE_CHECKING` for imports only needed for type hints

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

### Type Hints & Naming
- **Required** for all function parameters and return types
- Use modern syntax: `str | None`, `list[str]`, `Path | None`
- Classes: PascalCase (`LlamaServerManager`)
- Functions/variables: snake_case (`get_default_models_dir`)
- Constants: UPPER_SNAKE_CASE
- Private members: single underscore prefix `_internal_method`

### Docstrings & Formatting
- Use triple double quotes `"""` for all modules, classes, and public functions
- Line length: 100 characters
- Use double quotes for strings, trailing commas in multi-line structures

```python
class MyClass:
    """Class description."""
    
    def my_method(self, param: str) -> bool:
        """Short description.
        
        Args:
            param: Description of param
            
        Returns:
            Description of return value
        """
```

### Error Handling
- Always catch specific exceptions, never bare `except:`
- Common pattern for process iteration:

```python
for proc in psutil.process_iter(["name"]):
    try:
        if proc.info["name"] and "target" in proc.info["name"]:
            pass
    except (psutil.NoSuchProcess, psutil.AccessDenied):
        pass
```

### Pydantic Models
```python
class ModelDefinition(BaseModel):
    """Definition of a GGUF model."""
    
    id: str = Field(..., description="Unique identifier")
    name: str = Field(..., description="Human-readable name")
    tags: list[str] = Field(default_factory=list)  # Mutable defaults
```

### CLI Commands (Typer)
```python
@app.command()
def my_command(
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Show detailed info"),
) -> None:
    """Brief description shown in help."""
    console.print("[green]Success![/green]")
```

## Technology Stack

| Component | Library |
|-----------|---------|
| CLI | Typer + Rich |
| Models | Pydantic v2 |
| Process mgmt | psutil |
| HTTP | httpx |
| Testing | pytest + pytest-asyncio |
| Formatting | Black (100 chars) |
| Linting | Ruff |
| Type checking | MyPy (strict) |
| Build | Hatchling |

## Project Structure

```
src/local_ai_manager/
├── __init__.py         # Version info
├── __main__.py         # Entry point
├── cli.py              # Typer CLI commands
├── models.py           # Pydantic models
├── config.py           # Config loading/saving
├── system_platform.py  # Platform abstraction
├── server.py           # Llama server lifecycle
├── registry.py         # Model discovery
├── steam_watcher.py    # Steam integration
└── autostart.py        # Windows autostart
```

## Architecture Patterns

- **Platform abstraction**: Extend `PlatformInterface` for new OS support
- **Registry pattern**: `ModelRegistry` handles model discovery
- **Manager pattern**: `LlamaServerManager` handles process lifecycle

## Common Tasks

### Add a CLI command
1. Add function in `cli.py` with `@app.command()` decorator
2. Use type hints for all parameters
3. Use Rich `console.print()` for output
4. Add docstring for help text

### Add a configuration option
1. Add field to model in `models.py` with `Field(description=...)`
2. Add `@field_validator` or `@model_validator` if needed
3. Update `create_default_config()` in `config.py`

### Add platform support
1. Create class inheriting from `PlatformInterface`
2. Implement all abstract methods
3. Register in `get_platform()` factory function
4. Add platform-specific process names to `processes_to_kill`
