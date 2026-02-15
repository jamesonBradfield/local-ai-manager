"""Llama server lifecycle management and HTTP API wrapper."""

from __future__ import annotations

import asyncio
import json
import shlex
import subprocess
import time
from pathlib import Path
from typing import TYPE_CHECKING

import httpx
import psutil
from rich.console import Console

if TYPE_CHECKING:
    from .config import ServerConfig
from .models import ModelDefinition


console = Console()


class LlamaServerManager:
    """Manages llama-server process lifecycle and HTTP API interactions."""

    def __init__(self, config: ServerConfig) -> None:
        """Initialize server manager.

        Args:
            config: Server configuration
        """
        self.config = config
        self.pid_file = config.cache_dir / "server.pid"
        self._register_shutdown_handler()

    def is_running(self) -> bool:
        """Check if llama-server is running."""
        if not self.pid_file.exists():
            return False

        try:
            pid = int(self.pid_file.read_text().strip())
            process = psutil.Process(pid)

            if not process.is_running():
                self.pid_file.unlink()
                return False

            if "llama" not in process.name().lower():
                self.pid_file.unlink()
                return False

            return True

        except (psutil.NoSuchProcess, ValueError, FileNotFoundError):
            if self.pid_file.exists():
                self.pid_file.unlink()
            return False

    def stop(self, save_cache: bool = False) -> bool:
        """Stop the server process.

        Args:
            save_cache: Whether to preserve the model cache

        Returns:
            True if stopped successfully
        """
        if not self.is_running():
            return True

        try:
            pid = int(self.pid_file.read_text().strip())
            process = psutil.Process(pid)

            if not save_cache:
                # Find and terminate the process without cache
                parent = psutil.Process(pid)
                children = parent.children(recursive=True)
                for child in children:
                    child.terminate()
                parent.terminate()

                gone, alive = psutil.wait_procs(children + [parent], timeout=5)
                for p in alive:
                    p.kill()
            else:
                process.terminate()
                try:
                    process.wait(timeout=5)
                except psutil.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=2)

            if self.pid_file.exists():
                self.pid_file.unlink()

            return True

        except Exception as e:
            console.print(f"[red]Error stopping server: {e}[/red]")
            return False

    def start(
        self,
        model_def: ModelDefinition,
        model_path: Path,
        background: bool = True,
        use_cache: bool = False,
        extra_args: list[str] | None = None,
    ) -> bool:
        """Start the server process.

        Args:
            model_def: Model definition
            model_path: Path to model file
            background: Run in background
            use_cache: Use cached model weights
            extra_args: Additional server arguments

        Returns:
            True if started successfully
        """
        if self.is_running():
            console.print("[yellow]Server is already running[/yellow]")
            return True

        if not model_path.exists():
            console.print(f"[red]Model file not found: {model_path}[/red]")
            return False

        args = self._build_args(model_def, model_path, use_cache, extra_args)

        try:
            if background:
                return self._start_background(args)
            return self._start_foreground(args)
        except Exception as e:
            console.print(f"[red]Failed to start server: {e}[/red]")
            return False

    def _build_args(
        self,
        model_def: ModelDefinition,
        model_path: Path,
        use_cache: bool,
        extra_args: list[str] | None,
    ) -> list[str]:
        """Build server command arguments."""
        args = [
            str(self.config.llama_server_path),
            "--model",
            str(model_path),
            "--ctx-size",
            str(model_def.ctx_size),
            "--n-gpu-layers",
            str(model_def.n_gpu_layers),
            "--threads",
            str(model_def.threads),
            "--batch-size",
            str(model_def.batch_size),
            "--ubatch-size",
            str(model_def.ubatch_size),
            "--host",
            self.config.host,
            "--port",
            str(self.config.port),
        ]

        if model_def.cache_type_k:
            args.extend(["--cache-type-k", model_def.cache_type_k.value])

        if model_def.cache_type_v:
            args.extend(["--cache-type-v", model_def.cache_type_v.value])

        if model_def.flash_attn:
            args.append("--flash-attn")

        if use_cache:
            args.extend(["--model-cache-dir", str(self.config.cache_dir)])

        if extra_args:
            args.extend(extra_args)

        return args

    def _start_background(self, args: list[str]) -> bool:
        """Start server in background."""
        import subprocess
        import sys

        creationflags = 0
        if sys.platform == "win32":
            creationflags = subprocess.CREATE_NO_WINDOW

        process = subprocess.Popen(
            args,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=creationflags,
        )

        self.pid_file.write_text(str(process.pid))

        if not self.wait_for_ready():
            console.print("[red]Server failed to start[/red]")
            self.stop()
            return False

        return True

    def _start_foreground(self, args: list[str]) -> bool:
        """Start server in foreground."""
        import subprocess
        import sys

        creationflags = 0
        if sys.platform == "win32":
            creationflags = subprocess.CREATE_NO_WINDOW

        self.pid_file.write_text(
            str(
                subprocess.Popen(
                    args,
                    creationflags=creationflags,
                ).pid
            )
        )

        return True

    def wait_for_ready(self, timeout: float = 60.0) -> bool:
        """Wait for server to be ready."""
        url = f"http://{self.config.host}:{self.config.port}/health"
        start_time = time.time()

        while time.time() - start_time < timeout:
            try:
                response = httpx.get(url, timeout=2)
                if response.status_code == 200:
                    return True
            except httpx.RequestError:
                pass
            time.sleep(0.5)

        return False

    def get_status(self) -> dict:
        """Get current server status."""
        url = f"http://{self.config.host}:{self.config.port}/health"
        try:
            response = httpx.get(url, timeout=5)
            return {
                "running": True,
                "healthy": response.status_code == 200,
                "details": response.json() if response.status_code == 200 else None,
            }
        except httpx.RequestError as e:
            return {
                "running": self.is_running(),
                "healthy": False,
                "error": str(e),
            }

    async def generate(
        self,
        messages: list[dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 1024,
        stream: bool = False,
    ) -> dict:
        """Generate text using llama-server API.

        Args:
            messages: List of message dicts with 'role' and 'content' keys
            temperature: Sampling temperature (0.0 to 2.0)
            max_tokens: Maximum tokens to generate
            stream: Whether to stream the response

        Returns:
            API response dict with 'content' key

        Raises:
            RuntimeError: If server is not running
            httpx.HTTPError: If API request fails
        """
        if not self.is_running():
            raise RuntimeError("Server is not running")

        url = f"http://{self.config.host}:{self.config.port}/v1/chat/completions"

        payload = {
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": stream,
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(url, json=payload, timeout=300.0)
            response.raise_for_status()
            data = response.json()

            if stream:
                return data

            # Extract content from response
            if "choices" in data and len(data["choices"]) > 0:
                choice = data["choices"][0]
                if "message" in choice:
                    return {"content": choice["message"]["content"]}
                elif "text" in choice:
                    return {"content": choice["text"]}

            return {"content": ""}

    def _register_shutdown_handler(self) -> None:
        """Register cleanup handler for auto-shutdown on exit."""
        import atexit

        def cleanup():
            if self.config.auto_shutdown_on_exit and self.is_running():
                console.print("[yellow]Auto-shutting down server...[/yellow]")
                self.stop(save_cache=True)

        atexit.register(cleanup)
