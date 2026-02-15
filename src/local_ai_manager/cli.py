"""Command-line interface for Local AI Manager."""

from __future__ import annotations

import shlex
import sys
from pathlib import Path

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from .autostart import disable_autostart, enable_autostart, is_autostart_enabled
from .config import create_default_config, load_config, save_config
from .registry import ModelRegistry
from .server import LlamaServerManager
from .steam_watcher import SteamWatcher

app = typer.Typer(help="Local AI Manager - Manage local LLMs with Steam integration")
console = Console()


# Security validation for extra_args
DANGEROUS_ARGS = {
    "--rm",
    "--delete",
    "--exec",
    "--eval",
    "--shell",
    "|",
    ">",
    "<",
    "&&",
    "||",
    ";",
    "`",
    "$",
}


def validate_extra_args(extra_args: str | None) -> list[str]:
    """Validate extra_args for security issues.

    Args:
        extra_args: Raw extra arguments string

    Returns:
        List of parsed arguments

    Raises:
        typer.Exit: If dangerous arguments detected
    """
    if not extra_args:
        return []

    try:
        parsed = shlex.split(extra_args)
    except ValueError as e:
        console.print(f"[red]Error parsing extra arguments: {e}[/red]")
        raise typer.Exit(1)

    # Check for dangerous arguments
    for arg in parsed:
        arg_lower = arg.lower()
        if any(dangerous in arg_lower for dangerous in DANGEROUS_ARGS):
            console.print(
                f"[red]Security Error: Potentially dangerous argument detected: '{arg}'[/red]"
            )
            console.print(
                "[yellow]For security, the following are not allowed in extra_args:[/yellow]"
            )
            console.print(f"  {', '.join(sorted(DANGEROUS_ARGS))}")
            raise typer.Exit(1)

    return parsed


@app.command()
def list_models(
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Show detailed info"),
) -> None:
    """List all available models and their status."""
    config = load_config()
    registry = ModelRegistry(config)

    table = Table(title="Available Models")
    table.add_column("ID", style="cyan")
    table.add_column("Name", style="green")
    table.add_column("Status", style="yellow")
    table.add_column("Priority", style="blue")

    if verbose:
        table.add_column("Context", style="magenta")
        table.add_column("Path", style="dim")

    for model_id, model_def, path in registry.get_available_models():
        status = "[green]Available[/green]" if path.exists() else "[red]Missing[/red]"
        row = [
            model_id,
            model_def.name,
            status,
            str(model_def.priority),
        ]
        if verbose:
            row.extend(
                [
                    f"{model_def.ctx_size:,}",
                    str(path),
                ]
            )
        table.add_row(*row)

    console.print(table)

    # Show auto-selected model
    auto = registry.get_auto_selected_model()
    if auto:
        console.print(f"\n[bold green]Auto-selected:[/bold green] {auto[1].name}")


