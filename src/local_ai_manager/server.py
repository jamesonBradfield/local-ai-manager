"""Llama server lifecycle management and HTTP API wrapper."""

import sys
import time
from pathlib import Path
from typing import TYPE_CHECKING

import httpx
import psutil
import subprocess
from rich.console import Console

from .models import ModelDefinition, ServerConfig

if TYPE_CHECKING:
    from .models import ServerConfig


console = Console()


class LlamaServerManager:
    """Manages llama-server process lifecycle and HTTP API interactions."""

    def __init__(self, config: ServerConfig) -> None:
        """Initialize server manager.

        Args:
            config: Server configuration
        """
        self.config = config
        config.cache_dir.mkdir(parents=True, exist_ok=True)
        self.pid_file = config.cache_dir / "server.pid"
        self._register_shutdown_handler()

    def is_running(self) -> bool:
        """Check if llama-server is running."""
        if self.pid_file.exists():
            # Check PID file first
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

        # Also check HTTP as fallback (for servers started outside CLI)
        try:
            health_url = f"http://{self.config.host}:{self.config.port}/health"
            response = httpx.get(health_url, timeout=2)
            return response.status_code == 200
        except httpx.RequestError:
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

    def _kill_by_port(self) -> bool:
        """Kill server process by finding it via port."""
        for conn in psutil.net_connections(kind="inet"):
            if conn.laddr.port == self.config.port and conn.status == "LISTEN":
                try:
                    proc = psutil.Process(conn.pid)
                    if proc.name().lower() == "llama-server.exe":
                        proc.terminate()
                        try:
                            proc.wait(timeout=5)
                        except psutil.TimeoutExpired:
                            proc.kill()
                        return True
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass
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

        # Try to get PID from file if it exists
        pid = None
        if self.pid_file.exists():
            try:
                pid = int(self.pid_file.read_text().strip())
            except (ValueError, FileNotFoundError):
                pid = None

        # If we have a valid PID, use it; otherwise try to kill by port
        if pid is None:
            console.print("[yellow]No PID file, attempting to kill by port...[/yellow]")
            if self._kill_by_port():
                return True
            console.print("[red]Could not find server process[/red]")
            return False

        try:
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
        timeout: float | None = None,
        available_models: dict[str, tuple[ModelDefinition, Path]] | None = None,
    ) -> bool:
        """Start the server process.

        Args:
            model_def: Model definition
            model_path: Path to model file
            background: Run in background
            use_cache: Use cached model weights
            extra_args: Additional server arguments
            timeout: Override wait_for_ready timeout (uses config default if None)
            available_models: Dictionary of available models for speculative decoding

        Returns:
            True if started successfully
        """
        if self.is_running():
            console.print("[yellow]Server is already running[/yellow]")
            return True

        if not model_path.exists():
            console.print(f"[red]Model file not found: {model_path}[/red]")
            return False

        args = self._build_args(model_def, model_path, use_cache, extra_args, available_models)

        try:
            if background:
                return self._start_background(args, timeout)
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
        available_models: dict[str, tuple[ModelDefinition, Path]] | None = None,
    ) -> list[str]:
        """Build server command arguments."""
        args = [
            str(self.config.llama_server_path),
            "--model",
            str(model_path),
            "--alias",
            model_def.id,
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
            val = (
                model_def.cache_type_k.value
                if hasattr(model_def.cache_type_k, "value")
                else model_def.cache_type_k
            )
            args.extend(["--cache-type-k", val])

        if model_def.cache_type_v:
            val = (
                model_def.cache_type_v.value
                if hasattr(model_def.cache_type_v, "value")
                else model_def.cache_type_v
            )
            args.extend(["--cache-type-v", val])

        if model_def.flash_attn:
            args.extend(["--flash-attn", "on"])

        if model_def.cache_dir:
            args.extend(["--model-cache-dir", str(model_def.cache_dir)])

        if extra_args:
            args.extend(extra_args)

        if available_models:
            args = self._add_speculative_decoding_args(
                model_def, self.config.models_dir, available_models, args
            )

        return args

    def _add_speculative_decoding_args(
        self,
        model_def: ModelDefinition,
        models_dir: Path,
        available_models: dict[str, tuple[ModelDefinition, Path]],
        args: list[str],
    ) -> list[str]:
        """Add speculative decoding arguments if draft model is configured."""
        if not model_def.draft_model_id:
            return args

        draft_result = available_models.get(model_def.draft_model_id)

        if draft_result is None:
            console.print(
                f"[yellow]Warning: Draft model '{model_def.draft_model_id}' not found, "
                "skipping speculative decoding[/yellow]"
            )
            return args

        draft_model_def, draft_path = draft_result

        args.extend(
            [
                "--model-draft",
                str(draft_path),
                "--draft",
                str(model_def.draft_n_tokens),
                "--draft-p-min",
                str(model_def.draft_p_min),
            ]
        )

        return args

    def _start_background(self, args: list[str], timeout: float | None = None) -> bool:
        """Start server in background."""
        creationflags = 0
        if sys.platform == "win32" and self.config.create_no_window:
            creationflags = subprocess.CREATE_NO_WINDOW

        log_file = self.config.log_dir / f"llama-server-{self.config.default_model}.log"
        log_file.parent.mkdir(parents=True, exist_ok=True)

        with open(log_file, "w") as log_handle:
            try:
                process = subprocess.Popen(
                    args,
                    stdout=log_handle,
                    stderr=subprocess.STDOUT,
                    creationflags=creationflags,
                )
            except Exception as e:
                console.print(f"[red]Failed to launch subprocess: {e}[/red]")
                return False

            self.pid_file.write_text(str(process.pid))
            log_handle.flush()

            wait_timeout = timeout if timeout is not None else self.config.start_timeout
            if not self.wait_for_ready(timeout=wait_timeout):
                console.print(f"[red]Server failed to start - check logs: {log_file}[/red]")
                self.stop()
                return False

        return True

    def _start_foreground(self, args: list[str]) -> bool:
        """Start server in foreground."""
        creationflags = 0
        if sys.platform == "win32" and self.config.create_no_window:
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
        health_url = f"http://{self.config.host}:{self.config.port}/health"
        props_url = f"http://{self.config.host}:{self.config.port}/props"
        try:
            health_response = httpx.get(health_url, timeout=5)
            is_healthy = health_response.status_code == 200

            details = health_response.json() if is_healthy else None

            # Also fetch props for model info
            if is_healthy:
                try:
                    props_response = httpx.get(props_url, timeout=5)
                    if props_response.status_code == 200:
                        props = props_response.json()
                        if details is None:
                            details = {}
                        details["model"] = props.get("model_alias", "Unknown")
                        details["version"] = props.get("build_info", "Unknown")
                except httpx.RequestError:
                    pass

            return {
                "running": True,
                "healthy": is_healthy,
                "details": details,
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
