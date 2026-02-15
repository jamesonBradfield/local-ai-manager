"""Llama server management with prompt caching support."""

from __future__ import annotations

import subprocess
import time
from pathlib import Path

import httpx
import psutil

from .models import ModelDefinition, ServerConfig


class LlamaServerManager:
    """Manages llama-server process lifecycle with prompt caching."""
    
    def __init__(self, config: ServerConfig) -> None:
        self.config = config
        self._process: subprocess.Popen | None = None
    
    def is_running(self) -> bool:
        """Check if llama-server is currently running."""
        for proc in psutil.process_iter(["name"]):
            try:
                if proc.info["name"] and "llama-server" in proc.info["name"]:
                    return True
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
        return False
    
    def stop(self, save_cache: bool = False, cache_path: Path | None = None) -> bool:
        """Stop the llama-server process gracefully."""
        if not self.is_running():
            return True
        
        # Find and terminate all llama-server processes
        terminated = []
        for proc in psutil.process_iter(["name", "pid"]):
            try:
                if proc.info["name"] and "llama-server" in proc.info["name"]:
                    proc.terminate()
                    terminated.append(proc)
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
        
        # Wait for graceful shutdown
        gone, alive = psutil.wait_procs(terminated, timeout=5)
        
        # Force kill any remaining
        for proc in alive:
            try:
                proc.kill()
            except psutil.NoSuchProcess:
                pass
        
        return len(alive) == 0
    
    def start(
        self,
        model_def: ModelDefinition,
        model_path: Path,
        background: bool = False,
        use_cache: bool = True,
        extra_args: list[str] | None = None,
    ) -> bool:
        """Start llama-server with the given model and configuration."""
        if self.is_running():
            self.stop(save_cache=model_def.save_cache_on_exit)
            time.sleep(1)
        
        args = self._build_args(model_def, model_path, use_cache, extra_args)
        
        if background:
            return self._start_background(args, model_def)
        return self._start_foreground(args)
    
    def _build_args(
        self,
        model_def: ModelDefinition,
        model_path: Path,
        use_cache: bool,
        extra_args: list[str] | None = None,
    ) -> list[str]:
        """Build llama-server command-line arguments."""
        args = [
            str(self.config.llama_server_path),
            "--model", str(model_path),
            "--host", self.config.host,
            "--port", str(self.config.port),
            "--ctx-size", str(model_def.ctx_size),
            "--n-gpu-layers", str(model_def.n_gpu_layers),
            "--threads", str(model_def.threads),
            "--batch-size", str(model_def.batch_size),
            "--ubatch-size", str(model_def.ubatch_size),
            "--parallel", "1",
            "--temp", str(model_def.temperature),
            "--top-p", str(model_def.top_p),
            "--top-k", str(model_def.top_k),
            "--alias", model_def.id,
        ]
        
        # Memory & performance flags
        if model_def.flash_attn:
            args.extend(["--flash-attn", "on"])
        if model_def.mlock:
            args.append("--mlock")
        if not model_def.mmap:
            args.append("--no-mmap")
        if model_def.cont_batching:
            args.append("--cont-batching")
       
        if model_def.cache_type_k:
            args.extend(["--cache-type-k", model_def.cache_type_k])
        if model_def.cache_type_v:
            args.extend(["--cache-type-v", model_def.cache_type_v])

        # Note: Prompt caching via --prompt-cache flag is not supported
        # in this version of llama-server. Cache is handled via the API.
        
        # Add extra custom arguments (can override defaults)
        if extra_args:
            args.extend(extra_args)
        
        return args
    
    def _get_cache_path(self, model_def: ModelDefinition) -> Path | None:
        """Get the cache file path for a model."""
        if model_def.cache_dir:
            cache_dir = Path(model_def.cache_dir).expanduser()
        else:
            cache_dir = self.config.cache_dir
        
        cache_dir.mkdir(parents=True, exist_ok=True)
        return cache_dir / f"{model_def.id}.cache"
    
    def _start_background(self, args: list[str], model_def: ModelDefinition) -> bool:
        """Start server in background mode."""
        self.config.log_dir.mkdir(parents=True, exist_ok=True)
        log_file = self.config.log_dir / f"llama-server-{model_def.id}.log"
        
        with open(log_file, "w") as f:
            self._process = subprocess.Popen(
                args,
                stdout=f,
                stderr=subprocess.STDOUT,
                creationflags=subprocess.CREATE_NO_WINDOW,
            )
        
        return self._process.poll() is None
    
    def _start_foreground(self, args: list[str]) -> bool:
        """Start server in foreground mode."""
        try:
            subprocess.run(args, check=True)
            return True
        except subprocess.CalledProcessError:
            return False
    
    def wait_for_ready(self, timeout: int = 60) -> bool:
        """Wait for the server to be ready to accept requests."""
        start = time.time()
        url = f"http://{self.config.host}:{self.config.port}/health"
        
        while time.time() - start < timeout:
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