@app.command()
def start(
    model: str = typer.Option("auto", "--model", "-m", help="Model ID or 'auto'"),
    background: bool = typer.Option(False, "--background", "-b", help="Run in background"),
    context: int = typer.Option(0, "--context", "-c", help="Override context size"),
    no_cache: bool = typer.Option(False, "--no-cache", help="Disable prompt caching"),
    autostart: bool = typer.Option(
        False, "--autostart", "-a", help="Enable auto-start on Windows login"
    ),
    extra_args: str = typer.Option(
        "", "--extra-args", "-e", help="Extra arguments for llama-server (quoted string)"
    ),
) -> None:
    """Start the llama-server with the specified model."""
    config = load_config()
    registry = ModelRegistry(config)
    server = LlamaServerManager(config.server)

    # Determine which model to use
    if model == "auto":
        selection = registry.get_auto_selected_model()
        if not selection:
            console.print("[red]No models available![/red]")
            console.print("\nDownload a model to ~/models/")
            raise typer.Exit(1)
        model_id, model_def, model_path = selection
    else:
        result = registry.get_model_by_id(model)
        if not result:
            console.print(f"[red]Model '{model}' not found[/red]")
            available = [m[0] for m in registry.get_available_models()]
            if available:
                console.print(f"Available: {', '.join(available)}")
            raise typer.Exit(1)
        model_def, model_path = result
        model_id = model

    # Override context size if specified
    if context > 0:
        # Validate context doesn't exceed model maximum
        max_ctx = model_def.ctx_size
        if context > max_ctx:
            console.print(
                f"[red]Error: Requested context size ({context}) exceeds model maximum ({max_ctx})[/red]"
            )
            console.print(f"[yellow]Tip: Use --context {max_ctx} or less for this model[/yellow]")
            raise typer.Exit(1)
        model_def.ctx_size = context

    # Parse and validate extra arguments
    parsed_extra_args = validate_extra_args(extra_args) if extra_args else None
    if parsed_extra_args:
        console.print(f"[dim]Extra args: {' '.join(parsed_extra_args)}[/dim]")

    # Display startup info
    console.print(
        Panel(
            f"[bold cyan]{model_def.name}[/bold cyan]\n"
            f"Context: {model_def.ctx_size:,} tokens\n"
            f"GPU Layers: {model_def.n_gpu_layers}\n"
            f"Flash Attention: {'Yes' if model_def.flash_attn else 'No'}\n"
            f"Prompt Cache: {'No' if no_cache else 'Yes'}",
            title="Starting Server",
        )
    )

    # Start the server
    if server.start(
        model_def,
        model_path,
        background=background,
        use_cache=not no_cache,
        extra_args=parsed_extra_args,
    ):
        if background:
            console.print("[green]Server started in background[/green]")
            console.print(f"  Logs: {config.server.log_dir}/llama-server-{model_id}.log")

            if server.wait_for_ready(timeout=60):
                console.print("[green]Server is ready![/green]")
            else:
                console.print("[yellow]Server starting... check logs[/yellow]")
        else:
            # Foreground mode - blocks until server exits
            pass
    else:
        console.print("[red]Failed to start server[/red]")
        raise typer.Exit(1)

    # Enable autostart if requested
    if autostart:
        console.print("\n[yellow]Enabling auto-start on login...[/yellow]")
        if enable_autostart(model=model_id, background=True):
            console.print("[green]Auto-start enabled![/green]")
            console.print("  The AI server will start automatically when you login")
            console.print("  Disable with: local-ai autostart disable")
        else:
            console.print("[red]Failed to enable auto-start[/red]")


@app.command()
def stop(
    save_cache: bool = typer.Option(True, help="Save prompt cache before stopping"),
) -> None:
    """Stop the running llama-server."""
    config = load_config()
    server = LlamaServerManager(config.server)

    if not server.is_running():
        console.print("[yellow]Server is not running[/yellow]")
        return

    console.print("Stopping server...")
    if server.stop(save_cache=save_cache):
        console.print("[green]Server stopped[/green]")
    else:
        console.print("[red]Failed to stop server gracefully[/red]")


@app.command()
def status() -> None:
    """Check the status of the llama-server and autostart."""
    config = load_config()
    server = LlamaServerManager(config.server)

    status_info = server.get_status()

    if status_info["running"]:
        if status_info["healthy"]:
            console.print("[green]Server is running and healthy[/green]")
            if status_info.get("details"):
                details = status_info["details"]
                console.print(f"  Model: {details.get('model', 'Unknown')}")
                console.print(f"  Version: {details.get('version', 'Unknown')}")
        else:
            console.print("[yellow]Server is running but not responding[/yellow]")
            if status_info.get("error"):
                console.print(f"  Error: {status_info['error']}")
    else:
        console.print("[red]Server is not running[/red]")

    # Show autostart status
    if is_autostart_enabled():
        console.print("\n[green]Auto-start is enabled[/green]")
    else:
        console.print("\n[dim]Auto-start is disabled[/dim]")


@app.command()
def config_init(
    force: bool = typer.Option(False, "--force", help="Overwrite existing config"),
) -> None:
    """Initialize default configuration file."""
    config_path = Path.home() / ".config" / "local-ai" / "local-ai-config.json"

    if config_path.exists() and not force:
        console.print(f"[yellow]Config already exists at {config_path}[/yellow]")
        console.print("Use --force to overwrite")
        return

    config = create_default_config()
    save_config(config, config_path)

    console.print(f"[green]Configuration created at {config_path}[/green]")
    console.print("\nEdit this file to customize:")
    console.print("  - Model definitions")
    console.print("  - Server settings")
    console.print("  - Steam watcher behavior")


@app.command()
def config_show() -> None:
    """Display current configuration."""
    config = load_config()

    console.print(
        Panel(
            f"[bold]Models Directory:[/bold] {config.server.models_dir}\n"
            f"[bold]Cache Directory:[/bold] {config.server.cache_dir}\n"
            f"[bold]Log Directory:[/bold] {config.server.log_dir}\n"
            f"[bold]Default Model:[/bold] {config.server.default_model or 'Auto'}\n"
            f"[bold]Steam Watcher:[/bold] {'Enabled' if config.steam.enabled else 'Disabled'}",
            title="Configuration",
        )
    )

    table = Table(title="Model Definitions")
    table.add_column("ID", style="cyan")
    table.add_column("Name", style="green")
    table.add_column("Pattern", style="dim")

    for model in config.models:
        pattern = model.filename or model.filename_pattern or "N/A"
        table.add_row(model.id, model.name, pattern[:40] + "..." if len(pattern) > 40 else pattern)

    console.print(table)


# Steam watcher subcommand
steam_app = typer.Typer(help="Steam game watcher commands")
app.add_typer(steam_app, name="steam")


@steam_app.command("start")
def steam_start() -> None:
    """Start the Steam watcher daemon."""
    config = load_config()
    watcher = SteamWatcher(config)
    watcher.run()


@steam_app.command("status")
def steam_status() -> None:
    """Check if the Steam watcher is running."""
    if SteamWatcher.is_running():
        console.print("[green]Steam watcher is running[/green]")
    else:
        console.print("[yellow]Steam watcher is not running[/yellow]")
        console.print("\nStart with: local-ai steam start")


@steam_app.command("stop")
def steam_stop() -> None:
    """Stop the Steam watcher daemon."""
    stopped = SteamWatcher.stop_all()

    if stopped > 0:
        console.print(f"[green]Stopped {stopped} watcher process(es)[/green]")
    else:
        console.print("[yellow]No watcher processes found[/yellow]")


# Autostart subcommand
autostart_app = typer.Typer(help="Manage Windows startup settings")
app.add_typer(autostart_app, name="autostart")


@autostart_app.command("enable")
def autostart_enable(
    model: str = typer.Option("auto", "--model", "-m", help="Model to auto-start"),
    background: bool = typer.Option(True, "--background", "-b", help="Run in background"),
) -> None:
    """Enable auto-start on Windows login."""
    console.print(f"[yellow]Enabling auto-start with model '{model}'...[/yellow]")

    if enable_autostart(model=model, background=background):
        console.print("[green]Auto-start enabled![/green]")
        console.print(f"  Model: {model}")
        console.print(f"  Background: {background}")
        console.print("\nThe AI server will start automatically when you login to Windows")
    else:
        console.print("[red]Failed to enable auto-start[/red]")
        console.print("\nTroubleshooting:")
        console.print("  - Ensure Python virtual environment exists at ~/bin/local-ai-venv")
        console.print("  - Run as Administrator if permission denied")


@autostart_app.command("disable")
def autostart_disable() -> None:
    """Disable auto-start on Windows login."""
    console.print("[yellow]Disabling auto-start...[/yellow]")

    if disable_autostart():
        console.print("[green]Auto-start disabled![/green]")
    else:
        console.print("[yellow]Auto-start was not enabled[/yellow]")


@autostart_app.command("status")
def autostart_status() -> None:
    """Check auto-start status."""
    if is_autostart_enabled():
        console.print("[green]Auto-start is enabled[/green]")
        console.print("  The AI server will start automatically on login")
    else:
        console.print("[yellow]Auto-start is disabled[/yellow]")
        console.print("\nEnable with: local-ai autostart enable")


def main() -> None:
    """Main entry point."""
    app()


# Legacy CLI aliases for backward compatibility
def server_cli() -> None:
    """Server management CLI (legacy entry point)."""
    app()


def steam_cli() -> None:
    """Steam watcher CLI (legacy entry point)."""
    sys.argv.insert(1, "steam")
    app()
